#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import Column, Integer, String, UnicodeText, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, backref
from sqlalchemy.exc import IntegrityError, InterfaceError, InvalidRequestError, StatementError, OperationalError

from mmofriends.mmoutils import *
from mmofriends.database import Base

class MMONetworkCache(Base):
    __tablename__ = 'mmonetcache'
    
    id = Column(Integer, primary_key=True)
    network_handle = Column(String(20))
    entry_name = Column(String(20))
    last_update = Column(Integer)
    cache_data = Column(UnicodeText) #MEDIUMTEXT
    
    __table_args__ = (UniqueConstraint(network_handle, entry_name, name="handle_name_uc"), )

    def __init__(self, network_handle, entry_name, cache_data = ""):
        self.network_handle = network_handle
        self.entry_name = entry_name
        self.last_update = 0
        self.cache_data = cache_data

    def __repr__(self):
        return '<MMONetworkCache %r>' % self.id

    def get(self):
        return json.loads(self.cache_data)

    def set(self, cache_data):
        self.cache_data = json.dumps(cache_data)

    def age(self):
        return int(time.time()) - self.last_update