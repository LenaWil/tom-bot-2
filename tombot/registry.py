'''
Contains generalized events and the command handlers.
'''
import logging
import types
from collections import defaultdict


LOGGER = get_easy_logger('registry')
# Events

# Event constants:
# Format: NAME = 'identifier' # when, (args)
BOT_START = 'tombot.bot.start'                  # bot's start, (bot)
BOT_SHUTDOWN = 'tombot.bot.shutdown'            # bot shutdown, (bot)
BOT_MSG_RECEIVE = 'tombot.layer.msg_receive'    # message received, (bot, message)
BOT_CONNECTED = 'tombot.bot.connected'          # connection established, (bot)
BOT_DISCONNECTED = 'tombot.bot.disconnected'    # connection lost, (bot)

EVENT_HANDLERS = defaultdict(set)
class Subscribe(object): #pylint: disable=too-few-public-methods
    '''
    Subscribes the decorated function to an event. Function is not modified.
    '''
    def __init__(self, eventname):
        self.eventname = eventname

    def __call__(self, func):
        if hasattr(self.eventname, '__iter__'):
            if isinstance(self.eventname, types.StringTypes):
                # String
                EVENT_HANDLERS[self.eventname].add(func)
                return func

            # Iterable
            for name in self.eventname:
                EVENT_HANDLERS[name].add(func)
            return func

        # Something else
        EVENT_HANDLERS[self.eventname].add(func)
        return func

def fire_event(eventname, *args, **kwargs):
    '''
    Call all subscribed functions with the given arguments.

    Functions which throw exceptions are unregistered.
    '''
    for func in EVENT_HANDLERS[eventname]:
        try:
            func(*args, **kwargs)
        except Exception as ex: #pylint: disable=broad-except
            LOGGER.critical('Event callback %s failed on event %s, disabled:', func, eventname)
            LOGGER.critical(ex)
            EVENT_HANDLERS[eventname].remove(func)

# Helper functions
def get_easy_logger(name, level=None):
    ''' Create a logger with the given name and optionally a level. '''
    result = logging.getLogger(name)
    if level:
        result.setLevel(level)
    return result
