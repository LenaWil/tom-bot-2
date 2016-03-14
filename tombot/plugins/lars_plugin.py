'''
The best plugin.

Provides the best command, which provides bad pickuplines.
'''
import fortune
from tombot.registry import Command
from .fortune_plugin import SPECIALS


@Command(['lars', 'loveyou', 'pickup', 'date'], 'fortune')
def lars_cb(bot, message, *args, **kwargs):
    '''
    Send a (bad) genderless pickupline to sender.
    '''
    return fortune.get_random_fortune(SPECIALS['pickupline.spc'])
