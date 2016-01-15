''' Tombot, a chatbot for WhatsApp. '''

import gettext
import os
LOCALE_DIR = os.path.join(os.path.dirname(__file__), 'locales')
_ = gettext.gettext
gettext.install('tombot', LOCALE_DIR)
