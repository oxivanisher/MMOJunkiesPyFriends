#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from sqlalchemy import Column, Integer, String, UnicodeText, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, backref

from mmofriends.mmoutils import *
from mmofriends.database import db_session, Base

class MMOGameLink(Base):
    __tablename__ = 'mmogamelink'

    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey('mmouser.id'))
    user = relationship('MMOUser', backref=backref('gamelinks', lazy='dynamic'))
    network_handle = Column(String(20))
    gameId = Column(String(255))
    link = Column(String(255))
    name = Column(String(255))
    comment = Column(UnicodeText)
    date = Column(Integer)

    __table_args__ = (UniqueConstraint(network_handle, gameId, link, name="net_game_link_uc"), )

    def __init__(self, user_id, network_handle, gameId, link, name = "", comment = "", date = 0):
        self.user_id = user_id
        self.network_handle = network_handle
        self.gameId = gameId
        self.link = link
        self.name = name
        self.comment = comment
        if not date:
            date = int(time.time())
        self.date = date

    def __repr__(self):
        return '<MMOGameLink %r>' % self.id
