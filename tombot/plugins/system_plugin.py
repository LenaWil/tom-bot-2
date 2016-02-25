'''
Provides commands to globally modify the bot's behaviour.
'''
import logging
import pydoc
from .users_plugin import isadmin
from .registry import get_easy_logger, register_command, register_startup
from .registry import FUNCTIONS, COMMANDS
from tombot.helper_functions import determine_sender, extract_query


LOGGER = get_easy_logger('plugins.system')
HELP_OVERVIEW = ''

@register_command('ping', 'system')
def ping_cb(bot=None, message=None, *args, **kwargs):
    ''' Return 'pong' to indicate non-deadness. '''
    return 'Pong'

@register_command('forcelog', 'system', hidden=True)
def forcelog_cb(bot, message, *args, **kwargs):
    ''' Write a message to the root logger. '''
    logging.info('Forcelog from %s: %s', message.getFrom(), message.getBody())
    return

@register_command(['shutdown', 'halt'], 'system')
def shutdown_cb(bot, message, *args, **kwargs):
    ''' Shut down the bot. '''
    LOGGER.info('Stop message received from %s, content "%s"',
                message.getFrom(), message.getBody())
    if not isadmin(bot, message):
        LOGGER.warning('Unauthorized shutdown attempt from %s',
                       determine_sender(message))
        return 'Not authorized.'
    bot.stop()

@register_command('restart', 'system')
def restart_cb(bot, message, *args, **kwargs):
    ''' Restart the bot. '''
    LOGGER.info('Restart message received from %s, content "%s"',
                message.getFrom(), message.getBody())
    if not isadmin(bot, message):
        LOGGER.warning('Unauthorized shutdown attempt from %s',
                       determine_sender(message))
        return 'Not authorized.'
    bot.stop(True)

@register_command('logdebug', 'system')
def logdebug_cb(bot, message=None, *args, **kwargs):
    ''' Temporarily set the loglevel to debug. '''
    if message:
        if not isadmin(bot, message):
            return 'Not authorized.'
    logging.getLogger().setLevel(logging.DEBUG)
    return 'Ok.'

@register_command('loginfo', 'system')
def loginfo_cb(bot, message=None, *args, **kwargs):
    ''' Temporarily (re)set the loglevel to info. '''
    if message:
        if not isadmin(bot, message):
            return 'Not authorized.'
    logging.getLogger().setLevel(logging.INFO)
    return 'Ok.'

@register_startup
def build_help_cb(bot, *args, **kwargs):
    '''
    Build the help overview so it can be cached and poked at from shell.
    '''
    global HELP_OVERVIEW
    HELP_OVERVIEW += 'Available commands:\n'
    for category in sorted(FUNCTIONS):
        if category:
            HELP_OVERVIEW += '- {}:\n'.format(category)
        for command in sorted(FUNCTIONS[category]):
            HELP_OVERVIEW += '{}: {}\n'.format(
                command[0], pydoc.splitdoc(command[2].__doc__)[0])


@register_command(['help', '?'], 'system')
def help_cb(bot, message, *args, **kwargs):
    '''
    Give moral and spiritual guidance in using this bot.

    When you select one command, a longer text will be sent!
    '''
    cmd = extract_query(message)
    if not cmd:
        return HELP_OVERVIEW
    else:
        try:
            return pydoc.getdoc(COMMANDS[cmd.upper()])
        except KeyError:
            return 'Sorry, that command is not known.'
