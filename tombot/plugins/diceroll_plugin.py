'''
Provides dice-rolling command.
'''
import operator
import random
import re
from tombot.helper_functions import extract_query
from tombot.registry import Command

# Dice rolling constants and function
DICE_REGEX = r'(?P<number>\d+)d(?P<sides>\d+)\s?((?P<operator>\W)\s?(?P<modifier>\d+))?'

DICE_PATTERN = re.compile(DICE_REGEX, re.IGNORECASE)

DICE_MODIFIER_OPERATORS = {
    '+': operator.add,
    '-': operator.sub,
    '/': operator.truediv,
    '*': operator.mul,
    'x': operator.mul,
    '%': operator.mod,
    '^': operator.pow,
    }

@Command('roll')
def diceroll_cb(bot, message, *args, **kwargs):
    '''
    Roll some dice!

    Usage: include a 'XdY' pattern somewhere in your message, optionally followed by a modifier.
    Examples:
     - roll 1d6 -> rolls one six-sided die
     - roll 2d10 + 5 -> rolls two ten-sided dice, adds up the result, and adds 5

    Supported operators are: +, -, /, *, % (modulo), ^ (power).
    '''
    query = extract_query(message)
    match = DICE_PATTERN.search(query)
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
            modresult = DICE_MODIFIER_OPERATORS[match.group('operator')](
                som, int(match.group('modifier')))
            result = '{orig}, {som} {operator} {modifier} = {modresult}'.format(
                orig=result, som=som, operator=match.group('operator'),
                modifier=match.group('modifier'), modresult=modresult)
        except KeyError:
            pass  # unrecognized operator, skip modifier
    return result
