'''
Provides a command for scheduling reminders.

Never forget.
'''
import datetime

import dateutil.parser
from yowsup.layers.protocol_messages.protocolentities \
        import TextMessageProtocolEntity

from .registry import register_command, get_easy_logger
from tombot.helper_functions import extract_query, determine_sender, reply_directly
import tombot.datefinder as datefinder
import tombot.rpc as rpc

LOGGER = get_easy_logger('plugins.reminder')

@register_command(['remind', 'remindme'])
@reply_directly
def addreminder_cb(bot, message, *args, **kwargs):
    ''' (Hopefully) sends user a message at the given time '''
    body = extract_query(message)
    timespec = body.split()[0]
    try:
        trytime = dateutil.parser.parse(body, parserinfo=datefinder.BPI, fuzzy=True)
    except ValueError:
        trytime = datetime.datetime(1970, 1, 1) # job is dropped if no other date is found
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
            LOGGER.error('Cannot find time in "%s"', body)
    if delta:
        deadline = delta
    else:
        deadline = trytime
    LOGGER.debug('Parsed reminder command "%s"', body)
    LOGGER.info('Deadline %s from message "%s".',
                deadline, body)
    reply = 'Reminder set for {}.'.format(deadline)
    replymessage = TextMessageProtocolEntity(
        to=determine_sender(message), body=reply)
    bot.toLower(replymessage)
    bot.scheduler.add_job(
        rpc.remote_send, 'date',
        [body, determine_sender(message)],
        run_date=deadline)
    return
