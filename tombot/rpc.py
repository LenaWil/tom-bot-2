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
        logging.info(data)
        response = "Ok."
        self.request.sendall(response)

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    ''' Mixin placeholder '''
    pass


