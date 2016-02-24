'''
Contains functions to be used commonly in plugins.
'''
# pylint: disable=too-few-public-methods, invalid-name
import logging


COMMANDS = {}
FUNCTIONS = {}  # similiar to commands, but grouped by category and used for help.
STARTUP_FUNCTIONS = set()
SHUTDOWN_FUNCTIONS = set()
MESSAGE_HANDLERS = set()

def get_easy_logger(name, level=None):
    '''
    Create a logger with a console handler and a basic format.
    '''
    result = logging.getLogger(name)
    if level:
        result.setLevel(level)
    return result

LOGGER = get_easy_logger('pluginloader')

class register_command(object):
    '''
    Register a function as a command.

    Adds a function to the command dict, either by name or list of names.
    Decorated functions must accept at least two arguments (bot, message).

    If the function is not hidden, it is also added to the help dict.
    '''
    def __init__(self, name, category=None, hidden=False):
        self.name = name
        self.hidden = hidden
        self.category = category

    def __call__(self, func):
        if hasattr(self.name, '__iter__'):
            for item in self.name:
                COMMANDS[item.upper()] = func
            if not self.hidden:
                if self.category not in FUNCTIONS:
                    FUNCTIONS[self.category] = []
                FUNCTIONS[self.category].append((self.name[0], self.name[1:], func))
        else:
            COMMANDS[self.name.upper()] = func
            if not self.hidden:
                if self.category not in FUNCTIONS:
                    FUNCTIONS[self.category] = []
                FUNCTIONS[self.category].append((self.name, None, func))
        LOGGER.debug('Registered command %s', self.name)
        return func

class register_startup(object):
    '''
    Register a function to be run at bot's start.

    Decorated functions must accept at least one argument, bot.
    '''
    def __init__(self, f):
        STARTUP_FUNCTIONS.add(f)
        LOGGER.debug('Registered startup function %s', f)

    def __call__(self):
        pass

class register_shutdown(object):
    '''
    Register a function to be run at shutdown.

    Decorated functions must accept at least one argument, bot.
    '''
    def __init__(self, f):
        SHUTDOWN_FUNCTIONS.add(f)
        LOGGER.debug('Registered shutdown function %s', f)

    def __call__(self):
        pass

class message_handler(object):
    '''
    Register a function to be run after receiving a message.

    Decorated functions must accept at least two arguments, (bot, message).
    '''
    def __init__(self, f):
        MESSAGE_HANDLERS.add(f)
        LOGGER.debug('Registered message handler %s', f)

    def __call__(self):
        pass
