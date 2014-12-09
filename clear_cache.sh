#!/bin/bash

# Getting script directory.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# create new inore list:
# ignore=(".keep" "icon_0" "icon_100" "icon_200" "icon_300" "icon_500" "icon_600")
# echo $(printf -- '! -iname "%s" ' "${ignore[@]:1}")

# removing old files
find ${DIR}/mmofriends/static/cache -ctime +1 -type f ! -iname ".keep" ! -iname "icon_0" ! -iname "icon_100" ! -iname "icon_200" ! -iname "icon_300" ! -iname "icon_500" ! -iname "icon_600" -exec rm {} \;