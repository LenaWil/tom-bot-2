''' Twoekoe: calculate when munnie '''
from __future__ import print_function
from datetime import date
from dateutil.relativedelta import relativedelta


def doekoe():
    ''' Doekoe: zie wanneer je weer geld krijgt '''
    res = ""
    today = date.today()
    next_month = today + relativedelta(months=1)

    # Loon: Eerstvolgende 8e van de maand
    if today.day == 8:
        res += 'Loon is vandaag!\n'
    elif today.day < 8:
        res += 'Loon komt over {} {}.\n'.format(
            8-today.day, 'dag' if 8-today.day < 2 else 'dagen')
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
        res += 'Stufi komt vandaag! ({})\n'.format(stufidag.isoformat())
    else:
        delta = relativedelta(stufidag, today)
        res += 'Stufi komt over {} {}. ({})\n'.format(
            delta.days, 'dag' if delta.days < 2 else 'dagen', stufidag.isoformat())

    res += '\nAan deze informatie kunnen geen rechten worden ontleend.'
    return res

def first_weekday_after(arg):
    ''' Finds the first weekday on or after the given date. '''
    if arg.weekday() < 5:
        return arg
    return arg + relativedelta(days=7 - arg.weekday())

def last_weekday_before(arg):
    ''' Returns the first weekday on or before the given date. '''
    if arg.weekday() < 5:
        return arg
    return arg + relativedelta(days=4 - arg.weekday())

if __name__ == '__main__':
    print(doekoe())
