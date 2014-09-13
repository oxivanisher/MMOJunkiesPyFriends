#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Saving origin path
ORIGDIR=$(pwd)

# Cleaning old .pyc files to not run into the "importing seems to work" trap again!
find ${DIR} -name *.pyc -exec rm {} \;

# Changing to the root path of th application
cd ${DIR}

# Actually starting the application
python mmofriends.py

# Changing back to origin path
cd ${ORIGDIR}