MMOJunkiesPyFriends
===================

Website friends system to connect friends from different game sources, used for https://mmojunkies.net.

## Ideas for the future:
* make a comment feature on all sites/boxes (logged in) to the dev for ideas/improvements
* statistic and/or ranking feature (lol, starcraft, ...)
* groups
* timers
* message board

## Install needed libraries (debian)
```bash
apt-get install python-pip python-dev redis-server
pip install requests rauth numpy Flask-OpenID Flask-SQLAlchemy Flask-Compress Flask-Celery3 PyYAML feedparser celery redis MySQL-python
```

### Install TS3 Lib (do this in some other directory!)
```bash
git clone git://github.com/nikdoof/python-ts3.git
cd python-ts3
python setup.py install
```

## Tips and Tricks
### Init GIT Submodules
```bash
git submodule foreach git pull
git submodule update --init
```

### Unable to write file errors
If there is a problem caching the external image files, check the permissions on "MMOJunkiesPyFriends/mmofriends/static/cache/"

### Generate new application secret
```python
import os
os.urandom(24) 
```

### useful links:
http://stackoverflow.com/questions/9692962/flask-sqlalchemy-import-context-issue/9695045#9695045

### flask tutorial: Sign in with Steam ID
http://flask.pocoo.org/snippets/42/

### Important bugfix URL's:
- http://stackoverflow.com/questions/29134512/insecureplatformwarning-a-true-sslcontext-object-is-not-available-this-prevent

### Twitch URL
https://github.com/justintv/Twitch-API/blob/master/authentication.md

### start redis server on osx
```bash
sudo redis-server /opt/local/etc/redis.conf
```

### pip_update.py
Use this script to update all pip packages to the nwewst version. Especially useful, if you installed some libs via apt-get.
# Debian dependencies for pip update
```bash
apt-get install libmysqlclient-dev libffi-dev libacl1-dev libssl-dev
```

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pip
from subprocess import call

for dist in pip.get_installed_distributions():
    print (":: Checking for %s" % dist.project_name)
    call("pip install --upgrade " + dist.project_name + "", shell=True)
```

## Ressources
* https://dev.battle.net
* http://steamcommunity.com/dev
* http://voicecommandcenter.com/knowledgebase/24/Teamspeak-3-FAQ.html
* http://community.mybb.com/thread-117220.html
* https://support.teamspeakusa.com/index.php?/Knowledgebase/List/Index/10/english#ts3_integrate_userdb
* http://media.teamspeak.com/ts3_literature/TeamSpeak%203%20Server%20Query%20Manual.pdf
* http://stackoverflow.com/questions/1811730/how-do-i-work-with-a-git-repository-within-another-repository
* http://us.battle.net/en/forum/topic/13977917832#4

## Used libs
* https://github.com/nikdoof/python-ts3
* http://flask.pocoo.org/
* http://jquery.com/
* http://jqueryui.com/
* http://getbootstrap.com/