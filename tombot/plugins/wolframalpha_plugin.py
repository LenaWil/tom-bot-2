'''
Provides a command for answering queries using the WolframAlpha API.
'''
import urllib
from tombot.helper_functions import extract_query
from .registry import register_command, get_easy_logger
from yowsup.layers.protocol_chatstate.protocolentities \
    import OutgoingChatstateProtocolEntity, ChatstateProtocolEntity


LOGGER = get_easy_logger('tombot.plugins.wolframalpha')

@register_command(['calc', 'calculate', 'bereken'])
def wolfram_cb(bot, message, *args, **kwargs):
    '''
    (Attempt to) answer query using the WolframAlpha API.

    Results may not be interpreted as you'd expect, open link for explanation.
    '''
    if not bot.wolfram_client:
        return _('Not connected to WolframAlpha!')
    query = extract_query(message)
    LOGGER.debug('Query to WolframAlpha: %s', query)
    entity = OutgoingChatstateProtocolEntity(
        ChatstateProtocolEntity.STATE_TYPING, message.getFrom())
    bot.toLower(entity)
    result = bot.wolfram_client.query(query)
    entity = OutgoingChatstateProtocolEntity(
        ChatstateProtocolEntity.STATE_PAUSED, message.getFrom())
    bot.toLower(entity)
    restext = _('Result from WolframAlpha:\n')
    results = [p.text for p in result.pods
               if p.title in ('Result', 'Value', 'Decimal approximation', 'Exact result')]
    if not results:
        return _('No result.')
    restext += '\n'.join(results) + '\n'
    restext += 'Link: https://wolframalpha.com/input/?i={}'.format(
        urllib.quote(query).replace('%20', '+'))
    return restext
