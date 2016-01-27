''' Contains functions that poke the bot to do something on its own '''
import socket
import threading
import SocketServer
import logging


def scheduler_ping():
    ''' Ping '''
    logging.info('This is a scheduled ping!')

class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):
    ''' Allow the bot to be poked to do stuff '''
    def handle(self):
        data = self.request.recv(1024)
        args = data.split('\x1c')
        if args[0].upper() == 'LOG':
            logging.info(args)
        elif args[0].upper() == 'SEND':
            logging.info('Sending %s to %s', args[1], args[2])
        logging.info(data)
        response = "Ok."
        self.request.sendall(response)

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    ''' Extended to have a reference to the currently running bot'''
    def __init__(self, server_address, RequestHandlerClass, bot, bind_and_activate=True):
        self.bot = bot
        SocketServer.TCPServer.__init__(
            self, server_address, RequestHandlerClass, bind_and_activate)
