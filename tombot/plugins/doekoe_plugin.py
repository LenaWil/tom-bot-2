# coding: utf-8
'''
Doekoe: bereken wanneer je geld krijgt.

Deze module bevat een commando om te berekenen wanneer verschillende uitbetalingen
plaatsvinden, zie de docstring van doekoe().
'''
from __future__ import print_function
from collections import namedtuple
import datetime
from datetime import date

from dateutil.relativedelta import relativedelta
import dateutil.rrule
from dateutil.rrule import rrule
from apscheduler.jobstores.base import JobLookupError

import tombot.rpc
from .registry import register_command, get_easy_logger, register_startup, register_shutdown


LOGGER = get_easy_logger('plugins.doekoe')
Rule = namedtuple('rule', 'name rule relocator')

def doekoe_neo(relative_to=datetime.datetime.today()):
    '''
    Bereken wanneer de uitbetalingen in RULES gebeuren.

    Vraag uw specialist en/of gebruik uw ogen om de inhoud van RULES te achterhalen.
    '''
    result = ''

    for item in next_occurrences(relative_to):
        if item[1] == relative_to.date():
            result += '{} is vandaag! ({})\n'.format(
                item[0].name, item[1])
        else:
            delta = relativedelta(item[1], relative_to)
            numdays = delta.days
            word = 'dag' if numdays == 1 else 'dagen'
            result += '{} komt over {} {}. ({})\n'.format(
                item[0].name, numdays, word, item[1])

    result += '\n\nAan deze informatie kunnen geen rechten worden ontleend.'
    return result

def next_occurrences(relative_to=datetime.datetime.today()):
    '''
    Calculate when the rules in RULES will next fire.
    Returns a list of (Rule, datetime.date) tuples.
    '''
    result = []
    for rule in RULES:
        yesterday = relative_to - datetime.timedelta(days=1)
        naive_next = rule.rule.after(yesterday)
        actual_next = rule.relocator(naive_next)
        result.append((rule, actual_next))

    return result

def which_today(relative_to=datetime.datetime.today()):
    ''' List all events which should happen on the same date as relative_to. '''
    todays_events = [x[0].name for x in next_occurrences(relative_to)
                     if x[1] == date.today()]
    return todays_events

def midnight_announce_cb(recipient, *args, **kwargs):
    '''
    Callback to announce if a doekoe_event is scheduled for the day.
    '''
    LOGGER.info('Checking for doekoe_events to announce...')
    todays_events = which_today()
    if not todays_events:
        LOGGER.info('No events to announce, returning.')
        return

    LOGGER.info('Announcing %s.', ', '.join(todays_events))
    result = 'Vandaag {} {}!'.format(
        'komt' if len(todays_events) == 1 else 'komen',
        ', '.join(todays_events))
    tombot.rpc.remote_send(result, recipient)
    LOGGER.info('Done.')

@register_startup
def add_midnight_announce_cb(bot, *args, **kwargs):
    '''
    Wrapper om de voornoemde callback te registreren.
    '''
    LOGGER.info('Registering doekoeannouncer.')
    bot.scheduler.add_job(
        midnight_announce_cb,
        'cron', hour=0, minute=0, second=30,
        coalesce=True, misfire_grace_time=10,
        id='plugins.doekoe.midnight',
        args=(bot.config['Jids']['announce-group'],),
        replace_existing=True,
        *args, **kwargs)

@register_shutdown
def rem_midnight_announce_cb(bot, *args, **kwargs):
    '''
    Verwijder announcer bij afsluiten om geen dubbele jobs te krijgen.
    '''
    LOGGER.info('Deregistering doekoeannouncer.')
    try:
        bot.scheduler.remove_job('plugins.doekoe.midnight')
    except JobLookupError:
        pass

def doekoe():
    '''
    Bereken wanneer verschillende uitbetalingen gebeuren.

    De huidige uitbetalingen zijn:
      - SAH Loon: de eerstvolgende 8e van een maand
      - Zorgtoeslag: de eerste werkdag na de 20e
      - Studiefinanciëring: de laatste werkdag voor de 24e
    '''
    res = ""
    today = date.today()
    next_month = today + relativedelta(months=1)

    # Loon: Eerstvolgende 8e van de maand
    if today.day == 8:
        res += 'Loon is vandaag!\n'
    elif today.day < 8:
        loondag = date(today.year, today.month, 8)
        res += 'Loon komt over {} {}. ({})\n'.format(
            8-today.day, 'dag' if 8-today.day < 2 else 'dagen', loondag.isoformat())
    else:
        loondag = date(next_month.year, next_month.month, 8)
        delta = relativedelta(loondag, today)
        res += 'Loon komt over {} {}. ({})\n'.format(
            delta.days, 'dag' if delta.days < 2 else 'dagen', loondag.isoformat())

    # Zorgtoeslag: eerste werkdag na de 20e
    ztdag = first_weekday_after(date(today.year, today.month, 20))

    if today > ztdag:
        ztdag = first_weekday_after(date(next_month.year, next_month.month, 20))

    if today == ztdag:
        res += 'Zorgtoeslag is vandaag! ({})\n'.format(ztdag.isoformat())
    else:
        delta = relativedelta(ztdag, today)
        res += 'Zorgtoeslag komt over {} {}. ({})\n'.format(
            delta.days, 'dag' if delta.days < 2 else 'dagen', ztdag.isoformat())

    # Stufi: laatste werkdag voor de 24e
    stufidag = last_weekday_before(date(today.year, today.month, 24))

    if today > stufidag:  # volgende maand berekenen
        stufidag = last_weekday_before(date(next_month.year, next_month.month, 24))

    if today == stufidag:
        res += 'Stufi is vandaag! ({})\n'.format(stufidag.isoformat())
    else:
        delta = relativedelta(stufidag, today)
        res += 'Stufi komt over {} {}. ({})\n'.format(
            delta.days, 'dag' if delta.days < 2 else 'dagen', stufidag.isoformat())

    res += '\nAan deze informatie kunnen geen rechten worden ontleend.'
    return res

@register_command(['doekoe', 'duku', 'geld', 'gheldt', 'munnie', 'moneys', 'cash'])
def doekoe_cb(*args, **kwargs):
    '''
    Tel af tot wanneer je weer geld krijgt.

    De huidige uitbetalingen zijn:
      - SAH Loon: de eerstvolgende 8e van een maand
      - AH-loon: gekte, iets met vier weken
      - De Fancy-loon: eerste werkdag na de volgende 21e
      - Zorgtoeslag: de eerste werkdag na de 20e
      - Studiefinanciëring: de laatste werkdag voor de 24e
    Noch de makers, noch de bot zelf is of zijn verantwoordelijk, aansprakelijk \
    of bedreigbaar in het waarschijnlijke geval dat de gegeven info eens niet klopt.
    '''
    return doekoe_neo()

def first_weekday_after(arg):
    '''
    Find the first weekday on or after the given date.

    If the argument is a Saturday or Sunday, the Monday after is returned.
    '''
    if hasattr(arg, 'date'):
        arg = arg.date()
    if arg.weekday() < 5:
        return arg
    return arg + relativedelta(days=7 - arg.weekday())

def last_weekday_before(arg):
    '''
    Find the first weekday on or before the given date.

    If the argument is a Saturday or Sunday, the preceding Friday is returned.
    '''
    if hasattr(arg, 'date'):
        arg = arg.date()
    if arg.weekday() < 5:
        return arg
    return arg + relativedelta(days=4 - arg.weekday())

RULES = [
    Rule('SaH-loon',
         rrule(dateutil.rrule.MONTHLY, bymonthday=8),
         lambda x: x.date()),
    Rule('AH-loon',
         rrule(dateutil.rrule.WEEKLY, interval=4,
               dtstart=date(2016, 3, 7), cache=True),
         first_weekday_after),
    Rule('Defensie-loon',
         rrule(dateutil.rrule.MONTHLY, bymonthday=21,
               cache=True),
         first_weekday_after),
    Rule('Zorgtoeslag',
         rrule(dateutil.rrule.MONTHLY, bymonthday=20,
               cache=True),
         first_weekday_after),
    Rule('Stufi',
         rrule(dateutil.rrule.MONTHLY, bymonthday=24,
               cache=True),
         last_weekday_before),
    ]

if __name__ == '__main__':
    print(doekoe_neo())
