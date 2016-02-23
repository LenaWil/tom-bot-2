'''
Provides user and nickname management.
'''
import sqlite3
from tombot.helper_functions import determine_sender, extract_query
from .registry import register_command, get_easy_logger


LOGGER = get_easy_logger('plugins.users')

# User
@register_command(['mynicks', 'lsnicks'])
def list_own_nicks_cb(bot, message, *args, **kwargs):
    '''
    List all your nicks and their id's.

    Nicks can be added using addnick, removed using rmnick.
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

@register_command(['user', 'whois'])
def list_other_nicks_cb(bot, message, *args, **kwargs):
    '''
    List all nicks of another user.

    Specify user by id or nick.
    '''
    if message.participant:
        return
    cmd = extract_query(message)

    if str.isdigit(cmd):
        bot.cursor.execute(
            'SELECT id,jid,lastactive,primary_nick FROM users WHERE id = ?',
            (cmd,))
    else:
        try:
            userjid = bot.nick_to_jid(cmd)
            bot.cursor.execute(
                'SELECT id,jid,lastactive,primary_nick FROM users WHERE jid = ?',
                (userjid,))
        except KeyError:
            return 'Unknown (nick)name'
    result = bot.cursor.fetchone()
    if not result:
        return 'Unknown ID' # nick resolution errors earlier
    reply = 'Nicks for {} ({}/{}):\n'.format(result[3], result[1], result[0])
    bot.cursor.execute('SELECT name FROM nicks WHERE jid = ?',
                       (result[1],))
    results = bot.cursor.fetchall()
    for row in results:
        reply = reply + row[0] + ' '
    return reply

@register_command(['addnick', 'newnick'])
def add_own_nick_cb(bot, message, *args, **kwargs):
    '''
    Add a new nick to yourself.

    Nicknames can be removed using 'rmnick'.
    '''
    if message.participant:
        return
    cmd = extract_query(message)
    cmdl = cmd.split()
    sender = determine_sender(message)
    newnick = cmdl[0].lower()
    if len(newnick) > 16:
        return 'Too long'
    if str.isdigit(newnick):
        return 'Pls'
    try:
        LOGGER.info('Nick %s added to jid %s', newnick, sender)
        bot.cursor.execute('INSERT INTO nicks (name, jid) VALUES (?,?)',
                           (newnick, sender))
        bot.conn.commit()
        return 'Ok.'
    except sqlite3.IntegrityError:
        return 'Nick exists'

@register_command(['rmnick', 'delnick'])
def remove_own_nick_cb(bot, message, *args, **kwargs):
    '''
    Remove one of your nicks.

    Specify a nick by id (see mynicks) or the nick itself.
    '''
    if message.participant:
        return
    cmd = extract_query(message)
    if str.isdigit(cmd):
        bot.cursor.execute('SELECT id,name,jid FROM nicks WHERE id = ?',
                           (cmd,))
    else:
        bot.cursor.execute('SELECT id,name,jid FROM nicks WHERE name = ?',
                           (cmd,))
    result = bot.cursor.fetchone()
    if result is None:
        return 'Unknown nick'
    if result[2] != determine_sender(message):
        return 'That\'s not you'
    bot.cursor.execute('DELETE FROM nicks WHERE id = ?',
                       (result[0],))
    bot.conn.commit()
    LOGGER.info('Nick %s removed.', cmd)
    return 'Ok.'

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
