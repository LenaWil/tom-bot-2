'''
Provides commands to globally modify the bot's behaviour.
'''
from .users_plugin import isadmin
from .registry import get_easy_logger, register_command
from tombot.helper_functions import determine_sender


LOGGER = get_easy_logger('plugins.system')

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
