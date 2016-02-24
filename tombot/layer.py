''' Contains the Tombot layer, which handles the messages. '''
import os
import sys
import logging
import time
import re
import sqlite3
import datetime
import threading
import dateutil.parser

from . import plugins
from .helper_functions import extract_query, determine_sender
from .helper_functions import forcelog, unknown_command
import tombot.rpc as rpc
import tombot.datefinder as datefinder
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


class TomBotLayer(YowInterfaceLayer):
    ''' The tombot layer, a chatbot for WhatsApp. '''
    # pylint: disable=too-many-instance-attributes
    def __init__(self, config, scheduler):
        super(self.__class__, self).__init__()
        self.config = config
        self.scheduler = scheduler
        logging.info('Current working directory: %s', os.getcwd())
        try:
            logging.info('Database location: %s',
                         config['Yowsup']['database'])
            self.conn = sqlite3.connect(config['Yowsup']['database'])
            self.cursor = self.conn.cursor()
        except KeyError:
            logging.critical('Database could not be loaded!')

        # Mentioning setup
        mention_regex = r'(?<!\w)@\s?(\w+)[ .:,]?'
        self.mention_pattern = re.compile(mention_regex)

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

        self.functions = {  # Plugins :D
            'HELP'      : self.help,
            'FORCELOG'  : forcelog,
            'ADMINCHECK': self.isadmin,
            'DBSETUP'   : self.collect_users,
            'GNS'       : self.get_nameless_seen,
            'REGISTER'  : self.register_user,
            'REMINDME'  : self.addreminder,
            'REMIND'    : self.addreminder,
            'BOTHER'    : self.anonsend,
            }
        plugins.load_plugins()
        self.functions.update(plugins.COMMANDS)

        # Execute startup hooks
        for func in plugins.STARTUP_FUNCTIONS:
            func(self)

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
            if reason == 'Connection Closed':
                time.sleep(.5)
                logging.warning(_('Reconnecting'))
                self.getStack().broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
                return True
            else:
                self.stop()
                return False
        elif layerEvent.getName() == YowNetworkLayer.EVENT_STATE_CONNECTED:
            logging.info('Connection established.')
            self.set_online()
        return False

    @ProtocolEntityCallback('message')
    def onMessageReceived(self, message):
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

        # Handle mentions:
        mentioned_sent = []
        # Used to not send multiple messages to the same person if multiple
        # nicks resolve to the same jid
        for nick in self.mention_pattern.findall(message.getBody()):
            logging.debug('Nick detected: %s', nick)

            # Who sent the message?
            senderjid = determine_sender(message)
            logging.debug('Resolving sender %s', senderjid)
            try:
                sendername = self.jid_to_nick(senderjid)
                logging.debug('Sendernick %s', sendername)
            except KeyError:
                sendername = senderjid
                logging.debug('Could not find jid %s', senderjid)

            # Who was mentioned?
            try:
                targetjid = self.nick_to_jid(nick)
            except KeyError as e:
                # Some nick that is unknown, pass
                logging.debug('Could not resolve nick %s', nick)
                logging.debug('Exception %s', e)
                continue

            if targetjid not in mentioned_sent:
                # Check timeout
                t_info = self.get_jid_timeout(targetjid)
                currenttime = (datetime.datetime.now() - datetime.datetime(
                    1970, 1, 1)).total_seconds()
                if currenttime < (t_info[1] + t_info[0]) and message.participant:
                    # Do not send DM if recipient has not timed out yet
                    continue

                # Send mention notification: [author]: [body]
                entity = TextMessageProtocolEntity('{}: {}'.format(
                    sendername, message.getBody()), to=targetjid)
                self.toLower(entity)
                mentioned_sent.append(targetjid)
        # Updating user's last seen is after mentions so mention timeouts can be tested solo
        self.update_lastseen(message)

    @ProtocolEntityCallback('receipt')
    def onReceipt(self, entity):
        ''' Sends acknowledgements for read receipts. '''
        # pylint: disable=invalid-name
        ack = OutgoingAckProtocolEntity(
            entity.getId(), 'receipt', entity.getType(), entity.getFrom())
        self.toLower(ack)

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
            response = self.functions[text[0]](message)
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
                response.encode('utf-8'), to=message.getFrom())
            self.toLower(reply_message)

    def anonsend(self, message):
        ''' Send a mention under the group name and not the author's name '''
        if not message.participant:
            return

        try:
            groupname = self.jid_to_nick(message.getFrom())
        except KeyError:
            return 'This group is not enrolled in the BrotherBother program, sorry'

        text = extract_query(message, 2)
        body = '{}: {}'.format(groupname, text)

        # Who was mentioned?
        nick = message.getBody().split()[2]
        try:
            recipient = self.nick_to_jid(nick)
        except KeyError:
            return 'Unknown recipient!'

        entity = TextMessageProtocolEntity(body, to=recipient)
        self.toLower(entity)

    def help(self, message):
        ''' TODO: give an overview of available commands. '''
        # pylint: disable=unused-argument
        return self.koekje.decode('utf-8')

    def stop(self, restart=False):
        ''' Shut down the bot. '''
        logging.info('Shutting down via stop method.')
        self.set_offline()
        self.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
        self.config.write()
        self.scheduler.shutdown()
        self.rpcserver.shutdown()
        self.rpcserver.server_close()
        if restart:
            sys.exit(3)
        sys.exit(0)

    # NewNicks
    def collect_users(self, message=None):
        ''' Detect all users and add them to the 'users' table, if not present. Disabled. '''
        # pylint: disable=unused-argument
        logging.info('Beginning user detection.')
        if not self.known_groups:
            logging.warning('Groups have not been detected, aborting.')
            return
        for group in self.known_groups:
            for user in group.getParticipants().keys():
                logging.info('User: %s', user)
                self.cursor.execute('SELECT COUNT(*) FROM users WHERE jid = ?',
                                    (user,))
                result = self.cursor.fetchone()[0]
                if result == 0:
                    logging.info('User not yet present in database, adding...')
                    currenttime = (datetime.datetime.now() -
                                   datetime.datetime(1970, 1, 1)).total_seconds()
                    default_timeout = 2 * 60 * 60 # 2 hours
                    self.cursor.execute('''INSERT INTO USERS
                        (jid, lastactive, timeout, admin) VALUES (?, ?, ?, ?)
                    ''', (user, currenttime, default_timeout, False))
                    logging.info('User added.')
                else:
                    logging.info('User present.')
            self.conn.commit()

    def update_lastseen(self, message):
        ''' Update a user's last seen time in the database. '''
        author = determine_sender(message)
        currenttime = (datetime.datetime.now() - datetime.datetime(1970, 1, 1)).total_seconds()
        logging.debug('Updating %s\'s last seen.', author)
        self.cursor.execute('UPDATE users SET lastactive = ?, message = ? WHERE jid = ?',
                            (currenttime, message.getBody().decode('utf-8'), author))
        self.conn.commit()

    def get_nameless_seen(self, message):
        ''' List all jids which have been heard by the bot, but have no primary nick. '''
        if not self.isadmin(message):
            return
        self.cursor.execute(
            'SELECT id,message,jid FROM users WHERE primary_nick IS NULL AND message IS NOT NULL')
        results = self.cursor.fetchall()
        result = 'Non-registered but seen talking:\n'
        for user in results:
            result += '{} ({}): {}\n'.format(user[0], user[2], user[1])
        return result

    def register_user(self, message):
        ''' Assign a primary nick to a user. '''
        if not self.isadmin(message):
            return
        cmd = extract_query(message)
        try:
            cmdl = cmd.split()
            id_ = int(cmdl[0])
            name = cmdl[1]
            self.cursor.execute('UPDATE users SET primary_nick = ? WHERE id = ?',
                                (name, id_))
            self.conn.commit()
            logging.info(self.cursor.rowcount)
            logging.info('User %s registered as %s.', id_, name)
            return 'Ok'
        except IndexError as ex:
            logging.warning('Invalid message')
            logging.warning(ex)
            return 'Malformed command'
        except sqlite3.IntegrityError as ex:
            logging.error('Error during register')
            logging.error(ex)
            return 'Error'

    def add_other_nick(self, message):
        ''' TODO: Link a nickname to another user (admin-only) '''
        pass

    def remove_other_nick(self, message):
        ''' TODO: Remove a nickname from any user. '''
        # pylint: disable=unused-argument
        pass

    # Remindme and scheduling
    def addreminder(self, message):
        ''' (Hopefully) sends user a message at the given time '''
        body = extract_query(message)
        timespec = body.split()[0]
        trytime = dateutil.parser.parse(body, parserinfo=datefinder.BPI, fuzzy=True)
        delta = None
        if timespec in datefinder.DURATION_MARKERS or datefinder.STRICT_CLOCK_REGEX.match(timespec):
            try:
                delta = datetime.datetime.now() + datefinder.find_timedelta(body)
            except ValueError:
                delta = None
        elif timespec in datefinder.CLOCK_MARKERS:
            try:
                trytime = datefinder.find_first_time(body)
            except ValueError:
                logging.error('Cannot find time in "%s"', body)
        if delta:
            deadline = delta
        else:
            deadline = trytime
        logging.debug('Parsed reminder command "%s"', body)
        logging.info('Deadline %s from message "%s".',
                     deadline, body)
        reply = 'Reminder set for {}.'.format(deadline)
        replymessage = TextMessageProtocolEntity(
            to=determine_sender(message), body=reply)
        self.toLower(replymessage)
        self.scheduler.add_job(
            rpc.remote_send, 'date',
            [body, determine_sender(message)],
            run_date=deadline)
        return

    def nick_to_jid(self, name):
        '''
        Maps a (nick)name to a jid using either users or nicks.

        Raises KeyError if the name is unknown.
        '''
        # Search authornames first
        queries = [
            'SELECT jid FROM users WHERE primary_nick LIKE ?',
            'SELECT jid FROM nicks WHERE name LIKE ?',
            ]
        for query in queries:
            self.cursor.execute(query, (name,))
            result = self.cursor.fetchone()
            if result:
                return result[0]

        raise KeyError('Unknown nick {}!'.format(name))

    def jid_to_nick(self, jid):
        '''
        Map a jid to the user's primary_nick.

        Raises KeyError if user not known.
        '''
        query = 'SELECT primary_nick FROM users WHERE jid = ?'
        self.cursor.execute(query, (jid,))
        result = self.cursor.fetchone()
        if result:
            return result[0]

        raise KeyError('Unknown jid {}'.format(jid))

    def get_jid_timeout(self, jid):
        '''
        Retrieve a user's lastactive and timeout.

        Returns a (timeout, lastactive) tuple.
        Raises KeyError if jid not known.
        '''
        self.cursor.execute(
            'SELECT timeout, lastactive FROM users WHERE jid = ?',
            (jid,))
        result = self.cursor.fetchone()

        if result:
            return result

        raise KeyError('Unknown jid {}'.format(jid))

    # Helper functions
    def isadmin(self, message):
        ''' Check whether the sender of a message is listed as an admin. '''
        # Doen: Use admin field from database, instead of / alongside configfile.
        sender = determine_sender(message)
        try:
            if self.config['Admins'][sender]:
                return True
        except KeyError:
            return False
        return False

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
