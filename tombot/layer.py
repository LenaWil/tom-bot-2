''' Contains the Tombot layer, which handles the messages. '''
import os
import sys
import logging
import time
import random
import re
import operator
import urllib
import sqlite3
import datetime
import fortune
import wolframalpha
from .helper_functions import extract_query, determine_sender, ddg_respond
from .helper_functions import forcelog, ping, unknown_command
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


class TomBotLayer(YowInterfaceLayer):
    ''' The tombot layer, a chatbot for WhatsApp. '''
    def __init__(self, config):
        super(self.__class__, self).__init__()
        self.running = True
        self.havegroups = False
        self.config = config
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
        self.load_fortunes()

        # Dice setup:
        dice_regex = \
            r'(?P<number>\d+)d(?P<sides>\d+)\s?((?P<operator>\W)\s?(?P<modifier>\d+))?'
        self.operators = {
            '+': operator.add,
            '-': operator.sub,
            '/': operator.div,
            '*': operator.mul,
            'x': operator.mul,
            '%': operator.mod,
            '^': operator.pow
            }
        self.dice_pattern = re.compile(dice_regex, re.IGNORECASE)

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
                time.sleep(10)
                logging.warning(_('Reconnecting'))
                self.getStack().broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
                return True
            else:
                self.stop()
                return False
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
            self.cursor.execute('SELECT primary_nick FROM users WHERE jid = ?',
                                (senderjid,))
            senderres = self.cursor.fetchone()
            if senderres is not None:
                sendername = senderres[0]
            else:
                sendername = senderjid

            # Who was mentioned?
            self.cursor.execute(
                'SELECT jid,timeout,lastactive FROM users WHERE primary_nick LIKE ?',
                (nick,))
            result = self.cursor.fetchone()
            if result is None:
                self.cursor.execute('SELECT jid FROM nicks WHERE name LIKE ?',
                                    (nick,))
                result = self.cursor.fetchone()
                if result is not None:
                    self.cursor.execute('SELECT jid,timeout,lastactive FROM users WHERE jid LIKE ?',
                                        (result[0],))
                    result = self.cursor.fetchone()

            if result is not None and result[0] not in mentioned_sent:
                # Check timeout
                currenttime = (datetime.datetime.now() - datetime.datetime(
                    1970, 1, 1)).total_seconds()
                if currenttime < (result[2] + result[1]):
                    return

                # Send mention notification: [author]: [body]
                entity = TextMessageProtocolEntity('{}: {}'.format(
                    sendername, message.getBody()), to=result[0])
                self.toLower(entity)
                mentioned_sent.append(result[0])
        # Updating user's last seen is after mentions so mention timeouts can be tested solo
        self.update_lastseen(message)

    @ProtocolEntityCallback('receipt')
    def onReceipt(self, entity):
        ''' Sends acknowledgements for read receipts. '''
        # pylint: disable=invalid-name
        ack = OutgoingAckProtocolEntity(
            entity.getId(), 'receipt', entity.getType(), entity.getFrom())
        self.toLower(ack)

    def load_fortunes(self):
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
        ]

    def react(self, message):
        ''' Generates a response to a message using a response function and sends it. '''
        functions = {  # Has to be inside function because of usage of self
            'HELP'      : self.help,
            'FORCELOG'  : forcelog,
            '8BALL'     : self.eightball,
            'FORTUNE'   : self.fortune,
            'SHUTDOWN'  : self.stopmsg,
            'RESTART'   : self.restartmsg,
            'PING'      : ping,
            'CALCULATE' : self.wolfram,
            'BEREKEN'   : self.wolfram,
            'DEFINE'    : ddg_respond,
            'DDG'       : ddg_respond,
            'ROLL'      : self.diceroll,
            'ADMINCHECK': self.isadmin,
            'COOKIE'    : self.cookie,
            self.koekje      : self.cookie,
            'KOEKJE'    : self.cookie,
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
            if isgroup:
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
        self.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
        self.config.write()
        self.running = False
        if restart:
            sys.exit(3)
        sys.exit(0)

    def eightball(self, message):
        ''' Generate a random response from the eightball special. '''
        # pylint: disable=unused-argument
        return fortune.get_random_fortune(self.specials['eightball.spc'])

    def diceroll(self, message):
        '''Roll dice according to a xdy pattern.'''
        query = extract_query(message)
        match = self.dice_pattern.search(query)
        if match is None:
            return

        number = int(match.group('number'))
        sides = int(match.group('sides'))
        if sides < 0 or number < 0:
            return      # Maar hoe dan
        if number > 50 and message.participant:
            return      # Probably spam

        results = []
        for _ in xrange(number):
            results.append(random.randint(1, sides))
        result = ''
        for item in results:
            result = result + str(item)
            result = result + ' + '
        result = result.rstrip(' + ')
        som = sum(results)
        if len(results) > 1:
            result = result + ' = ' + str(som)
        if match.group(3) != None:
            try:
                modresult = self.operators[match.group('operator')](
                    som, int(match.group('modifier')))
                result = '{orig}, {som} {operator} {modifier} = {modresult}'.format(
                    orig=result, som=som, operator=match.group('operator'),
                    modifier=match.group('modifier'), modresult=modresult)
            except KeyError:
                pass  # unrecognized operator, skip modifier
        return result

    def fortune(self, message):
        ''' Choose a random quote from a random fortune file. '''
        # pylint: disable=unused-argument
        # Feature request: allow file specification, eg fortune discworld always picks discworld
        try:
            file_ = random.choice(self.fortune_files)
            return fortune.get_random_fortune(file_)
        except:
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

    # NewNicks
    def collect_users(self, message=None):
        ''' Detect all users and add them to the 'users' table, if not present. Disabled. '''
        # pylint: disable=unused-argument
        logging.info('Beginning user detection.')
        if not self.havegroups:
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
        except:
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
        except:
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
            self.cursor.execute(
                'SELECT id,jid,lastactive,primary_nick FROM users WHERE primary_nick LIKE ?',
                (cmd,))
        result = self.cursor.fetchone()
        if result is None:
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

    # Nicks
    def has_nick(self, jid):
        ''' Deprecated: return whether a oldstyle nick is known in the config file. '''
        return self.config['Nicks'].has_key(jid)

    def admincheck(self, message):
        ''' Deprecated: message handler that can confirm a user's admin status. '''
        # Doen: vervangen met adminstatus uit database
        if self.isadmin(message):
            return 'Yeh'
        return 'Neh'

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

if __name__ == '__main__':
    sys.exit("This script should be run via run.py and/or the tombot-run command.")
