#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from sqlalchemy import Column, Integer, String, UnicodeText, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, backref

from mmofriends.mmoutils import *
from mmofriends.database import Base

class MMOPayPalPayment(Base):
    __tablename__ = 'mmopaypalpayment'

    id = Column(Integer, primary_key=True)
    item_name = Column(String(255))
    item_number = Column(String(255))
    custom = Column(String(255))
    payment_status =  Column(String(255))
    payment_amount =  Column(String(255))
    payment_currency =  Column(String(255))
    payment_type =  Column(String(255))
    payment_date =  Column(String(255))
    txn_id =  Column(String(255))
    txn_type =  Column(String(255))
    receiver_email =  Column(String(255))
    receiver_id =  Column(String(255))
    payer_email =  Column(String(255))
    test_ipn =  Column(String(255))
    response_string =  Column(String(255))
    memo =  Column(String(255))
    date = Column(Integer)

    def __init__(self, item_name, item_number, custom, payment_status, payment_amount, payment_currency, payment_type, payment_date, txn_id, txn_type, receiver_email, receiver_id, payer_email, test_ipn, response_string, memo):
        self.item_name = item_name
        self.item_number = item_number
        self.custom = custom
        self.payment_status = payment_status
        self.payment_amount = payment_amount
        self.payment_currency = payment_currency
        self.payment_type = payment_type
        self.payment_date = payment_date
        self.txn_id = txn_id
        self.txn_type = txn_type
        self.receiver_email = receiver_email
        self.receiver_id = receiver_id
        self.payer_email = payer_email
        self.test_ipn = test_ipn
        self.response_string = response_string
        self.memo = memo
        self.date = int(time.time())

    def __repr__(self):
        return '<MMOPayPalPayment %r>' % self.id

