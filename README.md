MMOJunkiesPyFriends
===================

Website friends system to connect friends from different game sources.

Planned is:
- Connect friends from Battle.Net (Blizzard)
- Steam (Valve)

And let them register a TS3 account for our TS3 Server.


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

Notes:
	Ts3 Console:
		- clientlist [-uid] [-away] [-voice] [-times] [-groups] [-info] [-icon] [-country]
		- clientfind pattern={clientName}
		- clientinfo clid={clientID} 

		- clientdblist [start={offset}] [duration={limit}] [-count]
		- clientpoke clid={clientID}… msg={text}
		- clientdbfind pattern={clientName|clientUID} [-uid]
		- clientdbedit cldbid={clientDBID} [client_properties…]
		- clientdbdelete cldbid={clientDBID}
		- clientkick clid={clientID}… reasonid={4|5} [reasonmsg={text}]

		- sendtextmessage targetmode={1-3} target={serverID|channelID|clientID} msg={text}

	Targetmodes:
		1: target is a client
		2: target is a channel
		3: target is a virtual serve


git submodule foreach git pull