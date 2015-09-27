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
from yowsup.layers.interface                            import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers                                      import YowLayerEvent
from yowsup.layers.network                              import YowNetworkLayer
from yowsup.layers.protocol_messages.protocolentities   import TextMessageProtocolEntity
from yowsup.layers.protocol_receipts.protocolentities   import OutgoingReceiptProtocolEntity
from yowsup.layers.protocol_acks.protocolentities       import OutgoingAckProtocolEntity
from yowsup.layers.protocol_chatstate.protocolentities  import OutgoingChatstateProtocolEntity, ChatstateProtocolEntity


class TomBotLayer(YowInterfaceLayer):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.running = True
        self.fortuneFiles = []
        self.loadFortunes()
        wolframKey = os.environ.get('WOLFRAM_APPID', 'changeme')
        if wolframKey != 'changeme':
            self.wolframClient = wolframalpha.Client(wolframKey)
            logging.info('WolframAlpha client enabled, API key set.')
        else:
            self.wolframClient = False
            logging.info('WolframAlpha client disabled, no API key given.')

    def onAuthSuccess(self, args):
        logging.info('Authentication successful.')
        self.loadFortunes()

    def onAuthFailed(self, args):
        logging.critical('Authentication failed.')
        self.running = False

    def onEvent(self, layerEvent):
        logging.info('Event {}'.format(layerEvent.getName()))
        if layerEvent.getName() == YowNetworkLayer.EVENT_STATE_DISCONNECTED:
            reason = layerEvent.getArg('reason')
            logging.warning('Connection lost: {}'.format(reason))
            if reason == 'Connection Closed':
                time.sleep(20)
                logging.warning('Reconnecting')
                self.getStack().broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
                return True
            else:
                self.stop()
                return False
        return False

    def onDisconnected(self, args):
        logging.error('Connection lost.')
        self.running = False

    def onMessageDelivered(self, message):
        logging.debug('Message {} to {} delivered.'.format(message.getId(), message.getTo()))

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
        logging.debug('Loading fortune files.')
        for root, dirs, files in os.walk('fortunes/'):
            for file in files:
                if not file.endswith('.txt'):
                    continue
                logging.debug('Loading fortune file {}'.format(file))
                try:
                    filepath = os.path.join(root, file)
                    fortune.make_fortune_data_file(filepath)
                    self.fortuneFiles.append(filepath)
                    logging.debug('Fortune file {} loaded.'.format(filepath))
                except Exception as e:
                    logging.error('Fortune file {} failed to load: {}'.format(filepath, e))
        logging.info('Fortune files loaded.')

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
        except KeyError:
            if isgroup:
                return # no "unknown command!" spam
            response = self.unknownCommand(message)
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
        return "Git gud"

    def unknownCommand(self, message):
        return "Unknown command!"

    def stopmsg(self, message):
        logging.info('Stop message received from {}, content "{}"'.format(
            message.getFrom(), message.getBody()))
        self.stop()
        return "Shutting down."

    def stop(self):
        logging.info('Shutting down via stop method.')
        self.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
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
            return "Something went wrong, go bug my author!"
    
    def extract_query(self, message, cmdlength = 1):
        """ Remove the command and trigger from the message body, return the stripped text."""
        content = message.getBody()
        if message.participant:
            offset = 1 + cmdlength
        else:
            offset = cmdlength
        return ' '.join(content.split()[offset:])

    def duckduckgo(self, message):
        """ Beantwoord vraag met DuckDuckGo's API"""
        query = self.extract_query(message)
        return duckduckgo.get_zci(query)

    def wolfram(self, message):
        """ Beantwoord vraag met WolframAlpha """
        if not self.wolframClient:
            return 'Geen verbinding met WolframAlpha.'
        query = self.extract_query(message)
        logging.debug('Query to WolframAlpha: {}'.format(query))
        try:
            entity = OutgoingChatstateProtocolEntity(ChatstateProtocolEntity.STATE_TYPING, message.getFrom())
            self.toLower(entity)
            result = self.wolframClient.query(query)
            entity = OutgoingChatstateProtocolEntity(ChatstateProtocolEntity.STATE_PAUSED, message.getFrom())
            self.toLower(entity)
            logging.info('Wolfram response: {}'.format(next(result.results).text.encode('utf-8')))
            restext = 'Resultaat van WolframAlpha:\n'
            restext += next(result.results).text.encode('utf-8') + '\n'
            restext += 'Link: https://wolframalpha.com/input/?i={}'.format(
                    urllib.quote(query).replace('%20','+'))
            return restext
        except StopIteration:
            logging.error('StopIteration op query "{}"'.format(query))
            return 'Geen resultaat.'

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

