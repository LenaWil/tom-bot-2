#!/bin/bash

HOME=/home/pi
VENVDIR=$HOME/.virtualenvs/tombot
CONFIGPATH=~/tombot/production.config

source $VENVDIR/bin/activate
cd ~/tombot
tombot-run $CONFIGPATH
RETURN_CODE=$?
if [[ $RETURN_CODE -eq 1 ]]
	then pb push "Tombot has died."
fi
exit $RETURN_CODE
