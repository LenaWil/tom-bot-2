''' Contains date/time finding logic. '''
import re
from datetime import timedelta


YEAR_WORDS = ['y', 'j', 'jaar', 'jaren', 'years', 'year']
WEEK_WORDS = ['w', 'weeks', 'week', 'weken']
DAY_WORDS = ['d', 'dag', 'dagen', 'day', 'days']
HOUR_WORDS = ['h', 'hr', 'hrs', 'hours', 'hour', 'u', 'uur', 'uren']
MINUTE_WORDS = ['m', 'min', 'mins', 'minute', 'minutes', 'minuten', 'minuut']
SECOND_WORDS = ['s', 'sec', 'secs', 'second', 'seconds', 'seconden']

WORDS = [YEAR_WORDS, WEEK_WORDS, DAY_WORDS, HOUR_WORDS, MINUTE_WORDS, SECOND_WORDS]
for item in WORDS:
    item.sort(key=len, reverse=True)

SEPARATORS = [r'\s', ',', 'en', 'and', '&']
SEP_PART = '({})*'.format('|'.join(SEPARATORS))

YEAR_PART = r'((?P<years>\d+)\s*?({}){})?'.format('|'.join(YEAR_WORDS), SEP_PART)
WEEK_PART = r'((?P<weeks>\d+)\s*?({}){})?'.format('|'.join(WEEK_WORDS), SEP_PART)
DAY_PART = r'((?P<days>\d+)\s*?({}){})?'.format('|'.join(DAY_WORDS), SEP_PART)
HOUR_PART = r'((?P<hours>\d+)\s*?({}){})?'.format('|'.join(HOUR_WORDS), SEP_PART)
MINUTE_PART = r'((?P<minutes>\d+)\s*?({}){})?'.format('|'.join(MINUTE_WORDS), SEP_PART)
SECOND_PART = r'((?P<seconds>\d+)\s*?({}))?'.format('|'.join(SECOND_WORDS))

FUTURE_MARKERS = ['in', 'over', 'na']

MONSTER = ''.join([YEAR_PART, WEEK_PART, DAY_PART, HOUR_PART, MINUTE_PART, SECOND_PART])
REGEX = re.compile(MONSTER, re.IGNORECASE)

def find_timedelta(text):
    '''
    (Attempts to) Find the first readable duration in a text and return it as a datetime.

    Argument: the text to search. The regex is horrible, so take care.
    Returns a timedelta, zero-length if no matches.
    '''
    matches = REGEX.findall(text)
    for res in matches:
        if any(res):
            match = res
            break
    years = int(match[1]) if match[1] else 0 # in tdays
    weeks = int(match[5]) if match[5] else 0 # in tdays
    days = int(match[9]) if match[9] else 0 # in tdays
    tdays = days + 7 * weeks + 365 * years
    hours = int(match[13]) if match[13] else 0 # passed
    minutes = int(match[17]) if match[17] else 0 # passed
    seconds = int(match[21]) if match[21] else 0 # passed
    result = timedelta(
        days=tdays, hours=hours, minutes=minutes, seconds=seconds)
    return result

CLOCK_MARKERS = ['om', 'at']
CLOCK_PAT = r'(#! )?((?P<hours>\d{1,2})(:?((?P<minutes>\d{2})(:?(?P<seconds>\d{2}))?)?))'.replace(
    r'#!', '|'.join(CLOCK_MARKERS))
CLOCK_REGEX = re.compile(CLOCK_PAT, re.IGNORECASE)
def find_first_time(text):
    '''
    Find the next occurrence of a clock time, return as datetime.
    '''
    match = CLOCK_REGEX.search(text)
    return match
