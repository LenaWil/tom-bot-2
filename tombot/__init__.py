import gettext, os
locale_dir = os.path.join(os.path.dirname(__file__), 'locales')
gettext.install('tombot', locale_dir)
