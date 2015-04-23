#!/bin/bash
# http://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xiv-i18n-and-l10n

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

APPDIR=$DIR/../mmofriends/
TRANSLATIONDIR=$APPDIR/translations
MESSAGES=$TRANSLATIONDIR/messages.pot
RUNCOMPILE=true

PYBABEL=$(whereis pybabel|awk '{print $2}')
if [ "z" = "z$PYBABEL" ];
then
	PYBABEL=/opt/local/Library/Frameworks/Python.framework/Versions/2.7/bin/pybabel
fi
echo "Using pybabel from: $PYBABEL"

if [ $RUNCOMPILE ];
then
	echo "Compiling languages"
	$PYBABEL compile -f -d $TRANSLATIONDIR
fi
