import json
import os
import logging
import argparse
from configobj import ConfigObj
from .layer import TomBotLayer
from .helper_functions import byteify
# Yowsup
from yowsup.layers.auth                 import YowAuthenticationProtocolLayer
from yowsup.layers.protocol_chatstate   import YowChatstateProtocolLayer
from yowsup.layers.protocol_messages    import YowMessagesProtocolLayer
from yowsup.layers.protocol_receipts    import YowReceiptProtocolLayer
from yowsup.layers.protocol_acks        import YowAckProtocolLayer
from yowsup.layers.protocol_iq          import YowIqProtocolLayer
from yowsup.layers.network              import YowNetworkLayer
from yowsup.layers.coder                import YowCoderLayer
from yowsup.stacks import YowStack
from yowsup.common import YowConstants
from yowsup.layers import YowLayerEvent, YowParallelLayer
from yowsup.stacks import YowStack, YOWSUP_CORE_LAYERS
from yowsup.layers.axolotl import YowAxolotlLayer
from yowsup import env


#CREDENTIALS = (os.environ.get('WA_USER', 'changeme'), os.environ.get('WA_PASS', 'changeme'))
#if CREDENTIALS[0] == 'changeme' or CREDENTIALS[1] == 'changeme':
    #with open('config.json', 'r') as configfile:
        #config = byteify(json.loads(configfile.read()))
        #CREDENTIALS = (config['username'], config['password'])

def main():
    # Arguments
    parser = argparse.ArgumentParser(
            description='Start Tombot, a chatbot for Whatsapp'
            )
    parser.add_argument("-v", "--verbose", help="enable debug logging",
            action="store_true")
    parser.add_argument("-d", "--dry-run", 
            help="don't actually start bot, but print config",
            action="store_true")
    parser.add_argument("configfile", help="config file location")
    args = parser.parse_args()
    # Set up logging
    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO
    logging.basicConfig(level=loglevel)
    # Read configuration
    specpath = os.path.join(os.path.dirname(__file__), 'configspec.ini')
    config = ConfigObj(args.configfile)
    # Build Yowsup stack
    if not args.dry_run:
        CREDENTIALS = (config['Yowsup']['username'], config['Yowsup']['password'])
        layers = (
            TomBotLayer(config),
            YowParallelLayer([YowAuthenticationProtocolLayer, YowMessagesProtocolLayer, 
                YowIqProtocolLayer, YowReceiptProtocolLayer, YowChatstateProtocolLayer, YowAckProtocolLayer]),
            YowAxolotlLayer,
        ) + YOWSUP_CORE_LAYERS

        stack = YowStack(layers)
        stack.setProp(YowAuthenticationProtocolLayer.PROP_CREDENTIALS, CREDENTIALS)         #setting credentials
        stack.setProp(YowNetworkLayer.PROP_ENDPOINT, YowConstants.ENDPOINTS[0])    #whatsapp server address
        stack.setProp(YowCoderLayer.PROP_DOMAIN, YowConstants.DOMAIN)              
        stack.setProp(YowCoderLayer.PROP_RESOURCE, env.CURRENT_ENV.getResource())          #info about us as WhatsApp client

        stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))   #sending the connect signal

        stack.loop(timeout = 0.5, discrete = 0.5) #this is the program mainloop
    else:
        # Output config file to stdout
        config.filename = None
        output = config.write()
        for line in output:
            print(line)


if __name__ == '__main__':
    main()
