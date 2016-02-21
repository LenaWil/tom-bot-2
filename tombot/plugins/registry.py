'''
Contains functions to be used commonly in plugins.
'''
# pylint: disable=too-few-public-methods, invalid-name
import logging


COMMANDS = {}
STARTUP_FUNCTIONS = set()
SHUTDOWN_FUNCTIONS = set()

def get_easy_logger(name, level=logging.INFO):
    '''
    Create a logger with a console handler and a basic format.
    '''
    result = logging.getLogger(name)
    result.setLevel(level)
    formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(formatter)
    result.addHandler(handler)
    return result

LOGGER = get_easy_logger('tombot.pluginloader')

class register_command(object):
    '''
    Register a function as a command.

    Adds a function to the command dict, either by name or list of names.
    Decorated functions must accept at least two arguments (bot, message).
    '''
    def __init__(self, name):
        self.name = name

    def __call__(self, func):
        if hasattr(self.name, '__iter__'):
            for item in self.name:
                COMMANDS[item.upper()] = func
        else:
            COMMANDS[self.name.upper()] = func
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
