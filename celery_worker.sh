#!/bin/bash

# Getting script directory.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Saving origin path.
ORIGDIR=$(pwd)

# Changing to the root path of th application.
cd ${DIR}

# Checking if MMOFRIENDS_CFG is set. If not, use the provided example file.
if [ -z "$MMOFRIENDS_CFG" ]; then
	if [ -f "dist/mmofriends.cfg" ]; then
		echo "Setting MMOFRIENDS_CFG for you. Please use your own settings for production!"
		export MMOFRIENDS_CFG="../dist/mmofriends.cfg"
	else
		export MMOFRIENDS_CFG="../dist/mmofriends.cfg.example"
	fi
fi

# Actually starting the application worker.
celery --autoscale=1,1 --concurrency=4 --app=mmofriends.celery worker

# Changing back to origin path.
cd ${ORIGDIR}
