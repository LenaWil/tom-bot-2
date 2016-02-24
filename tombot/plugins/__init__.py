'''
Provides the plugin infrastructure and some helper functions for plugins.
'''
import os.path
import importlib
from .registry import COMMANDS, STARTUP_FUNCTIONS, SHUTDOWN_FUNCTIONS, MESSAGE_HANDLERS
from .registry import get_easy_logger


LOGGER = get_easy_logger('moduleloader')

def load_plugins():
    '''
    Import all plugins.
    '''
    root = os.path.dirname(__file__)
    LOGGER.info('Loading plugins from %s', root)
    for dummy, dummy, files in os.walk(root):
        for ffile in files:
            if ffile.endswith('_plugin.py'):
                modulename = ffile.strip('.py')
                LOGGER.info('Initializing plugin %s', modulename)
                try:
                    importlib.import_module('.' + modulename, package=__name__)
                    LOGGER.debug('%s loaded.', modulename)
                except (NameError, SyntaxError) as ex:
                    LOGGER.error('Module %s cannot be loaded!', modulename)
                    LOGGER.error(ex)
