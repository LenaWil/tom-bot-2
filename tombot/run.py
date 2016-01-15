''' Contains script to start the bot. '''
from __future__ import print_function
import os
import sys
import logging
import argparse
from configobj import ConfigObj
from validate import Validator
from .layer import TomBotLayer
# Yowsup
from yowsup.layers.auth                 import YowAuthenticationProtocolLayer
from yowsup.layers.protocol_chatstate   import YowChatstateProtocolLayer
from yowsup.layers.protocol_groups      import YowGroupsProtocolLayer
from yowsup.layers.protocol_messages    import YowMessagesProtocolLayer
from yowsup.layers.protocol_receipts    import YowReceiptProtocolLayer
from yowsup.layers.protocol_acks        import YowAckProtocolLayer
from yowsup.layers.protocol_iq          import YowIqProtocolLayer
from yowsup.layers.network              import YowNetworkLayer
from yowsup.layers.coder                import YowCoderLayer
from yowsup.stacks import YowStack
from yowsup.stacks import YOWSUP_CORE_LAYERS
from yowsup.common import YowConstants
from yowsup.layers import YowLayerEvent, YowParallelLayer
from yowsup.layers.axolotl import YowAxolotlLayer
from yowsup import env

def main():
    ''' Console script to start the bot or output default config file. '''
    # Arguments
    parser = argparse.ArgumentParser(
        description=_('Start Tombot, a chatbot for Whatsapp')
        )
    parser.add_argument(
        '-v', '--verbose', help=_("enable debug logging"), action='store_true')
    parser.add_argument(
        '-d', '--dry-run',
        help=_("don't actually start bot, but print config"),
        action='store_true')
    parser.add_argument('configfile', help=_("config file location"), nargs='?')
    args = parser.parse_args()
    # Set up logging
    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO
    logging.basicConfig(level=loglevel)
    # Read configuration
    specpath = os.path.join(os.path.dirname(__file__), 'configspec.ini')
    config = ConfigObj(args.configfile, configspec=specpath)
    val = Validator()
    if not args.dry_run:
        config.validate(val)
        if not args.configfile:
            error = _("You must specify a config file!")
            generate_hint = _("Generate one using 'tombot -d > file.ini'.")
            logging.critical(error)
            logging.critical(generate_hint)
            sys.exit(1)
        # Build Yowsup stack
        credentials = (config['Yowsup']['username'], config['Yowsup']['password'])
        layers = (
            TomBotLayer(config),
            YowParallelLayer([
                YowAuthenticationProtocolLayer, YowMessagesProtocolLayer,
                YowIqProtocolLayer, YowReceiptProtocolLayer, YowChatstateProtocolLayer,
                YowAckProtocolLayer, YowGroupsProtocolLayer
                ]),
            YowAxolotlLayer,
        ) + YOWSUP_CORE_LAYERS

        stack = YowStack(layers)
        # Set credentials, server address, info about us as WhatsApp client
        stack.setProp(YowAuthenticationProtocolLayer.PROP_CREDENTIALS, credentials)
        stack.setProp(YowNetworkLayer.PROP_ENDPOINT, YowConstants.ENDPOINTS[0])
        stack.setProp(YowCoderLayer.PROP_DOMAIN, YowConstants.DOMAIN)
        stack.setProp(YowCoderLayer.PROP_RESOURCE, env.CURRENT_ENV.getResource())

        # Send connect signal
        stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))

        stack.loop(timeout=0.5, discrete=0.5)  #this is the program mainloop
    else:
        # Output config file to stdout
        config.filename = None
        config.validate(val, copy=True)
        output = config.write()
        for line in output:
            print(line)

if __name__ == '__main__':
    main()
