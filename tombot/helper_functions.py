def byteify(input):
    """ 
    Helper function to force json deserialize to string and not unicode. 
    Written by Mark Amery on https://stackoverflow.com/a/13105359
    """
    if isinstance(input, dict):
        return {byteify(key):byteify(value) for key,value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input

def extract_query(message, cmdlength = 1):
    """ Remove the command and trigger from the message body, return the stripped text."""
    content = message.getBody()
    if message.participant:
        offset = 1 + cmdlength
    else:
        offset = cmdlength
    return ' '.join(content.split()[offset:])

def determine_sender(message):
    if message.participant:
        return message.participant
    return message.getFrom()
