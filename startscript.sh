#!/bin/bash

HOME=/home/pi
VENVDIR=$HOME/.virtualenvs/tombot

source $VENVDIR/bin/activate
cd ~/tombot
tombot-run ~/tombot/production.config
RETURN_CODE=$?
if [[ $RETURN_CODE -eq 1 ]]
	then pb push "Tombot has died."
fi
exit $RETURN_CODE
