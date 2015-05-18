#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

# from mmofriends import db
db = SQLAlchemy()

class MMOPayPalPayment(db.Model):
    __tablename__ = 'mmopaypalpayment'

    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(255))
    item_number = db.Column(db.String(255))
    custom = db.Column(db.String(255))
    payment_status =  db.Column(db.String(255))
    payment_amount =  db.Column(db.String(255))
    payment_currency =  db.Column(db.String(255))
    payment_type =  db.Column(db.String(255))
    payment_date =  db.Column(db.String(255))
    txn_id =  db.Column(db.String(255))
    txn_type =  db.Column(db.String(255))
    receiver_email =  db.Column(db.String(255))
    receiver_id =  db.Column(db.String(255))
    payer_email =  db.Column(db.String(255))
    test_ipn =  db.Column(db.String(255))
    response_string =  db.Column(db.String(255))
    memo =  db.Column(db.String(255))
    date = db.Column(db.Integer)

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

