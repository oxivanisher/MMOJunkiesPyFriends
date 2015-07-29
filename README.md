MMOJunkiesPyFriends
===================

Website friends system to connect friends from different game sources, used for https://mmojunkies.net.


Ressources:
https://dev.battle.net
http://steamcommunity.com/dev
http://voicecommandcenter.com/knowledgebase/24/Teamspeak-3-FAQ.html
http://community.mybb.com/thread-117220.html
https://support.teamspeakusa.com/index.php?/Knowledgebase/List/Index/10/english#ts3_integrate_userdb
http://media.teamspeak.com/ts3_literature/TeamSpeak%203%20Server%20Query%20Manual.pdf
http://stackoverflow.com/questions/1811730/how-do-i-work-with-a-git-repository-within-another-repository
http://us.battle.net/en/forum/topic/13977917832#4

Libs:
https://github.com/nikdoof/python-ts3
http://flask.pocoo.org/
http://jquery.com/
http://jqueryui.com/
http://getbootstrap.com/

# Ideas for the future:
- make a comment on all sites (logged in) to the dev
- make network inking with a dialog popup and finally reload the page
- statistic and/or ranking feature (lol, starcraft, ...)

# Install needed libs (debian)
pip install requests

# Tips and Tricks
## GIT Submodules
git submodule foreach git pull
git submodule update --init

## Generate new application secret
import os
os.urandom(24) 

## useful links:
http://stackoverflow.com/questions/9692962/flask-sqlalchemy-import-context-issue/9695045#9695045

## flask tutorial: Sign in with Steam ID
http://flask.pocoo.org/snippets/42/
#  pip install Flask-OpenID

## Important bugfix URL's:
- http://stackoverflow.com/questions/29134512/insecureplatformwarning-a-true-sslcontext-object-is-not-available-this-prevent

## Twitch URL
https://github.com/justintv/Twitch-API/blob/master/authentication.md

## start redis server on osx
sudo redis-server /opt/local/etc/redis.conf
