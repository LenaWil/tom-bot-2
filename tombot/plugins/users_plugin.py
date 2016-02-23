'''
Provides user and nickname management.
'''
from tombot.helper_functions import determine_sender
from .registry import register_command, get_easy_logger


LOGGER = get_easy_logger('plugins.users')

# User
@register_command(['mynicks', 'lsnicks'])
def mynicks_cb(bot, message, *args, **kwargs):
    '''
    List all nicks and some user info of sender.
    '''
    if message.participant:
        return # Gets annoying when used in groups
    sender = determine_sender(message)
    bot.cursor.execute('SELECT id,primary_nick FROM users WHERE jid = ?',
                       (sender,))
    result = bot.cursor.fetchone()
    if result is None:
        return 'Wie ben jij'
    userid = result[0]
    username = result[1]
    bot.cursor.execute('SELECT id,name FROM nicks WHERE jid = ?',
                       (sender,))
    results = bot.cursor.fetchall()
    if results is not None:
        reply = 'Nicknames for {} ({}/{}):'.format(username, sender, userid)
        for row in results:
            reply = reply + '\n' + '{} (id {})'.format(row[1], row[0])
    else:
        reply = 'No nicknames known for number {} (internal id {})'.format(
            sender, userid)
    return reply

# Admin

# Lookup helpers
def nick_to_jid(bot, name):
    '''
    Maps a (nick)name to a jid using either users or nicks.

    Raises KeyError if the name is unknown.
    '''
    # Search authornames first
    queries = [
        'SELECT jid FROM users WHERE primary_nick LIKE ?',
        'SELECT jid FROM nicks WHERE name LIKE ?',
        ]
    for query in queries:
        bot.cursor.execute(query, (name,))
        result = bot.cursor.fetchone()
        if result:
            return result[0]

    raise KeyError('Unknown nick {}!'.format(name))

def jid_to_nick(bot, jid):
    '''
    Map a jid to the user's primary_nick.

    Raises KeyError if user not known.
    '''
    query = 'SELECT primary_nick FROM users WHERE jid = ?'
    bot.cursor.execute(query, (jid,))
    result = bot.cursor.fetchone()
    if result:
        return result[0]

    raise KeyError('Unknown jid {}'.format(jid))

# Authorization etc.
def isadmin(bot, message):
    '''
    Determine whether or not a user can execute admin commands.

    A user can be marked as admin by either the database, or the config file.
    Config file overrides database.
    '''
    sender = determine_sender(message)
    try:
        if bot.config['Admins'][sender]:
            return True
    except KeyError:
        pass
    bot.cursor.execute('SELECT admin FROM users WHERE jid = ?',
                       (sender,))
    result = bot.cursor.fetchone()
    if result:
        if result[0] == 1:
            return True
        return False
    return False
