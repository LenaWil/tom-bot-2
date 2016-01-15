''' Some helper functions used in tombot which do not need the bot state. '''
import logging
import duckduckgo


def byteify(param):
    """
    Helper function to force json deserialize to string and not unicode.
    Written by Mark Amery on https://stackoverflow.com/a/13105359
    """
    if isinstance(param, dict):
        return {byteify(key):byteify(value) for key, value in param.iteritems()}
    elif isinstance(param, list):
        return [byteify(element) for element in param]
    elif isinstance(param, unicode):
        return param.encode('utf-8')
    else:
        return param

def extract_query(message, cmdlength=1):
    """ Removes the command and trigger from the message body, return the stripped text."""
    content = message.getBody()
    if message.participant:
        offset = 1 + cmdlength
    else:
        offset = cmdlength
    return ' '.join(content.split()[offset:])

def determine_sender(message):
    ''' Returns the person who wrote a message. '''
    if message.participant:
        return message.participant
    return message.getFrom()

# The following functions are used in react, but do not need the bot's state.
def forcelog(message):
    ''' Write a message to the log. '''
    logging.info('Forcelog from %s: %s', message.getFrom(), message.getBody())
    return

def ddg_respond(message):
    ''' Answer question using DuckDuckGo instant answer'''
    try:
        query = extract_query(message)
        return duckduckgo.get_zci(query)
    except ValueError:
        return 'Sorry, no results.'
    except AttributeError:
        return 'Sorry, no results.'

# The following functions are used in react but do not use the bot's state,
# or the content of the message.
def ping(message=None):
    ''' Return 'pong' to indicate non-deadness '''
    # pylint: disable=unused-argument
    return _('Pong')

def unknown_command(message=None):
    ''' Return localized version of 'Unknown command!' '''
    # pylint: disable=unused-argument
    return _('Unknown command!')
