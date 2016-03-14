''' Contains the Tombot layer, which handles the messages. '''
import os
import sys
import logging
import time
import sqlite3
import threading

from . import plugins
from .helper_functions import unknown_command
import tombot.registry as registry
import tombot.rpc as rpc
from yowsup.layers.interface \
        import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers \
        import YowLayerEvent
from yowsup.layers.network \
        import YowNetworkLayer
from yowsup.layers.protocol_messages.protocolentities \
        import TextMessageProtocolEntity
from yowsup.layers.protocol_receipts.protocolentities \
        import OutgoingReceiptProtocolEntity
from yowsup.layers.protocol_acks.protocolentities \
        import OutgoingAckProtocolEntity
from yowsup.layers.protocol_presence.protocolentities \
        import AvailablePresenceProtocolEntity, UnavailablePresenceProtocolEntity
from apscheduler.schedulers import SchedulerNotRunningError


class TomBotLayer(YowInterfaceLayer):
    ''' The tombot layer, a chatbot for WhatsApp. '''
    # pylint: disable=too-many-instance-attributes
    def __init__(self, config, scheduler):
        super(self.__class__, self).__init__()
        self.connected = False
        self.config = config
        self.scheduler = scheduler
        logging.info('Current working directory: %s', os.getcwd())
        try:
            logging.info('Database location: %s',
                         config['Yowsup']['database'])
            self.conn = sqlite3.connect(config['Yowsup']['database'],
                                        detect_types=sqlite3.PARSE_DECLTYPES,
                                        check_same_thread=False)
            self.conn.text_factory = str
            self.cursor = self.conn.cursor()
        except KeyError:
            logging.critical('Database could not be loaded!')

        # Group list holder
        self.known_groups = []

        # Start rpc listener
        host = 'localhost'
        port = 10666
        self.rpcserver = rpc.ThreadedTCPServer((host, port), rpc.ThreadedTCPRequestHandler, self)

        server_thread = threading.Thread(target=self.rpcserver.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        # Start the passed scheduler
        self.scheduler.start()

        self.functions = {}
        plugins.load_plugins()
        self.functions.update(registry.COMMAND_DICT)

        # Execute startup hooks
        registry.fire_event(registry.BOT_START, self)

    @ProtocolEntityCallback('iq')
    def onIq(self, entity):
        ''' Handles incoming IQ messages, currently inactive. '''
        # pylint: disable=invalid-name
        if hasattr(entity, 'groupsList'):
            logging.info('Discovered groups:')
            logging.info(entity.groupsList)
            self.known_groups = entity.groupsList

    def onEvent(self, layerEvent):
        ''' Handles disconnection events and reconnects if we timed out.'''
        # pylint: disable=invalid-name
        logging.debug('Event %s received', layerEvent.getName())
        if layerEvent.getName() == YowNetworkLayer.EVENT_STATE_DISCONNECTED:
            reason = layerEvent.getArg('reason')
            logging.warning(_('Connection lost: {}').format(reason))
            registry.fire_event(registry.BOT_DISCONNECTED, self)
            if reason == 'Connection Closed':
                time.sleep(.5)
                logging.warning(_('Reconnecting'))
                self.getStack().broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
                self.connected = False
                return True
            else:
                logging.error('Fatal disconnect: %s', reason)
                if self.connected and reason != 'Requested':
                    self.stop()
                return False
        elif layerEvent.getName() == YowNetworkLayer.EVENT_STATE_CONNECTED:
            logging.info('Connection established.')
            self.connected = True
            self.set_online()
            registry.fire_event(registry.BOT_CONNECTED, self)
        return False

    @ProtocolEntityCallback('message')
    def onMessage(self, message):
        ''' Handles incoming messages and responds to them if needed. '''
        # pylint: disable=invalid-name
        logging.debug('Message %s from %s received, content: %s',
                      message.getId(), message.getFrom(), message.getBody())

        receipt = OutgoingReceiptProtocolEntity(
            message.getId(), message.getFrom(),
            'read', message.getParticipant())
        self.toLower(receipt)

        time.sleep(0.2)
        self.react(message)

        registry.fire_event(registry.BOT_MSG_RECEIVE, self, message)

    @ProtocolEntityCallback('receipt')
    def onReceipt(self, entity):
        ''' Sends acknowledgements for read receipts. '''
        # pylint: disable=invalid-name
        ack = OutgoingAckProtocolEntity(
            entity.getId(), 'receipt', entity.getType(), entity.getFrom())
        self.toLower(ack)

    def toLower(self, entity):
        ''' Intercept entites if not connected and warn user. '''
        if not self.connected:
            logging.warning('Not connected, dropping entity!')
            return
        super(self.__class__, self).toLower(entity)

    koekje = '\xf0\x9f\x8d\xaa'

    triggers = [
        'TOMBOT', 'TOMBOT,',
        'BOT', 'BOT,',
        'VRIEZIRI', 'VRIEZIRI,',
        'VICTOR', 'VICTOR,',
        'VIKTOR', 'VIKTOR,',
        'MINION', 'MINION,',
        ]

    def react(self, message):
        ''' Generates a response to a message using a response function and sends it. '''
        content = message.getBody()
        text = content.upper().split()
        isgroup = False
        if message.participant:  # A trigger is required in groups
            isgroup = True
            if text[0] not in self.triggers:
                return
            text.remove(text[0])
        try:
            response = self.functions[text[0]](self, message)
        except IndexError:
            return
        except KeyError:
            if isgroup or content.startswith('@'):
                return # no 'unknown command!' spam
            response = unknown_command(message)
            logging.debug('Failed command %s', text[0])
        except UnicodeDecodeError as ex:
            response = 'UnicodeDecodeError, see logs.'
            logging.error(ex)
        if response:
            reply_message = TextMessageProtocolEntity(
                response, to=message.getFrom())
            self.toLower(reply_message)

    def stop(self, restart=False):
        ''' Shut down the bot. '''
        logging.info('Shutting down via stop method.')
        # Execute shutdown hooks
        registry.fire_event(registry.BOT_SHUTDOWN, self)
        self.set_offline()
        try:
            self.scheduler.shutdown()
        except SchedulerNotRunningError:
            pass
        self.rpcserver.shutdown()
        self.rpcserver.server_close()
        if self.connected:
            self.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
        if restart:
            sys.exit(3)
        sys.exit(0)

    # Helper functions
    def set_online(self, *_):
        ''' Set presence as available '''
        logging.debug('Setting presence online.')
        entity = AvailablePresenceProtocolEntity()
        self.toLower(entity)

    def set_offline(self, *_):
        ''' Set presence as unavailable '''
        logging.debug('Setting presence offline.')
        entity = UnavailablePresenceProtocolEntity()
        self.toLower(entity)

if __name__ == '__main__':
    sys.exit("This script should be run via run.py and/or the tombot-run command.")
