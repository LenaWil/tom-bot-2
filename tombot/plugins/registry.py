'''
Contains functions to be used commonly in plugins.
'''
import functools
import logging


commands = {}
startup_functions = set()
shutdown_functions = set()

def get_easy_logger(name, level=logging.INFO):
    '''
    Create a logger with a console handler and a basic format.
    '''
    result = logging.getLogger(name)
    result.setLevel(level)
    formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    result.addHandler(ch)
    return result

logger = get_easy_logger('tombot.pluginloader')

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
                commands[item.upper()] = func
        else:
            commands[self.name.upper()] = func
        logger.debug('Registered command %s', self.name)
        return func

class register_startup(object):
    '''
    Register a function to be run at bot's start.

    Decorated functions must accept at least one argument, bot.
    '''
    def __init__(self, f):
        startup_functions.add(f)
        logger.debug('Registered startup function %s', f)

    def __call__(self):
        pass

class register_shutdown(object):
    '''
    Register a function to be run at shutdown.

    Decorated functions must accept at least one argument, bot.
    '''
    def __init__(self, f):
        shutdown_functions.add(f)
        logger.debug('Registered shutdown function %s', f)

    def __call__(self):
        pass
