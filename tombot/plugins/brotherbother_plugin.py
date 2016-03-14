'''
Brotherbother: semianonymously send messages under a group's name.
'''
from tombot.helper_functions import extract_query
from tombot.registry import Command
from .users_plugin import jid_to_nick, nick_to_jid
from yowsup.layers.protocol_messages.protocolentities import TextMessageProtocolEntity


@Command('bother')
def anonsend_cb(bot, message, *args, **kwargs):
    ''' Send a mention under the group name and not the author's name '''
    if not message.participant:
        return

    try:
        groupname = jid_to_nick(bot, message.getFrom())
    except KeyError:
        return 'This group is not enrolled in the BrotherBother program, sorry'

    text = extract_query(message, 2)
    body = '{}: {}'.format(groupname, text)

    # Who was mentioned?
    nick = message.getBody().split()[2]
    try:
        recipient = nick_to_jid(bot, nick)
    except KeyError:
        return 'Unknown recipient!'

    entity = TextMessageProtocolEntity(body, to=recipient)
    bot.toLower(entity)
