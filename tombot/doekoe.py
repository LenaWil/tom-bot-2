''' Twoekoe: calculate when munnie '''
from __future__ import print_function
from datetime import date
from dateutil.relativedelta import relativedelta


def doekoe():
    ''' Doekoe: zie wanneer je weer geld krijgt '''
    # pylint: disable=too-many-branches
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
    ztdag = date(today.year, today.month, 20)
    if ztdag.weekday() > 4:
        ztdag = date(today.year, today.month, 20 + 7 - ztdag.weekday())

    if today > ztdag:
        ztdag = date(next_month.year, next_month.month, 20)
        if ztdag.weekday() > 4:
            ztdag = date(next_month.year, next_month.month, 20 + 7 - ztdag.weekday())

    if today == ztdag:
        res += 'Zorgtoeslag is vandaag! ({})\n'.format(ztdag.isoformat())
    else:
        delta = relativedelta(ztdag, today)
        res += 'Zorgtoeslag komt over {} {}. ({})\n'.format(
            delta.days, 'dag' if delta.days < 2 else 'dagen', ztdag.isoformat())

    # Stufi: eerste werkdag voor de 24e
    stufidag = date(today.year, today.month, 24)
    if stufidag.weekday() > 4:
        stufidag = date(today.year, today.month, 24 + (4 - stufidag.weekday()))

    if today > stufidag:  # volgende maand berekenen
        stufidag = date(next_month.year, next_month.month, 24)
        if stufidag.weekday() > 4:
            stufidag = date(today.year, today.month, 24 + (4 - stufidag.weekday()))

    if today == stufidag:
        res += 'Stufi is vandaag! ({})\n'.format(stufidag.isoformat())
    else:
        delta = relativedelta(stufidag, today)
        res += 'Stufi komt over {} {}. ({})\n'.format(
            delta.days, 'dag' if delta.days < 2 else 'dagen', stufidag.isoformat())

    res += '\nAan deze informatie kunnen geen rechten worden ontleend.'
    return res

if __name__ == '__main__':
    print(doekoe())
