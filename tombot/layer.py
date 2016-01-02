import os
import sys
import logging
import json
import base64
import time
import random
import fortune
import wolframalpha
import duckduckgo
import urllib
from .helper_functions import extract_query, determine_sender
from yowsup.layers.interface                            import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers                                      import YowLayerEvent
from yowsup.layers.network                              import YowNetworkLayer
from yowsup.layers.protocol_messages.protocolentities   import TextMessageProtocolEntity
from yowsup.layers.protocol_receipts.protocolentities   import OutgoingReceiptProtocolEntity
from yowsup.layers.protocol_acks.protocolentities       import OutgoingAckProtocolEntity
from yowsup.layers.protocol_chatstate.protocolentities  import OutgoingChatstateProtocolEntity, ChatstateProtocolEntity


class TomBotLayer(YowInterfaceLayer):
    def __init__(self, config):
        super(self.__class__, self).__init__()
        self.running = True
        self.fortuneFiles = []
        self.loadFortunes()
        self.config = config
        wolframKey = os.environ.get('WOLFRAM_APPID', 'changeme')
        wolframKey = config['Keys']['WolframAlpha']
        if wolframKey != 'changeme':
            self.wolframClient = wolframalpha.Client(wolframKey)
            logging.info(_("WolframAlpha command enabled."))
        else:
            self.wolframClient = False
            logging.warning(_("WolframAlpha command disabled, no API key set."))

    def onEvent(self, layerEvent):
        logging.info('Event {}'.format(layerEvent.getName()))
        if layerEvent.getName() == YowNetworkLayer.EVENT_STATE_DISCONNECTED:
            reason = layerEvent.getArg('reason')
            logging.warning(_("Connection lost: {}").format(reason))
            if reason == 'Connection Closed':
                time.sleep(20)
                logging.warning(_('Reconnecting'))
                self.getStack().broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
                return True
            else:
                self.stop()
                return False
        return False

    @ProtocolEntityCallback('message')
    def onMessageReceived(self, message):
        logging.debug('Message {} from {} received, content: {}'.format(
                    message.getId(), message.getFrom(), message.getBody()))
        receipt = OutgoingReceiptProtocolEntity(
                message.getId(), message.getFrom(),
                'read', message.getParticipant())
        self.toLower(receipt)
        time.sleep(0.2)
        self.react(message)

    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        ack = OutgoingAckProtocolEntity(entity.getId(), "receipt", entity.getType(), entity.getFrom())
        self.toLower(ack)
    
    def loadFortunes(self):
        logging.debug(_('Loading fortune files.'))
        for root, dirs, files in os.walk('fortunes/'):
            for file in files:
                if not file.endswith('.txt'):
                    continue
                logging.debug(_('Loading fortune file {}').format(file))
                try:
                    filepath = os.path.join(root, file)
                    fortune.make_fortune_data_file(filepath, True)
                    self.fortuneFiles.append(filepath)
                    logging.debug(_('Fortune file {} loaded.').format(filepath))
                except Exception as e:
                    logging.error(_('Fortune file {} failed to load: {}').format(filepath, e))
        logging.info(_('Fortune files loaded.'))

    triggers = [
            'TOMBOT', 'TOMBOT,', 
            'BOT', 'BOT,', 
            'VRIEZIRI', 'VRIEZIRI,',
        ]
    def react(self, message):
        functions = { # Has to be inside function because of self.
            'HELP'      : self.help,
            'FORCELOG'  : self.forcelog,
            '8BALL'     : self.eightball,
            'FORTUNE'   : self.fortune,
            'SHUTDOWN'  : self.stopmsg,
            'PING'      : self.ping,
            'CALCULATE' : self.wolfram,
            'BEREKEN'   : self.wolfram,
            'DEFINE'    : self.duckduckgo,
            'DDG'       : self.duckduckgo,
            'ADMINCHECK' : self.isadmin,
            'SETNICK'   : self.set_nick,
            'GETNICK'   : self.get_nick,
            }
        content = message.getBody()
        text = content.upper().split()
        isgroup = False
        if message.participant: # group message, require trigger
            isgroup = True
            if text[0] not in self.triggers: 
                return # don't respond to normal messages
            text.remove(text[0])
        try:
            response = functions[text[0]](message)
        except IndexError:
            return
        except KeyError:
            if isgroup:
                return # no "unknown command!" spam
            response = self.unknownCommand(message)
            logging.debug('failed command {}'.format(text[0]))
        if response:
            replyMessage = TextMessageProtocolEntity(
                    response, to = message.getFrom()
                    )
            self.toLower(replyMessage)
    
    def ping(self, message):
        return "Pong"

    def forcelog(self, message):
        logging.info('Forcelog from {}: {}'.format(message.getFrom(), message.getBody()))
        return False

    def help(self, message):
        return _("I'm helpless!")

    def unknownCommand(self, message):
        return _("Unknown command!")

    def stopmsg(self, message):
        logging.info('Stop message received from {}, content "{}"'.format(
            message.getFrom(), message.getBody()))
        if not self.isadmin(message):
            logging.warning('Unauthorized shutdown attempt from {}'.format(determine_sender(message)))
            return self.userwarn()
        self.stop()

    def stop(self):
        logging.info('Shutting down via stop method.')
        self.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
        self.config.write()
        self.running = False
        sys.exit(0)

    eightballResponses = [
        'It is certain', 'It is decidedly so', 'Without a doubt', 
        'Yes, definitely', 'You may rely on it', 'As I see it, yes', 
        'Most likely', 'Outlook good', 'Yes', 'Signs point to yes',
        'Reply hazy, try again', 'Ask again later', 'Better not tell you now',
        'Cannot predict now', 'Concentrate and ask again', 'Don\'t count on it',
        'My reply is no', 'My sources say no', 'Outlook not so good',
        'Very doubtful'
        ]
    def eightball(self, message):
        return random.choice(self.eightballResponses)

    def fortune(self, message):
        try:
            file = random.choice(self.fortuneFiles)
            return fortune.get_random_fortune(file)
        except:
            return _("Be the quote you want to see on a wall. \n Error message 20XX")

    def userwarn(self):
        try:
            return fortune.get_random_fortune('fortunes/shitcurity.txt')
        except:
            return "Don't do that"
    
    def duckduckgo(self, message):
        """ Answer question using DuckDuckGo instant answer"""
        query = extract_query(message)
        return duckduckgo.get_zci(query)

    def wolfram(self, message):
        """ Answer question using WolframAlpha API """
        if not self.wolframClient:
            return _('Not connected to WolframAlpha!')
        query = extract_query(message)
        logging.debug('Query to WolframAlpha: {}'.format(query))
        entity = OutgoingChatstateProtocolEntity(ChatstateProtocolEntity.STATE_TYPING, message.getFrom())
        self.toLower(entity)
        result = self.wolframClient.query(query)
        entity = OutgoingChatstateProtocolEntity(ChatstateProtocolEntity.STATE_PAUSED, message.getFrom())
        self.toLower(entity)
        restext = _('Result from WolframAlpha:\n')
        results = [p.text for p in result.pods if p.title in ('Result', 'Value', 'Decimal approximation', 'Exact result')]
        if len(results) == 0:
            return _('No result.')
        restext += '\n'.join(results) + '\n'
        restext += 'Link: https://wolframalpha.com/input/?i={}'.format(
                urllib.quote(query).replace('%20','+'))
        return restext
        
    # Nicks
    def set_nick(self, message):
        """ Allow setting of nick for name registration """
        sender = determine_sender(message)
        command = extract_query(message)
        if self.has_nick(sender):
            old_nick = self.get_nick_from_string(sender)
            self.config['Nicks'].pop(old_nick) # Remove old nick
        csplit = command.split()
        self.config['Nicks'][csplit[0]] = sender # Only allow one word for the nick
        self.config['Nicks'][sender] = csplit[0]
        return _("Success! Hello, {}!").format(csplit[0])

    def get_nick(self, message):
        """ Return the name the sender of the message is currently known as """
        sender = determine_sender(message)
        nick = self.get_nick_from_string(sender)
        if not nick:
            return _("Unknown")
        return nick

    def get_nick_from_string(self, name):
        if self.config['Nicks'].has_key(name):
            nick = self.config['Nicks'][name]
            return nick
        else:
            return None

    def has_nick(self, jid):
        return self.config['Nicks'].has_key(jid)

    def admincheck(self, message):
        if self.isadmin(message):
            return 'Yeh'
        return 'Neh'

    # Helper functions
    def isadmin(self, message):
        """ Check admin status """
        sender = determine_sender(message)
        try:
            if self.config['Admins'][sender]:
                return True
        except KeyError:
            return False
        return False


if __name__ == '__main__':
    # Set up logging
    logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s: %(levelname)s - %(message)s',
            filename='logs/tombot.log',
            filemode='a'
            )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    # Read configuration
    if not os.path.isfile('config.json'):
        logging.critical('Could not open config file, exiting.')
        sys.exit(1)
    with open('config.json') as file:
        try:
            config = json.loads(file.read())
        except ValueError:
            logging.critical('Could not parse config, exiting.')
            sys.exit(1)
    logging.info('Configuration read.')

    # Set up bot
    logging.info('Initializing bot...')
    bot = TomBot(
            user = config['yowsup-config']['username'],
            password = config['yowsup-config']['password'],
            config = config
            )
    try:
        while bot.running:
            time.sleep(1)
        logging.info('Bot shut down, exiting.')
        sys.exit(0)
    except KeyboardInterrupt:
        logging.info('Keyboard interrupt received, exiting.')
        bot.stop()
        sys.exit(130)

