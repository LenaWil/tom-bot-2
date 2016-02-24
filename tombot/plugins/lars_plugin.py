'''
The best plugin.

Provides the best command, which provides bad pickuplines.
'''
import fortune
from .registry import register_command
from .fortune_plugin import SPECIALS


@register_command(['lars', 'loveyou', 'pickup', 'date'])
def lars_cb(bot, message, *args, **kwargs):
    '''
    Send a (bad) genderless pickupline to sender.
    '''
    return fortune.get_random_fortune(bot.specials['pickupline.spc'])
