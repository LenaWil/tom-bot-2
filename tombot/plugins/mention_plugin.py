'''
Provides hooks to handle @mentions.

Requires setup via the users plugin!

Mentions are based on the twitter-like @username notation. When a @username
is detected in a message, the username (nick) is looked up, and the message
time is compared to the time of the last seen message of the user. If the
last message is equal to or greather than their timeout, a copy of the
message is CC'd directly to the user.
This is useful for 'productive' chats with many messages.
'''
import re
import datetime

from yowsup.layers.protocol_messages.protocolentities import TextMessageProtocolEntity

from tombot.helper_functions import determine_sender, extract_query
from .registry import register_command, message_handler, get_easy_logger
from .users_plugin import jid_to_nick, nick_to_jid, nick_to_id, isadmin


LOGGER = get_easy_logger('plugins.users.mentions')
MENTION_PATTERN = r'(?<!\w)@\s?([^ .:,]+)[ .:,]?'
MENTION_REGEX = re.compile(MENTION_PATTERN, re.IGNORECASE)

@message_handler
def mention_handler_cb(bot, message, *args, **kwargs):
    '''
    Scans message text for @mentions and notifies user if appropriate.
    '''
    mentioned_sent = []
    for nick in MENTION_REGEX.findall(message.getBody()):
        LOGGER.debug('Nick detected: %s', nick)

        # Who sent the message?
        senderjid = determine_sender(message)
        LOGGER.debug('Resolving sender %s', senderjid)
        try:
            sendername = jid_to_nick(bot, senderjid)
            LOGGER.debug('Sendernick %s', sendername)
        except KeyError:
            sendername = senderjid
            LOGGER.debug('Could not find jid %s', senderjid)

        # Who was mentioned?
        try:
            targetjid = nick_to_jid(bot, nick)
        except KeyError as ex:
            # Some nick that is unknown, pass
            LOGGER.debug('Could not resolve nick %s', nick)
            LOGGER.debug('Exception %s', ex)
            continue

        if targetjid not in mentioned_sent:
            # Check timeout
            t_info = get_jid_timeout(bot, targetjid)
            currenttime = (datetime.datetime.now() - datetime.datetime(
                1970, 1, 1)).total_seconds()
            if currenttime < (t_info[1] + t_info[0]) and message.participant:
                # Do not send DM if recipient has not timed out yet
                continue

            # Send mention notification: [author]: [body]
            entity = TextMessageProtocolEntity('{}: {}'.format(
                sendername, message.getBody()), to=targetjid)
            bot.toLower(entity)
            mentioned_sent.append(targetjid)

@message_handler
def update_lastseen_cb(bot, message, *args, **kwargs):
    ''' Updates the user's last seen time in the database. '''
    author = determine_sender(message)
    currenttime = (datetime.datetime.now() - datetime.datetime(1970, 1, 1)).total_seconds()
    LOGGER.debug('Updating %s\'s last seen.', author)
    bot.cursor.execute('UPDATE users SET lastactive = ?, message = ? WHERE jid = ?',
                       (currenttime, message.getBody().decode('utf-8'), author))
    bot.conn.commit()

@register_command(['timeout', 'settimeout'], 'mentions')
def get_jid_timeout(self, jid):
    '''
    Retrieve a user's lastactive and timeout.

    Returns a (timeout, lastactive) tuple.
    Raises KeyError if jid not known.
    '''
    self.cursor.execute(
        'SELECT timeout, lastactive FROM users WHERE jid = ?',
        (jid,))
    result = self.cursor.fetchone()

    if result:
        return result

    raise KeyError('Unknown jid {}'.format(jid))

@register_command(['timeout', 'settimeout'], 'mentions')
def set_own_timeout_cb(bot, message, *args, **kwargs):
    '''
    Update your mention timeout.

    Your timeout is the amount of time (in seconds) that has to elapse before you receive @mentions.
    A value of 0 means you receive all mentions.
    '''
    try:
        cmd = extract_query(message)
        timeout = int(cmd)
        bot.cursor.execute('UPDATE users SET timeout = ? WHERE jid = ?',
                           (timeout, determine_sender(message)))
        bot.conn.commit()
        return 'Ok'
    except ValueError:
        LOGGER.error('Timeout set failure: %s', cmd)
        return 'IT BROKE'

# Admin
@register_command('ftimeout', 'mentions', hidden=True)
def set_other_timeout_cb(bot, message, *args, **kwargs):
    '''
    Update the timeout of any user.

    Specify user by id or nick.
    '''
    if not isadmin(bot, message):
        return
    try:
        cmd = extract_query(message)
        cmdl = cmd.split()
        if cmdl[0].isdigit():
            id_ = int(cmdl[0])
        else:
            try:
                id_ = nick_to_id(bot, cmdl[0])
            except KeyError:
                return 'Unknown nick.'
        timeout = int(cmdl[1])
        bot.cursor.execute('UPDATE users SET timeout = ? WHERE id = ?',
                           (timeout, id_))
        bot.conn.commit()
        return 'Timeout for user updated to {}'.format(id_)
    except ValueError:
        return 'IT BROKE'
