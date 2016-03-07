'''
Provides commands to globally modify the bot's behaviour.
'''
import logging
import pydoc
from .users_plugin import isadmin
from tombot.registry import get_easy_logger, Command, Subscribe, BOT_START
from tombot.registry import COMMAND_DICT, COMMAND_CATEGORIES
from tombot.helper_functions import determine_sender, extract_query, reply_directly


LOGGER = get_easy_logger('plugins.system')
HELP_OVERVIEW = ''

@Command('ping', 'system')
def ping_cb(bot=None, message=None, *args, **kwargs):
    ''' Return 'pong' to indicate non-deadness. '''
    return 'Pong'

@Command('forcelog', 'system', hidden=True)
def forcelog_cb(bot, message, *args, **kwargs):
    ''' Write a message to the root logger. '''
    logging.info('Forcelog from %s: %s', message.getFrom(), message.getBody())
    return

@Command(['shutdown', 'halt'], 'system')
def shutdown_cb(bot, message, *args, **kwargs):
    ''' Shut down the bot. '''
    LOGGER.info('Stop message received from %s, content "%s"',
                message.getFrom(), message.getBody())
    if not isadmin(bot, message):
        LOGGER.warning('Unauthorized shutdown attempt from %s',
                       determine_sender(message))
        return 'Not authorized.'
    bot.stop()

@Command('restart', 'system')
def restart_cb(bot, message, *args, **kwargs):
    ''' Restart the bot. '''
    LOGGER.info('Restart message received from %s, content "%s"',
                message.getFrom(), message.getBody())
    if not isadmin(bot, message):
        LOGGER.warning('Unauthorized shutdown attempt from %s',
                       determine_sender(message))
        return 'Not authorized.'
    bot.stop(True)

@Command('logdebug', 'system')
def logdebug_cb(bot, message=None, *args, **kwargs):
    ''' Temporarily set the loglevel to debug. '''
    if message:
        if not isadmin(bot, message):
            return 'Not authorized.'
    logging.getLogger().setLevel(logging.DEBUG)
    return 'Ok.'

@Command('loginfo', 'system')
def loginfo_cb(bot, message=None, *args, **kwargs):
    ''' Temporarily (re)set the loglevel to info. '''
    if message:
        if not isadmin(bot, message):
            return 'Not authorized.'
    logging.getLogger().setLevel(logging.INFO)
    return 'Ok.'

@Subscribe(BOT_START)
def build_help_cb(bot, *args, **kwargs):
    '''
    Build the help overview so it can be cached and poked at from shell.
    '''
    global HELP_OVERVIEW
    HELP_OVERVIEW += 'Available commands:\n'
    for category in sorted(COMMAND_CATEGORIES):
        if category:
            HELP_OVERVIEW += '- {}:\n'.format(category)
        for command in sorted(COMMAND_CATEGORIES[category]):
            HELP_OVERVIEW += '{}: {}\n'.format(
                command[0], pydoc.splitdoc(command[2].__doc__)[0])


@Command(['help', '?'], 'system')
@reply_directly
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
            return pydoc.getdoc(COMMAND_DICT[cmd.upper()])
        except KeyError:
            return 'Sorry, that command is not known.'
