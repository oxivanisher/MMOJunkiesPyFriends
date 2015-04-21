#!/bin/bash
# http://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xiv-i18n-and-l10n

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

APPDIR=$DIR/../mmofriends/
TRANSLATIONDIR=$APPDIR/translations
MESSAGES=$TRANSLATIONDIR/messages.pot
RUNCOMPILE=true

PYBABEL=$(whereis pybabel)
if [ "z" = "z$PYBABEL" ];
then
	PYBABEL=/opt/local/Library/Frameworks/Python.framework/Versions/2.7/bin/pybabel
fi
echo "Using pybabel from: $PYBABEL"

echo "Extracting strings"
$PYBABEL extract -F $DIR/../config/babel.cfg -o $MESSAGES $APPDIR

for L in de es;
do
	if [ ! -d "$TRANSLATIONDIR/$L" ];
	then
		echo "Initializing language $L"
		$PYBABEL init -i $MESSAGES -d $TRANSLATIONDIR -l $L
		RUNCOMPILE=false
	fi
done

echo "Searching new strings"
$PYBABEL update -i $MESSAGES -d $TRANSLATIONDIR

if [ $RUNCOMPILE ];
then
	echo "Compiling languages"
	$PYBABEL compile -d $TRANSLATIONDIR
fi
