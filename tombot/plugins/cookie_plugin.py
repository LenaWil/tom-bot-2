'''
Provides the cookie command, which originally was a test for unicode and now
spouts cookie quotes.
'''
import fortune
from .registry import register_command, get_easy_logger


LOGGER = get_easy_logger('plugins.cookie')

@register_command(['cookie', 'koekje', '\xf0\x9f\x8d\xaa'])
def cookie_cb(bot, *args, **kwargs):
    '''
    Provide random vaguely cookie-related quotes.
    '''
    try:
        return fortune.get_random_fortune(bot.specials['cookie.spc'])
    except KeyError:
        LOGGER.error('Specials file was not loaded!')
        return 'Error!\xf0\x9f\x8d\xaa'
