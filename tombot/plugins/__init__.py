'''
    Executes all files ending in '_plugin.py' in the plugin package, and collects the results.
'''
import os.path
import logging
import importlib
from .registry import commands, get_easy_logger


logger = get_easy_logger('tombot.moduleloader')

def load_plugins():
    root = os.path.dirname(__file__)
    logger.info('Loading plugins from %s', root)
    for top, dirs, files in os.walk(root):
        for ffile in files:
            if ffile.endswith('_plugin.py'):
                path = os.path.join(top, ffile)
                modulename = ffile.strip('.py')
                logger.info('Initializing plugin %s', modulename)
                importlib.import_module('.' + modulename, package=__name__)
