''' Contains functions that poke the bot to do something on its own '''
import socket
import SocketServer
from yowsup.layers.protocol_messages.protocolentities \
        import TextMessageProtocolEntity
from .registry import get_easy_logger, RPCCommand, RPC_DICT, safe_call


LOGGER = get_easy_logger('rpc')
RPC_OK = 'Ok.'
RPC_FAIL = 'Error.'

def scheduler_ping():
    ''' Ping '''
    LOGGER.info('This is a scheduled ping!')

@RPCCommand('ping')
def rpc_ping_cb(*args):
    ''' Ping '''
    return 'Pong: {}'.format(' '.join(args))

class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):
    ''' Allow the bot to be poked to do stuff '''
    def handle(self):
        data = self.request.recv(1024)
        args = data.split('\x1c')
        LOGGER.debug('Args: %s', args)
        response = RPC_FAIL
        try:
            response = safe_call(RPC_DICT, args[0], self, *args[1:])
        except TypeError as ex:
            response = 'TypeError {}'.format(ex)
        LOGGER.debug('Response: %s', response)
        self.request.sendall(response)

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    ''' Extended to have a reference to the currently running bot'''
    def __init__(self, server_address, RequestHandlerClass, bot, bind_and_activate=True):
        self.bot = bot
        SocketServer.TCPServer.__init__(
            self, server_address, RequestHandlerClass, bind_and_activate)

@RPCCommand('log')
def rpc_log_cb(*args):
    ''' Send all arguments to the log. '''
    LOGGER.info('Forcelog: %s', ' '.join(args))
    return RPC_OK

@RPCCommand('send')
def rpc_send_cb(self, recipient, body, *args):
    ''' Send a message to the bot ('''
    LOGGER.info('Sending %s to %s', body, recipient)
    msg = TextMessageProtocolEntity(
        body, to=recipient)
    self.server.bot.toLower(msg)
    return RPC_OK

def rpc_call(command, *args):
    ''' Call a function via the RPC socket. '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', 10666))
    if args:
        cmd = '{}\x1c{}'.format(command, '\x1c'.join(args))
    else:
        cmd = command
    LOGGER.debug(cmd)
    sock.sendall(cmd)
    resp = sock.recv(1024)
    LOGGER.debug(resp)
    return resp

def remote_send(body, recipient):
    ''' Send a single message via the local reacharound. '''
    resp = rpc_call('SEND', recipient, body)
    if resp != RPC_OK:
        raise ValueError('Something happened. ({})'.format(resp))
