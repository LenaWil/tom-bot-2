'''
Provides a command for answering queries using the WolframAlpha API.
'''
import os
import urllib

import wolframalpha

from tombot.helper_functions import extract_query
from .registry import register_command, get_easy_logger, register_startup
from yowsup.layers.protocol_chatstate.protocolentities \
    import OutgoingChatstateProtocolEntity, ChatstateProtocolEntity


LOGGER = get_easy_logger('plugins.wolframalpha')
CLIENT = None

@register_command(['calc', 'calculate', 'bereken'])
def wolfram_cb(bot, message, *args, **kwargs):
    '''
    (Attempt to) answer query using the WolframAlpha API.

    Results may not be interpreted as you'd expect, open link for explanation.
    '''
    if not CLIENT:
        return _('Not connected to WolframAlpha!')
    query = extract_query(message)
    LOGGER.debug('Query to WolframAlpha: %s', query)
    entity = OutgoingChatstateProtocolEntity(
        ChatstateProtocolEntity.STATE_TYPING, message.getFrom())
    bot.toLower(entity)
    result = CLIENT.query(query)
    entity = OutgoingChatstateProtocolEntity(
        ChatstateProtocolEntity.STATE_PAUSED, message.getFrom())
    bot.toLower(entity)
    restext = _('Result from WolframAlpha:\n')
    results = [p.text.encode('utf-8') for p in result.pods
               if p.title in ('Result', 'Value', 'Decimal approximation', 'Exact result')]
    if not results:
        return _('No result.')
    restext += '\n'.join(results) + '\n'
    restext += 'Link: https://wolframalpha.com/input/?i={}'.format(
        urllib.quote(query).replace('%20', '+'))
    return restext

@register_startup
def wolframinit_cb(bot, *args, **kwargs):
    '''
    Set up the Wolfram API client.

    Requires either an environment variable or a config key Keys.WolframAlpha.
    The environment variable overrides the config key.
    '''
    global CLIENT
    apikey = os.environ.get('WOLFRAM_APPID', None)
    if not apikey:
        try:
            apikey = bot.config['Keys']['WolframAlpha']
            if apikey == 'changeme':
                raise ValueError
        except (KeyError, ValueError):
            LOGGER.error('No API key was set! Get one from'
                         ' https://developer.wolframalpha.com/portal/apisignup.html')
            bot.functions = {key: value for key, value in bot.functions.items()
                             if value != wolfram_cb}
            LOGGER.error('Wolfram command disabled.')
    CLIENT = wolframalpha.Client(apikey)
    LOGGER.info('WolframAlpha command enabled.')
