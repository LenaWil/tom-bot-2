''' Contains date/time finding logic. '''
import re
from collections import namedtuple
from datetime import timedelta


YEAR_WORDS      = ['y', 'j', 'jaar', 'jaren', 'years', 'year']
WEEK_WORDS      = ['w', 'weeks', 'week', 'weken']
DAY_WORDS       = ['d', 'dag', 'dagen', 'day', 'days']
HOUR_WORDS      = ['h', 'hr', 'hrs', 'hours', 'hour', 'u', 'uur', 'uren']
MINUTE_WORDS    = ['m', 'min', 'mins', 'minute', 'minutes', 'minuten', 'minuut']
SECOND_WORDS    = ['s', 'sec', 'secs', 'second', 'seconds', 'seconden']

WORDS = [YEAR_WORDS, WEEK_WORDS, DAY_WORDS, HOUR_WORDS, MINUTE_WORDS, SECOND_WORDS]
for list in WORDS:
    list.sort(key=len, reverse=True)

YEAR_PART       = '((?P<years>\d+)\s*?({}))?'.format('|'.join(YEAR_WORDS))
WEEK_PART       = '((?P<weeks>\d+)\s*?({}))?'.format('|'.join(WEEK_WORDS))
DAY_PART        = '((?P<days>\d+)\s*?({}))?'.format('|'.join(DAY_WORDS))
HOUR_PART       = '((?P<hours>\d+)\s*?({}))?'.format('|'.join(HOUR_WORDS))
MINUTE_PART     = '((?P<minutes>\d+)\s*?({}))?'.format('|'.join(MINUTE_WORDS))
SECOND_PART     = '((?P<seconds>\d+)\s*?({}))?'.format('|'.join(SECOND_WORDS))

FUTURE_MARKERS  = ['in', 'over', 'na']
SEPARATORS      = [r'\s', ',', 'en', 'and', '&']
SEP_PART        = '({})*'.format('|'.join(SEPARATORS))

MONSTER         = SEP_PART.join([YEAR_PART, WEEK_PART, DAY_PART, HOUR_PART, MINUTE_PART, SECOND_PART])
REGEX           = re.compile(MONSTER, re.IGNORECASE)
print(MONSTER)

Dinges = namedtuple('Dinges', 'years days hours minutes seconds')
def find_timedelta(text):
    matches = REGEX.findall(text)
    for res in matches:
        if any(res):
            match = res
            break
    years   = int(match[1]) if match[1] else 0
    weeks   = int(match[5]) if match[5] else 0
    days    = int(match[9]) if match[9] else 0
    tdays   = days + 7 * weeks
    hours   = int(match[13]) if match[13] else 0
    minutes = int(match[17]) if match[17] else 0
    seconds = int(match[21]) if match[21] else 0
    result  = Dinges(
        years=years, days=tdays, hours=hours,
        minutes=minutes, seconds=seconds)
    return result
