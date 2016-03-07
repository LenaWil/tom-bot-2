'''
Contains generalized events and the command handlers.
'''
#pylint: disable=too-few-public-methods
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
class Subscribe(object):
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

# Commands and RPC commands
class RegisteringDecorator(object):
    '''
    Generalized decorator for registering case-insensitive commands in a dict.

    Must be overridden to specify target.
    '''
    target_dict = {}

    def __init__(self, name):
        self.name = name

    def __call__(self, func):
        if hasattr(self.name, '__iter__'):
            for item in self.name:
                self.target_dict[item.upper()] = func
            #if not self.hidden:
                #if self.category not in FUNCTIONS:
                    #FUNCTIONS[self.category] = []
                #FUNCTIONS[self.category].append((self.name[0], self.name[1:], func))
        else:
            self.target_dict[self.name.upper()] = func
            #if not self.hidden:
                #if self.category not in FUNCTIONS:
                    #FUNCTIONS[self.category] = []
                #FUNCTIONS[self.category].append((self.name, None, func))
        LOGGER.debug('Registered %s in %s', self.name)
        return func

COMMAND_DICT = {}
COMMAND_CATEGORIES = defaultdict(list)
RPC_DICT = {}

class RPCCommand(RegisteringDecorator):
    ''' Registers all functions that are available via the RPC socket. '''
    target_dict = RPC_DICT

class Command(RegisteringDecorator):
    ''' Registers all functions that are available as a command, and in a help_function '''
    target_dict = COMMAND_DICT
    help_dict = COMMAND_CATEGORIES

    def __init__(self, name, category=None, hidden=False):
        self.hidden = hidden
        self.category = category
        super(Command, self).__init__(name)

    def __call__(self, func):
        if isinstance(self.name, types.StringTypes):
            self.help_dict[self.category].append((self.name, None, func))
        else:
            self.help_dict[self.category].append((self.name[0], self.name[1:], func))
        return super(Command, self).__call__(func)

def safe_call(target_dict, key, *args, **kwargs):
    ''' Wrapper to call a function and not crash if it excepts. '''
    try:
        target_dict[key.upper()](*args, **kwargs)
    except NameError:
        raise
    except Exception as ex: #pylint: disable=broad-except
        del target_dict[key]
        LOGGER.critical('Command %s disabled: %s', key, ex)

# Helper functions
def get_easy_logger(name, level=None):
    ''' Create a logger with the given name and optionally a level. '''
    result = logging.getLogger(name)
    if level:
        result.setLevel(level)
    return result
