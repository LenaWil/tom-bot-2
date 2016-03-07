'''
8ball: provide answers from the void beyond.
'''
import os.path
import random
import fortune
from tombot.registry import Command, get_easy_logger, Subscribe, BOT_START


LOGGER = get_easy_logger('plugins.fortune')
FORTUNE_FILES = []
SPECIALS = {}

@Command('fortune', 'fortune')
def fortune_cb(bot, *args, **kwargs):
    '''
    Return a random quote from one of the quote files.
    '''
    try:
        source = random.choice(FORTUNE_FILES)
        return fortune.get_random_fortune(source)
    except ValueError as ex:
        LOGGER.error('Fortune failed: %s', ex)
        return _('Be the quote you want to see on a wall.\n -- Error 20XX')

@Subscribe(BOT_START)
@Command('loadfortunes', 'fortune', hidden=True)
def load_fortunes_cb(bot, message=None, *args, **kwargs):
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
                SPECIALS[file_] = abspath
                LOGGER.debug('Specials file %s loaded.', abspath)
            except (TypeError, ValueError) as ex:
                LOGGER.error('Specials file %s failed to load: %s',
                             abspath, ex)
    LOGGER.info('%s specials loaded.', len(SPECIALS))

    LOGGER.info('Loading fortunes.')
    for root, dummy, files in os.walk('fortunes/'):
        for file_ in files:
            if not file_.endswith('.txt'):
                continue
            LOGGER.debug('Loading fortune file %s', file_)
            abspath = os.path.join(root, file_)
            try:
                fortune.make_fortune_data_file(abspath, True)
                FORTUNE_FILES.append(abspath)
                LOGGER.debug('Fortune file %s loaded.',
                             abspath)
            except ValueError as ex:
                LOGGER.error('Fortune file %s failed to load: %s',
                             abspath, ex)

    LOGGER.info('%s fortune files loaded.', len(FORTUNE_FILES))
    if message:
        return 'Done.'

@Command(['8ball', 'is'], 'fortune')
def eightball_cb(bot, *args, **kwargs):
    '''
    Provide certainty in a turbulent world.

    Accuracy not guaranteed.
    '''
    try:
        return fortune.get_random_fortune(
            SPECIALS['eightball.spc'])
    except KeyError:
        LOGGER.error('Eightball specials not loaded!')
        return "Sorry, you're out of luck. (ERROR)"
