from tombotlayer import TomBotLayer
from yowsup.layers.auth                 import YowAuthenticationProtocolLayer
from yowsup.layers.protocol_messages    import YowMessagesProtocolLayer
from yowsup.layers.protocol_receipts    import YowReceiptProtocolLayer
from yowsup.layers.protocol_acks        import YowAckProtocolLayer
from yowsup.layers.protocol_iq          import YowIqProtocolLayer
from yowsup.layers.network              import YowNetworkLayer
from yowsup.layers.coder                import YowCoderLayer
from yowsup.stacks import YowStack
from yowsup.common import YowConstants
from yowsup.layers import YowLayerEvent
from yowsup.stacks import YowStack, YOWSUP_CORE_LAYERS
from yowsup.layers.axolotl import YowAxolotlLayer
from yowsup import env
import json
import os

def byteify(input):
    """ 
    Helper function to force json deserialize to string and not unicode. 
    Written by Mark Amery on https://stackoverflow.com/a/13105359
    """
    if isinstance(input, dict):
        return {byteify(key):byteify(value) for key,value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input

CREDENTIALS = (os.environ.get('WA_USER', 'changeme'), os.environ.get('WA_PASS', 'changeme'))
if CREDENTIALS[0] == 'changeme' or CREDENTIALS[1] == 'changeme':
    with open('config.json', 'r') as configfile:
        config = byteify(json.loads(configfile.read()))
        CREDENTIALS = (config['username'], config['password'])

if __name__==  "__main__":
    layers = (
        TomBotLayer,
        (YowAuthenticationProtocolLayer, YowMessagesProtocolLayer, 
            YowIqProtocolLayer, YowReceiptProtocolLayer, YowAckProtocolLayer),
        YowAxolotlLayer,
    ) + YOWSUP_CORE_LAYERS

    stack = YowStack(layers)
    stack.setProp(YowAuthenticationProtocolLayer.PROP_CREDENTIALS, CREDENTIALS)         #setting credentials
    stack.setProp(YowNetworkLayer.PROP_ENDPOINT, YowConstants.ENDPOINTS[0])    #whatsapp server address
    stack.setProp(YowCoderLayer.PROP_DOMAIN, YowConstants.DOMAIN)              
    stack.setProp(YowCoderLayer.PROP_RESOURCE, env.CURRENT_ENV.getResource())          #info about us as WhatsApp client

    stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))   #sending the connect signal

    stack.loop() #this is the program mainloop
