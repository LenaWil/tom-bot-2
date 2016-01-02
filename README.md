# Tom-bot: a bot for Whatsapp
Tom-bot is a bot that is intended to go on a specific group chat to respond to queries, currently it can do this:
- 8ball: responds with a random 8ball quote
- Ping: pong
- Fortune: responds with a random fortune from a random fortune file in the dir fortunes/
- Roll: generate random numbers, format `xdy [(+|-) modifier]`
- Shutdown: does not respond, ends process. (User must be in the config file)
- Restart: Exits the bot with a non-zero exit code, so it can be restarted by a service manager and/or script
