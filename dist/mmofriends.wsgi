import os
import sys

os.environ['MMOFRIENDS_CFG'] = "USERHOME/www_data/wsgi/mmofriends.cfg"

sys.path.insert(0, 'USERHOME/git_checkouts/MMOJunkiesPyFriends/')

from pymoviezweb import app as application
