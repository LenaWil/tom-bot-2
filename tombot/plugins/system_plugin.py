'''
Provides commands to globally modify the bot's behaviour.
'''
import logging
from .users_plugin import isadmin
from .registry import get_easy_logger, register_command
from tombot.helper_functions import determine_sender


LOGGER = get_easy_logger('plugins.system')

@register_command('ping')
def ping_cb(bot=None, message=None, *args, **kwargs):
    ''' Return 'pong' to indicate non-deadness. '''
    return 'Pong'

@register_command(['shutdown', 'halt'])
def shutdown_cb(bot, message, *args, **kwargs):
    ''' Shut down the bot. '''
    LOGGER.info('Stop message received from %s, content "%s"',
                message.getFrom(), message.getBody())
    if not isadmin(bot, message):
        LOGGER.warning('Unauthorized shutdown attempt from %s',
                       determine_sender(message))
        return 'Not authorized.'
    bot.stop()

@register_command('restart')
def restart_cb(bot, message, *args, **kwargs):
    ''' Restart the bot. '''
    LOGGER.info('Restart message received from %s, content "%s"',
                message.getFrom(), message.getBody())
    if not isadmin(bot, message):
        LOGGER.warning('Unauthorized shutdown attempt from %s',
                       determine_sender(message))
        return 'Not authorized.'
    bot.stop(True)

@register_command('logdebug')
def logdebug_cb(bot, message=None, *args, **kwargs):
    ''' Temporarily set the loglevel to debug. '''
    if message:
        if not bot.isadmin(message):
            return 'Not authorized.'
    logging.getLogger().setLevel(logging.DEBUG)
    return 'Ok.'

@register_command('loginfo')
def loginfo_cb(bot, message=None, *args, **kwargs):
    ''' Temporarily (re)set the loglevel to info. '''
    if message:
        if not bot.isadmin(message):
            return 'Not authorized.'
    logging.getLogger().setLevel(logging.INFO)
    return 'Ok.'
