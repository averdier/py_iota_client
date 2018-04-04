# -*- coding: utf-8 -*-

import time
import os
from configobj import ConfigObj
from model import Account

basedir = os.path.abspath(os.path.dirname(__file__))


if __name__ == '__main__':
    conf = ConfigObj(os.environ.get('APP_SETTINGS', os.path.join(basedir, 'conf.cfg')))
    account = Account(conf)

    def on_transaction(t, c):
        print('Transaction received, tag: {0}, confirmed: {1}'.format(t.tag, c))
        print('{0}'.format(t))

    account.on_new_transaction_received = on_transaction

    account.call_history(print_history=True)

    while True:
        account.call_history()
        time.sleep(int(conf['SLEEP']))

