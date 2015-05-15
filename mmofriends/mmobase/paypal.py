#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mmofriends import db

class MMOPayPalPaymant(db.Model):
    __tablename__ = 'mmopaypalpayment'

    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(255))
    item_number = db.Column(db.String(255))
    custom = db.Column(db.String(255))
    payment_status =  db.Column(db.String(255))
    payment_amount =  db.Column(db.String(255))
    payment_currency =  db.Column(db.String(255))
    payment_type =  db.Column(db.String(255))
    txn_id =  db.Column(db.String(255))
    txn_type =  db.Column(db.String(255))
    receiver_email =  db.Column(db.String(255))
    payer_email =  db.Column(db.String(255))
    date = db.Column(db.Integer)

    def __init__(self, item_name, item_number, custom, payment_status, payment_amount, payment_currency, payment_type, txn_id, txn_type, receiver_email, payer_email):
        self.item_name = item_name
        self.item_number = item_number
        self.custom = custom
        self.payment_status = payment_status
        self.payment_amount = payment_amount
        self.payment_currency = payment_currency
        self.payment_type = payment_type
        self.txn_id = txn_id
        self.txn_type = txn_type
        self.receiver_email = receiver_email
        self.payer_email = payer_email
        self.date = int(time.time())

    def __repr__(self):
        return '<MMOPayPalPaymant %r>' % self.id

def ordered_storage(f):
    import werkzeug.datastructures
    import flask
    def decorator(*args, **kwargs):
        flask.request.parameter_storage_class = werkzeug.datastructures.ImmutableOrderedMultiDict
        return f(*args, **kwargs)
    return decorator