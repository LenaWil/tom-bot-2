''' Some helper functions used in tombot which do not need the bot state. '''


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
def unknown_command(message=None):
    ''' Return localized version of 'Unknown command!' '''
    # pylint: disable=unused-argument
    return _('Unknown command!')
