''' Contains the Tombot layer, which handles the messages. '''
import os
import sys
import logging
import time
import random
import re
import urllib
import sqlite3
import datetime
import threading
import wolframalpha
import dateutil.parser
import fortune

from .helper_functions import extract_query, determine_sender, ddg_respond
from .helper_functions import forcelog, ping, unknown_command, diceroll
from .doekoe import doekoe
import tombot.rpc as rpc
import tombot.datefinder as datefinder
from yowsup.layers.interface \
        import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers \
        import YowLayerEvent
from yowsup.layers.network \
        import YowNetworkLayer
from yowsup.layers.protocol_messages.protocolentities \
        import TextMessageProtocolEntity
from yowsup.layers.protocol_receipts.protocolentities \
        import OutgoingReceiptProtocolEntity
from yowsup.layers.protocol_acks.protocolentities \
        import OutgoingAckProtocolEntity
from yowsup.layers.protocol_chatstate.protocolentities \
        import OutgoingChatstateProtocolEntity, ChatstateProtocolEntity
from yowsup.layers.protocol_presence.protocolentities \
        import AvailablePresenceProtocolEntity, UnavailablePresenceProtocolEntity


class TomBotLayer(YowInterfaceLayer):
    ''' The tombot layer, a chatbot for WhatsApp. '''
    # pylint: disable=too-many-instance-attributes
    def __init__(self, config, scheduler):
        super(self.__class__, self).__init__()
        self.config = config
        self.scheduler = scheduler
        logging.info('Current working directory: %s', os.getcwd())
        try:
            logging.info('Database location: %s',
                         config['Yowsup']['database'])
            self.conn = sqlite3.connect(config['Yowsup']['database'])
            self.cursor = self.conn.cursor()
        except KeyError:
            logging.critical('Database could not be loaded!')

        # Fortune and specials-setup:
        self.fortune_files = []
        self.specials = {}
        self._load_fortunes()

        # Wolfram Answer API setup
        wolfram_key = config['Keys']['WolframAlpha']
        wolfram_key = os.environ.get('WOLFRAM_APPID', wolfram_key)
        if wolfram_key != 'changeme':
            self.wolfram_client = wolframalpha.Client(wolfram_key)
            logging.info(_('WolframAlpha command enabled.'))
        else:
            self.wolfram_client = None
            logging.warning(_('WolframAlpha command disabled, no API key set.'))

        # Mentioning setup
        mention_regex = r'(?<!\w)@\s?(\w+)[ .:,]?'
        self.mention_pattern = re.compile(mention_regex)

        # Group list holder
        self.known_groups = []

        # Start rpc listener
        host = 'localhost'
        port = 10666
        self.rpcserver = rpc.ThreadedTCPServer((host, port), rpc.ThreadedTCPRequestHandler, self)

        server_thread = threading.Thread(target=self.rpcserver.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        # Start the passed scheduler
        self.scheduler.start()

    @ProtocolEntityCallback('iq')
    def onIq(self, entity):
        ''' Handles incoming IQ messages, currently inactive. '''
        # pylint: disable=invalid-name
        if hasattr(entity, 'groupsList'):
            logging.info('Discovered groups:')
            logging.info(entity.groupsList)
            self.known_groups = entity.groupsList

    def onEvent(self, layerEvent):
        ''' Handles disconnection events and reconnects if we timed out.'''
        # pylint: disable=invalid-name
        logging.debug('Event %s received', layerEvent.getName())
        if layerEvent.getName() == YowNetworkLayer.EVENT_STATE_DISCONNECTED:
            reason = layerEvent.getArg('reason')
            logging.warning(_('Connection lost: {}').format(reason))
            if reason == 'Connection Closed':
                time.sleep(.5)
                logging.warning(_('Reconnecting'))
                self.getStack().broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
                return True
            else:
                self.stop()
                return False
        elif layerEvent.getName() == YowNetworkLayer.EVENT_STATE_CONNECTED:
            logging.info('Connection established.')
            self.set_online()
        return False

    @ProtocolEntityCallback('message')
    def onMessageReceived(self, message):
        ''' Handles incoming messages and responds to them if needed. '''
        # pylint: disable=invalid-name
        logging.debug('Message %s from %s received, content: %s',
                      message.getId(), message.getFrom(), message.getBody())

        receipt = OutgoingReceiptProtocolEntity(
            message.getId(), message.getFrom(),
            'read', message.getParticipant())
        self.toLower(receipt)

        time.sleep(0.2)
        self.react(message)

        # Handle mentions:
        mentioned_sent = []
        # Used to not send multiple messages to the same person if multiple
        # nicks resolve to the same jid
        for nick in self.mention_pattern.findall(message.getBody()):
            logging.debug('Nick detected: %s', nick)

            # Who sent the message?
            senderjid = determine_sender(message)
            logging.debug('Resolving sender %s', senderjid)
            try:
                sendername = self.jid_to_nick(senderjid)
                logging.debug('Sendernick %s', sendername)
            except KeyError:
                sendername = senderjid
                logging.debug('Could not find jid %s', senderjid)

            # Who was mentioned?
            try:
                targetjid = self.nick_to_jid(nick)
            except KeyError as e:
                # Some nick that is unknown, pass
                logging.debug('Could not resolve nick %s', nick)
                logging.debug('Exception %s', e)
                continue

            if targetjid not in mentioned_sent:
                # Check timeout
                t_info = self.get_jid_timeout(targetjid)
                currenttime = (datetime.datetime.now() - datetime.datetime(
                    1970, 1, 1)).total_seconds()
                if currenttime < (t_info[1] + t_info[0]) and message.participant:
                    # Do not send DM if recipient has not timed out yet
                    continue

                # Send mention notification: [author]: [body]
                entity = TextMessageProtocolEntity('{}: {}'.format(
                    sendername, message.getBody()), to=targetjid)
                self.toLower(entity)
                mentioned_sent.append(targetjid)
        # Updating user's last seen is after mentions so mention timeouts can be tested solo
        self.update_lastseen(message)

    @ProtocolEntityCallback('receipt')
    def onReceipt(self, entity):
        ''' Sends acknowledgements for read receipts. '''
        # pylint: disable=invalid-name
        ack = OutgoingAckProtocolEntity(
            entity.getId(), 'receipt', entity.getType(), entity.getFrom())
        self.toLower(ack)

    def _load_fortunes(self):
        ''' Loads fortune and specials files from their directories. '''
        # pylint: disable=unused-variable
        logging.debug(_('Loading specials files.'))
        for root, dirs, files in os.walk('specials/'):
            for file_ in files:
                if not file_.endswith('.spc'):
                    continue
                logging.debug(_('Loading specials file {}'), file_)
                try:
                    filepath = os.path.join(root, file_)
                    fortune.make_fortune_data_file(filepath, True)
                    self.specials[file_] = filepath
                    logging.debug(_('Specials file %s loaded.'), filepath)
                except ValueError as ex:
                    logging.error(_('Specials file %s failed to load: %s'), filepath, ex)

        logging.info(_('Specials loaded.'))

        for root, dirs, files in os.walk('fortunes/'):
            for file_ in files:
                if not file_.endswith('.txt'):
                    continue
                logging.debug(_('Loading fortune file %s'), file_)
                try:
                    filepath = os.path.join(root, file_)
                    fortune.make_fortune_data_file(filepath, True)
                    self.fortune_files.append(filepath)
                    logging.debug(_('Fortune file %s loaded.'), filepath)
                except ValueError as ex:
                    logging.error(_('Fortune file %s failed to load: %s'), filepath, ex)
        logging.info(_('Fortune files loaded.'))

    koekje = '\xf0\x9f\x8d\xaa'

    triggers = [
        'TOMBOT', 'TOMBOT,',
        'BOT', 'BOT,',
        'VRIEZIRI', 'VRIEZIRI,',
        'VICTOR', 'VICTOR,',
        'VIKTOR', 'VIKTOR,',
        'MINION', 'MINION,',
        ]

    def react(self, message):
        ''' Generates a response to a message using a response function and sends it. '''
        functions = {  # Has to be inside function because of usage of self
            'HELP'      : self.help,
            'FORCELOG'  : forcelog,
            '8BALL'     : self.eightball,
            'IS'        : self.eightball,
            'FORTUNE'   : self.fortune,
            'SHUTDOWN'  : self.stopmsg,
            'RESTART'   : self.restartmsg,
            'PING'      : ping,
            'CALCULATE' : self.wolfram,
            'CALC'      : self.wolfram,
            'BEREKEN'   : self.wolfram,
            'DEFINE'    : ddg_respond,
            'DDG'       : ddg_respond,
            'ROLL'      : diceroll,
            'ADMINCHECK': self.isadmin,
            'COOKIE'    : self.cookie,
            self.koekje      : self.cookie,
            'KOEKJE'    : self.cookie,
            'LARS'      : self.lars,
            'LOVEYOU'   : self.lars,
            'DATE'      : self.lars,
            'PICKUP'    : self.lars,
            'DBSETUP'   : self.collect_users,
            'LOGINFO'   : self.loginfo,
            'LOGDEBUG'  : self.logdebug,
            'GNS'       : self.get_nameless_seen,
            'REGISTER'  : self.register_user,
            'FTIMEOUT'  : self.set_other_timeout,
            'TIMEOUT'   : self.set_own_timeout,
            'MYNICKS'   : self.list_own_nicks,
            'ADDNICK'   : self.add_own_nick,
            'RMNICK'    : self.remove_own_nick,
            'USER'      : self.list_other_nicks,
            'DOEKOE'    : lambda x: doekoe(),
            'DUKU'      : lambda x: doekoe(),
            'GELD'      : lambda x: doekoe(),
            'GHELDT'    : lambda x: doekoe(),
            'CASH'      : lambda x: doekoe(),
            'MUNNIE'    : lambda x: doekoe(),
            'MONEYS'    : lambda x: doekoe(),
            'REMINDME'  : self.addreminder,
            'REMIND'    : self.addreminder,
            'BOTHER'    : self.anonsend,
            }
        content = message.getBody()
        text = content.upper().split()
        isgroup = False
        if message.participant:  # A trigger is required in groups
            isgroup = True
            if text[0] not in self.triggers:
                return
            text.remove(text[0])
        try:
            response = functions[text[0]](message)
        except IndexError:
            return
        except KeyError:
            if isgroup or content.startswith('@'):
                return # no 'unknown command!' spam
            response = unknown_command(message)
            logging.debug('Failed command %s', text[0])
        except UnicodeDecodeError as ex:
            response = 'UnicodeDecodeError, see logs.'
            logging.error(ex)
        if response:
            reply_message = TextMessageProtocolEntity(
                response.encode('utf-8'), to=message.getFrom())
            self.toLower(reply_message)

    def anonsend(self, message):
        ''' Send a mention under the group name and not the author's name '''
        if not message.participant:
            return

        try:
            groupname = self.jid_to_nick(message.getFrom())
        except KeyError:
            return 'This group is not enrolled in the BrotherBother program, sorry'

        text = extract_query(message, 2)
        body = '{}: {}'.format(groupname, text)

        # Who was mentioned?
        nick = message.getBody().split()[2]
        try:
            recipient = self.nick_to_jid(nick)
        except KeyError:
            return 'Unknown recipient!'

        entity = TextMessageProtocolEntity(body, to=recipient)
        self.toLower(entity)

    def help(self, message):
        ''' TODO: give an overview of available commands. '''
        # pylint: disable=unused-argument
        return self.koekje.decode('utf-8')

    def cookie(self, message):
        ''' Returns a cookie quote from specials. '''
        # pylint: disable=unused-argument
        return fortune.get_random_fortune(self.specials['cookie.spc']).decode('utf-8')

    def restartmsg(self, message):
        ''' Handle a restart command. '''
        logging.info('Restart message received from %s, content "%s"',
                     message.getFrom(), message.getBody())
        if not self.isadmin(message):
            logging.warning('Unauthorized shutdown attempt from %s',
                            determine_sender(message))
            return self.userwarn()
        self.stop(True)

    def stopmsg(self, message):
        ''' Handle a shutdown command. '''
        logging.info('Stop message received from %s, content "%s"',
                     message.getFrom(), message.getBody())
        if not self.isadmin(message):
            logging.warning('Unauthorized shutdown attempt from %s',
                            determine_sender(message))
            return self.userwarn()
        self.stop()

    def stop(self, restart=False):
        ''' Shut down the bot. '''
        logging.info('Shutting down via stop method.')
        self.set_offline()
        self.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
        self.config.write()
        self.scheduler.shutdown()
        self.rpcserver.shutdown()
        self.rpcserver.server_close()
        if restart:
            sys.exit(3)
        sys.exit(0)

    def eightball(self, message):
        ''' Generate a random response from the eightball special. '''
        # pylint: disable=unused-argument
        return fortune.get_random_fortune(self.specials['eightball.spc'])

    def fortune(self, message):
        ''' Choose a random quote from a random fortune file. '''
        # pylint: disable=unused-argument
        # Feature request: allow file specification, eg fortune discworld always picks discworld
        try:
            file_ = random.choice(self.fortune_files)
            return fortune.get_random_fortune(file_)
        except ValueError:
            return _('Be the quote you want to see on a wall. \n Error message 20XX')

    def userwarn(self):
        ''' Send a random warning from the userwarn special. '''
        try:
            return fortune.get_random_fortune(self.specials['userwarn.spc'])
        except KeyError:
            return "Don't do that"

    def wolfram(self, message):
        ''' Answer question using WolframAlpha API '''
        if not self.wolfram_client:
            return _('Not connected to WolframAlpha!')
        query = extract_query(message)
        logging.debug('Query to WolframAlpha: %s', query)
        entity = OutgoingChatstateProtocolEntity(
            ChatstateProtocolEntity.STATE_TYPING, message.getFrom())
        self.toLower(entity)
        result = self.wolfram_client.query(query)
        entity = OutgoingChatstateProtocolEntity(
            ChatstateProtocolEntity.STATE_PAUSED, message.getFrom())
        self.toLower(entity)
        restext = _('Result from WolframAlpha:\n')
        results = [p.text for p in result.pods
                   if p.title in ('Result', 'Value', 'Decimal approximation', 'Exact result')]
        if len(results) == 0:
            return _('No result.')
        restext += '\n'.join(results) + '\n'
        restext += 'Link: https://wolframalpha.com/input/?i={}'.format(
            urllib.quote(query).replace('%20', '+'))
        return restext

    def lars(self, message):
        ''' Sends (bad) genderless pickupline to sender. '''
        # pylint: disable=unused-argument
        return fortune.get_random_fortune(self.specials['pickupline.spc']).decode('utf-8')

    # NewNicks
    def collect_users(self, message=None):
        ''' Detect all users and add them to the 'users' table, if not present. Disabled. '''
        # pylint: disable=unused-argument
        logging.info('Beginning user detection.')
        if not self.known_groups:
            logging.warning('Groups have not been detected, aborting.')
            return
        for group in self.known_groups:
            for user in group.getParticipants().keys():
                logging.info('User: %s', user)
                self.cursor.execute('SELECT COUNT(*) FROM users WHERE jid = ?',
                                    (user,))
                result = self.cursor.fetchone()[0]
                if result == 0:
                    logging.info('User not yet present in database, adding...')
                    currenttime = (datetime.datetime.now() -
                                   datetime.datetime(1970, 1, 1)).total_seconds()
                    default_timeout = 2 * 60 * 60 # 2 hours
                    self.cursor.execute('''INSERT INTO USERS
                        (jid, lastactive, timeout, admin) VALUES (?, ?, ?, ?)
                    ''', (user, currenttime, default_timeout, False))
                    logging.info('User added.')
                else:
                    logging.info('User present.')
            self.conn.commit()

    def update_lastseen(self, message):
        ''' Update a user's last seen time in the database. '''
        author = determine_sender(message)
        currenttime = (datetime.datetime.now() - datetime.datetime(1970, 1, 1)).total_seconds()
        logging.debug('Updating %s\'s last seen.', author)
        self.cursor.execute('UPDATE users SET lastactive = ?, message = ? WHERE jid = ?',
                            (currenttime, message.getBody().decode('utf-8'), author))
        self.conn.commit()

    def get_nameless_seen(self, message):
        ''' List all jids which have been heard by the bot, but have no primary nick. '''
        if not self.isadmin(message):
            return
        self.cursor.execute(
            'SELECT id,message,jid FROM users WHERE primary_nick IS NULL AND message IS NOT NULL')
        results = self.cursor.fetchall()
        result = 'Non-registered but seen talking:\n'
        for user in results:
            result += '{} ({}): {}\n'.format(user[0], user[2], user[1])
        return result

    def register_user(self, message):
        ''' Assign a primary nick to a user. '''
        if not self.isadmin(message):
            return
        cmd = extract_query(message)
        try:
            cmdl = cmd.split()
            id_ = int(cmdl[0])
            name = cmdl[1]
            self.cursor.execute('UPDATE users SET primary_nick = ? WHERE id = ?',
                                (name, id_))
            self.conn.commit()
            logging.info(self.cursor.rowcount)
            logging.info('User %s registered as %s.', id_, name)
            return 'Ok'
        except IndexError as ex:
            logging.warning('Invalid message')
            logging.warning(ex)
            return 'Malformed command'
        except sqlite3.IntegrityError as ex:
            logging.error('Error during register')
            logging.error(ex)
            return 'Error'

    def set_own_timeout(self, message):
        ''' Update the mention timeout of the sender. '''
        try:
            cmd = extract_query(message)
            timeout = int(cmd)
            self.cursor.execute('UPDATE users SET timeout = ? WHERE jid = ?',
                                (timeout, determine_sender(message)))
            self.conn.commit()
            return 'Ok'
        except ValueError:
            logging.error('Timeout set failure: %s', cmd)
            return 'IT BROKE'

    def set_other_timeout(self, message):
        ''' Update the timeout of any user. '''
        if not self.isadmin(message):
            return
        try:
            cmd = extract_query(message)
            cmdl = cmd.split()
            id_ = int(cmdl[0])
            timeout = int(cmdl[1])
            self.cursor.execute('UPDATE users SET timeout = ? WHERE id = ?',
                                (timeout, id_))
            self.conn.commit()
            return 'Timeout for user updated to {}'.format(id_)
        except ValueError:
            return 'IT BROKE'

    def list_own_nicks(self, message):
        ''' List all nicknames linked to the sender. '''
        if message.participant:
            return
        sender = determine_sender(message)
        self.cursor.execute('SELECT id,primary_nick FROM users WHERE jid = ?',
                            (sender,))
        result = self.cursor.fetchone()
        if result is None:
            return 'Wie ben jij'
        userid = result[0]
        username = result[1]
        self.cursor.execute('SELECT id,name FROM nicks WHERE jid = ?',
                            (sender,))
        results = self.cursor.fetchall()
        if results is not None:
            reply = 'Nicknames for {} ({}/{}):'.format(username, sender, userid)
            for row in results:
                reply = reply + '\n' + '{} (id {})'.format(row[1], row[0])
        else:
            reply = 'No nicknames known for number {} (internal id {})'.format(
                sender, userid)
        return reply

    def list_other_nicks(self, message):
        ''' List all nicks of another user. '''
        if message.participant:
            return
        cmd = extract_query(message)
        if str.isdigit(cmd):
            self.cursor.execute(
                'SELECT id,jid,lastactive,primary_nick FROM users WHERE id = ?',
                (cmd,))
        else:
            try:
                userjid = self.nick_to_jid(cmd)
                self.cursor.execute(
                    'SELECT id,jid,lastactive,primary_nick FROM users WHERE jid = ?',
                    (userjid,))
                result = self.cursor.fetchone()
            except KeyError:
                return 'Ken ik niet'
        reply = 'Nicks for {} ({}/{}):\n'.format(result[3], result[1], result[0])
        self.cursor.execute('SELECT name FROM nicks WHERE jid = ?',
                            (result[1],))
        results = self.cursor.fetchall()
        for row in results:
            reply = reply + row[0] + ' '
        return reply

    def add_own_nick(self, message):
        ''' Link a new nickname to the sender. '''
        if message.participant:
            return
        cmd = extract_query(message)
        cmdl = cmd.split()
        sender = determine_sender(message)
        newnick = cmdl[0].lower()
        if len(newnick) > 16:
            return 'Te lang'
        if str.isdigit(newnick):
            return 'Pls'
        try:
            self.cursor.execute('INSERT INTO nicks (name, jid) VALUES (?,?)',
                                (newnick, sender))
            self.conn.commit()
            return 'Ok.'
        except sqlite3.IntegrityError:
            return 'Bestaat al'

    def add_other_nick(self, message):
        ''' TODO: Link a nickname to another user (admin-only) '''
        pass

    def remove_own_nick(self, message):
        ''' Remove a nickname from the sender. Will fail if another user's nick is targeted. '''
        if message.participant:
            return
        cmd = extract_query(message)
        if str.isdigit(cmd):
            self.cursor.execute('SELECT id,name,jid FROM nicks WHERE id = ?',
                                (cmd,))
        else:
            self.cursor.execute('SELECT id,name,jid FROM nicks WHERE name = ?',
                                (cmd,))
        result = self.cursor.fetchone()
        if result is None:
            return 'Ken ik niet'
        if result[2] != determine_sender(message):
            return 'Dat ben jij niet'
        self.cursor.execute('DELETE FROM nicks WHERE id = ?',
                            (result[0],))
        self.conn.commit()
        logging.info('Nick %s removed.', cmd)
        return 'Ok'

    def remove_other_nick(self, message):
        ''' TODO: Remove a nickname from any user. '''
        # pylint: disable=unused-argument
        pass

    # Remindme and scheduling
    def addreminder(self, message):
        ''' (Hopefully) sends user a message at the given time '''
        body = extract_query(message)
        timespec = body.split()[0]
        trytime = dateutil.parser.parse(body, parserinfo=datefinder.BPI, fuzzy=True)
        delta = None
        if timespec in datefinder.DURATION_MARKERS or datefinder.STRICT_CLOCK_REGEX.match(timespec):
            try:
                delta = datetime.datetime.now() + datefinder.find_timedelta(body)
            except ValueError:
                delta = None
        elif timespec in datefinder.CLOCK_MARKERS:
            try:
                trytime = datefinder.find_first_time(body)
            except ValueError:
                logging.error('Cannot find time in "%s"', body)
        if delta:
            deadline = delta
        else:
            deadline = trytime
        logging.debug('Parsed reminder command "%s"', body)
        logging.info('Deadline %s from message "%s".',
                     deadline, body)
        reply = 'Reminder set for {}.'.format(deadline)
        replymessage = TextMessageProtocolEntity(
            to=determine_sender(message), body=reply)
        self.toLower(replymessage)
        self.scheduler.add_job(
            rpc.remote_send, 'date',
            [body, determine_sender(message)],
            run_date=deadline)
        return

    def nick_to_jid(self, name):
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
            self.cursor.execute(query, (name,))
            result = self.cursor.fetchone()
            if result:
                return result[0]

        raise KeyError('Unknown nick {}!'.format(name))

    def jid_to_nick(self, jid):
        '''
        Map a jid to the user's primary_nick.

        Raises KeyError if user not known.
        '''
        query = 'SELECT primary_nick FROM users WHERE jid = ?'
        self.cursor.execute(query, (jid,))
        result = self.cursor.fetchone()
        if result:
            return result[0]

        raise KeyError('Unknown jid {}'.format(jid))

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

    # Loglevel changes
    def logdebug(self, message=None):
        ''' Temporarily set the loglevel to debug. '''
        if not self.isadmin(message):
            return
        logging.getLogger().setLevel(logging.DEBUG)

    def loginfo(self, message=None):
        ''' Temporarily set the loglevel to info. '''
        if not self.isadmin(message):
            return
        logging.getLogger().setLevel(logging.INFO)

    # Helper functions
    def isadmin(self, message):
        ''' Check whether the sender of a message is listed as an admin. '''
        # Doen: Use admin field from database, instead of / alongside configfile.
        sender = determine_sender(message)
        try:
            if self.config['Admins'][sender]:
                return True
        except KeyError:
            return False
        return False

    def set_online(self, *_):
        ''' Set presence as available '''
        logging.debug('Setting presence online.')
        entity = AvailablePresenceProtocolEntity()
        self.toLower(entity)

    def set_offline(self, *_):
        ''' Set presence as unavailable '''
        logging.debug('Setting presence offline.')
        entity = UnavailablePresenceProtocolEntity()
        self.toLower(entity)

if __name__ == '__main__':
    sys.exit("This script should be run via run.py and/or the tombot-run command.")
