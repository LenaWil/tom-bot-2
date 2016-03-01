# coding: utf-8
'''
Doekoe: bereken wanneer je geld krijgt.

Deze module bevat een commando om te berekenen wanneer verschillende uitbetalingen
plaatsvinden, zie de docstring van doekoe().
'''
from __future__ import print_function
from datetime import date
from dateutil.relativedelta import relativedelta
from .registry import register_command


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
      - Zorgtoeslag: de eerste werkdag na de 20e
      - Studiefinanciëring: de laatste werkdag voor de 24e
    '''
    return doekoe()

def first_weekday_after(arg):
    '''
    Find the first weekday on or after the given date.

    If the argument is a Saturday or Sunday, the Monday after is returned.
    '''
    if arg.weekday() < 5:
        return arg
    return arg + relativedelta(days=7 - arg.weekday())

def last_weekday_before(arg):
    '''
    Find the first weekday on or before the given date.

    If the argument is a Saturday or Sunday, the preceding Friday is returned.
    '''
    if arg.weekday() < 5:
        return arg
    return arg + relativedelta(days=4 - arg.weekday())

if __name__ == '__main__':
    print(doekoe())
