from setuptools import setup

setup(
        name='tombot',
        version='0.2',
        description='A chatbot for WhatsApp',
        classifiers =[
            'Development Status :: 3 - Alpha',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 2.7',
            ],
        url='http://github.com/maartenberg/tom-bot',
        author_email='maartenberg1+git@gmail.com',
        license='MIT',
        packages=['tombot'],
        install_requires=[
            'wolframalpha',
            'duckduckgo2',
            'configobj',
            ],
        dependency_links=[
            'http://github.com/maartenberg/fortune/tarball/master#egg=fortune-1.1',
            'git://github.com/tgalal/yowsup.git#egg=yowsupgit',
            ],
        entry_points = {
            'console_scripts' : [
                'tombot-run=tombot.run:main',
                'tombot-stop=tombot.rpc:remote_shutdown',
                'tombot-restart=tombot.rpc:remote_restart'
                ],
            },
        zip_safe=False
        )

