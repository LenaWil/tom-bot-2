'''
Provides the cookie command, which originally was a test for unicode and now
spouts cookie quotes.
'''
import fortune
from .registry import register_command, get_easy_logger
from .fortune_plugin import SPECIALS


LOGGER = get_easy_logger('plugins.cookie')

@register_command(['cookie', 'koekje', '\xf0\x9f\x8d\xaa'], 'fortune')
def cookie_cb(bot, *args, **kwargs):
    '''
    Return a cookie-related quote.
    '''
    try:
        return fortune.get_random_fortune(SPECIALS['cookie.spc'])
    except KeyError:
        LOGGER.error('Specials file was not loaded!')
        return 'Error!\xf0\x9f\x8d\xaa'
