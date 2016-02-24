'''
Provides user and nickname management.
'''
import datetime
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
def collect_users_cb(bot, message=None, *args, **kwargs):
    ''' Detect all users and add them to the 'users' table, if not present. Disabled. '''
    LOGGER.info('Beginning user detection.')
    if not bot.known_groups:
        LOGGER.warning('Groups have not been detected, aborting.')
        return
    for group in bot.known_groups:
        for user in group.getParticipants().keys():
            LOGGER.info('User: %s', user)
            bot.cursor.execute('SELECT COUNT(*) FROM users WHERE jid = ?',
                               (user,))
            result = bot.cursor.fetchone()[0]
            if result == 0:
                LOGGER.info('User not yet present in database, adding...')
                currenttime = (datetime.datetime.now() -
                               datetime.datetime(1970, 1, 1)).total_seconds()
                default_timeout = 2 * 60 * 60 # 2 hours
                bot.cursor.execute('''INSERT INTO USERS
                    (jid, lastactive, timeout, admin) VALUES (?, ?, ?, ?)
                ''', (user, currenttime, default_timeout, False))
                LOGGER.info('User added.')
            else:
                LOGGER.info('User present.')
        bot.conn.commit()

@register_command('gns')
def get_nameless_seen_cb(bot, message, *args, **kwargs):
    ''' List all jids which have been heard by the bot, but have no primary nick. '''
    if not isadmin(bot, message):
        return
    bot.cursor.execute(
        'SELECT id,message,jid FROM users WHERE primary_nick IS NULL AND message IS NOT NULL')
    results = bot.cursor.fetchall()
    result = 'Non-registered but seen talking:\n'
    for user in results:
        result += '{} ({}): {}\n'.format(user[0], user[2], user[1])
    return result

@register_command('register')
def register_user_cb(bot, message, *args, **kwargs):
    ''' Assign a primary nick to a user. '''
    if not isadmin(bot, message):
        return
    cmd = extract_query(message)
    try:
        cmdl = cmd.split()
        id_ = int(cmdl[0])
        name = cmdl[1]
        bot.cursor.execute('UPDATE users SET primary_nick = ? WHERE id = ?',
                           (name, id_))
        bot.conn.commit()
        LOGGER.info(bot.cursor.rowcount)
        LOGGER.info('User %s registered as %s.', id_, name)
        return 'Ok'
    except IndexError as ex:
        LOGGER.warning('Invalid message')
        LOGGER.warning(ex)
        return 'Malformed command'
    except sqlite3.IntegrityError as ex:
        LOGGER.error('Error during register')
        LOGGER.error(ex)
        return 'Error'

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

def nick_to_id(bot, nick):
    '''
    Map a nick to a userid.

    Raises KeyError if id not known.
    '''
    jid = nick_to_jid(bot, nick)
    query = 'SELECT id FROM users WHERE jid = ?'
    bot.cursor.execute(query, (jid,))
    result = bot.cursor.fetchone()
    if result:
        return result[0]

    # This will never happen, nick_to_jid raises earlier.
    raise KeyError('Unknown nick {}'.format(jid))

# Authorization etc.
@register_command('isadmin')
def isadmin_cb(bot, message, *args, **kwargs):
    ''' Check whether the sender has admin rights. '''
    if isadmin(bot, message):
        return 'Yes!'
    return 'No'

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
