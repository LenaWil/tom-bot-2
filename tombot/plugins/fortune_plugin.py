'''
8ball: provide answers from the void beyond.
'''
import os.path
import random
import fortune
from .registry import register_command, get_easy_logger, register_startup


LOGGER = get_easy_logger('plugins.fortune')

@register_command('fortune')
def fortune_cb(bot, *args, **kwargs):
    '''
    Return a random quote from one of the quote files.
    '''
    try:
        source = random.choice(bot.fortune_files)
        return fortune.get_random_fortune(source)
    except ValueError as ex:
        LOGGER.error('Fortune failed: %s', ex)
        return _('Be the quote you want to see on a wall.\n -- Error 20XX')

@register_startup
@register_command('loadfortunes', hidden=True)
def load_fortunes_cb(bot, *args, **kwargs):
    '''
    (Re)load all fortune and specials files from their directories.
    '''
    LOGGER.info('Loading specials.')
    for root, dummy, files in os.walk('specials/'):
        for file_ in files:
            if not file_.endswith('.spc'):
                continue
            LOGGER.debug('Loading specials file %s', file_)
            abspath = os.path.join(root, file_)
            try:
                fortune.make_fortune_data_file(abspath, True)
                bot.specials[file_] = abspath
                LOGGER.debug('Specials file %s loaded.', abspath)
            except ValueError as ex:
                LOGGER.error('Specials file %s failed to load: %s',
                             abspath, ex)
    LOGGER.info('%s specials loaded.', len(bot.specials))

    LOGGER.info('Loading fortunes.')
    for root, dummy, files in os.walk('fortunes/'):
        for file_ in files:
            if not file_.endswith('.txt'):
                continue
            LOGGER.debug('Loading fortune file %s', file_)
            abspath = os.path.join(root, file_)
            try:
                fortune.make_fortune_data_file(abspath, True)
                bot.fortune_files.append(abspath)
                LOGGER.debug('Fortune file %s loaded.',
                             abspath)
            except ValueError as ex:
                LOGGER.error('Fortune file %s failed to load: %s',
                             abspath, ex)

    LOGGER.info('Fortune files loaded.')
    return 'Done.'

@register_command(['8ball', 'is'])
def eightball_cb(bot, *args, **kwargs):
    '''
    Provide certainty in a turbulent world.

    Accuracy not guaranteed.
    '''
    try:
        return fortune.get_random_fortune(
            bot.specials['eightball.spc'])
    except KeyError:
        LOGGER.error('Eightball specials not loaded!')
        return "Sorry, you're out of luck. (ERROR)"
