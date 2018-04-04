# -*- coding: utf-8 -*-

import json
from iota import Iota, Transaction
from utils.hash import create_seed_hash, get_checksum, verify_checksum
from utils.logging import FileLogger
from iota.crypto.addresses import AddressGenerator
from utils.iota import address_checksum, address_balance, convert_units


class Account:
    """
    Account model
    """

    def __init__(self, args):
        """
        Constructor

        :param args:
        """
        self._seed = args['SEED']
        self._filename = create_seed_hash(args['SEED'])
        self._data = None
        self._logger = FileLogger('account', args['LOG_PATH'], args['LOG_LEVEL'])
        self._account_history_executing = False
        self._read_account_data()

    @property
    def iota_node(self):
        return self._data['account_data'][0]['settings'][0]['host']

    @property
    def units(self):
        return self._data['account_data'][0]['settings'][0]['units']

    def _read_account_data(self):
        """
        Read account data from file
        A new file is created if file not found
        """

        try:

            with open(self._filename, 'r') as account_data:
                self._data = json.load(account_data)
        except FileNotFoundError:
            with open(self._filename, 'w') as account_data:
                self._data = {
                    'account_data': [{
                        'settings': [{
                            'host': "http://127.0.0.1:14700",
                            'min_weight_magnitude': 13,
                            'units': "i"
                        }],
                        'address_data': [],
                        'fal_balance': [{
                            'f_index': 0,
                            'l_index': 0
                        }],
                        'transfers_data': []
                    }]
                }
                json.dump(self._data, account_data, indent=4)
                self._logger.info('Created new account file.')

    def _write_address_data(self, index, address, balance):
        """
        Writes the index, address and balance, as well as the checksum of address + seed into the account file

        :param index:
        :param address:
        :param balance:
        :return:
        """
        address = address_checksum(address)
        for p in self._data['account_data'][0]['address_data']:
            if p["address"] == address:
                p["balance"] = balance
                with open(self._filename, 'w') as account_data:
                    json.dump(self._data, account_data, indent=4)
                return

        checksum = get_checksum(address, self._seed)
        self._data["account_data"][0]["address_data"].append({
            'index': index,
            'address': address,
            'balance': balance,
            'checksum': checksum
        })

        with open(self._filename, 'w') as account_data:
            json.dump(self._data, account_data, indent=4)

    def _write_fal_balance(self, f_index=0, l_index=0):
        """
        Takes the f_index and/or the l_index and saves them in the account file
        "f_index" is the index of the first address with balance and "l_index" is the index of the last address with balance

        :param f_index:
        :param l_index:
        :return:
        """
        fal_balance = self._data['account_data'][0]['fal_balance']
        if f_index > 0 and l_index > 0:
            fal_balance[0]["f_index"] = f_index
            fal_balance[0]["l_index"] = l_index

        elif f_index > 0:
            fal_balance[0]["f_index"] = f_index
        elif l_index > 0:
            fal_balance[0]["l_index"] = l_index
        else:
            return

        with open(self._filename, 'w') as account_data:
            json.dump(self._data, account_data, indent=4)

    def _write_transfers_data(self, transaction_hash, is_confirmed, timestamp,
                              tag, address, message, value, bundle):
        """
        Writes data of an transaction to the account file

        :param transaction_hash:
        :param is_confirmed:
        :param timestamp:
        :param tag:
        :param address:
        :param message:
        :param value:
        :param bundle:
        :return:
        """
        for p in self._data['account_data'][0]['transfers_data']:
            if p["transaction_hash"] == transaction_hash:
                if is_confirmed == p["is_confirmed"]:
                    return
                else:
                    p['is_confirmed'] = is_confirmed
                    with open(self._filename, 'w') as account_data:
                        json.dump(self._data, account_data, indent=4)
                    return

        self._data["account_data"][0]["transfers_data"].append({
            'transaction_hash': transaction_hash,
            'is_confirmed': is_confirmed,
            'timestamp': timestamp,
            'tag': tag,
            'address': address,
            'message': message,
            'value': value,
            'bundle': bundle

        })

        with open(self._filename, 'w') as account_data:
            json.dump(self._data, account_data, indent=4)

    def _update_fal_balance(self):
        """
        Updates the f_index and l_index

        :return:
        """
        index_with_value = []
        for data in self._data['account_data'][0]['address_data']:
            if data["balance"] > 0:
                index = data["index"]
                index_with_value.append(index)

        if len(index_with_value) > 0:
            f_index = min(index_with_value)
            l_index = max(index_with_value)
            self._write_fal_balance(f_index, l_index)

        return

    def update_addresses_balance(self, start_index=0):
        """
        Checks all addresses that are saved in the account file and updates there balance
        start_index can be set in order to ignore all addresses before the start index

        :param start_index:
        :return:
        """
        max_index = 0
        for data in self._data['account_data'][0]['address_data']:
            index = data["index"]
            if start_index <= index:
                address = str(data["address"])
                balance = address_balance(self._data['account_data'][0]['settings'][0]['host'], address)
                self._write_address_data(index, address, balance)

            if max_index < index:
                max_index = index

        if max_index < start_index:
            self._logger.error(
                "Start index was not found. You should generate more addresses or use a lower start index")

    def generate_addresses(self, count):
        """
        Generates one or more addresses and saves them in the account file

        :param count:
        :return:
        """
        index_list = [-1]
        for data in self._data['account_data'][0]['address_data']:
            index = data["index"]
            index_list.append(index)

        if max(index_list) == -1:
            start_index = 0
        else:
            start_index = max(index_list) + 1
        generator = AddressGenerator(self._seed)
        addresses = generator.get_addresses(start_index, count)  # This is the actual function to generate the address.
        i = 0

        while i < count:
            index = start_index + i
            address = addresses[i]
            balance = address_balance(self._data['account_data'][0]['settings'][0]['host'], address)
            self._write_address_data(index, str(address), balance)
            i += 1

        self._update_fal_balance()

    def find_balance(self, count):
        """
        Will generate and scan X addresses of an seed for balance. If there are already saved addresses in the ac-
        count data, it will start with the next higher address index

        :param count:
        :return:
        """
        max_gap = 3
        margin = 4
        i = 0
        balance_found = False
        self._logger.info("Generating addresses and checking for balance, please wait...")
        while i < count and margin > 0:
            self._logger.debug("Checking address " + str(i + 1) + " in range of " + str(count))
            self.generate_addresses(1)
            index_list = []
            for data in self._data['account_data'][0]['address_data']:
                index = data['index']
                index_list.append(index)
            max_index = max(index_list)
            for data in self._data['account_data'][0]['address_data']:
                index = data['index']
                balance = data['balance']
                if index == max_index and balance > 0:
                    balance_found = True
                    address = data['address']
                    self._logger.debug('Balance found, index: {0}, address: {1}, balance: {2}'.format(
                        str(index), str(address),
                        convert_units(balance, self._data['account_data'][0]['settings'][0]['units'])
                    ))
                    margin = max_gap
                    if count - i <= max_gap:
                        count += max_gap

                elif index == max_index and margin <= max_gap:
                    margin -= 1

            i += 1
        if not balance_found:
            self._logger.debug("No address with balance found!")

    def get_deposit_address(self):
        """
        Gets the first address after the last address with balance. If there is no saved address it will generate a new one

        :return:
        """
        try:
            l_index = self._data['account_data'][0]['fal_balance'][0]["l_index"]
            if l_index == 0:
                deposit_address = self._data['account_data'][0]['address_data'][0]["address"]
                return deposit_address

            for p in self._data['account_data'][0]['address_data']:
                address = p["address"]
                checksum = p["checksum"]
                integrity = verify_checksum(checksum, address, self._seed)
                if p["index"] > l_index and integrity:
                    deposit_address = p["address"]
                    return deposit_address
                elif not integrity:
                    return "Invalid checksum!!!"
            self._logger.info("Generating address...")
            self.generate_addresses(1)

            for p in self._data['account_data'][0]['address_data']:
                address = p["address"]
                checksum = p["checksum"]
                integrity = verify_checksum(checksum, address, self._seed)
                if p["index"] > l_index and integrity:
                    deposit_address = p["address"]
                    return deposit_address

        except Exception as ex:
            self._logger.critical("An error acoured while trying to get the deposit address")
            raise ex

    def print_full_account_info(self):
        """
        Displays all saved addresses and there balance

        :return:
        """
        self.update_addresses_balance(self._data['account_data'][0]['fal_balance'][0]["f_index"])
        self._update_fal_balance()
        if len(self._data['account_data'][0]['address_data']) > 0:
            all_address_data = ""
            for p in self._data['account_data'][0]['address_data']:
                address = p["address"]
                checksum = p["checksum"]
                balance = int(p["balance"])
                integrity = verify_checksum(checksum, address, self._seed)
                if integrity:
                    data = "Index: " + str(p["index"]) + "   " + p["address"] + \
                           "   balance: " + convert_units(balance, self._data['account_data'][0]['settings'][0]['units']) + "\n"
                    all_address_data += data

                else:
                    data = "Index: " + str(p["index"]) + "   Invalid Checksum!!!" + "\n"
                    all_address_data += data

            print(all_address_data)
            fal_data = "First index with balance: " + str(
                self._data['account_data'][0]['fal_balance'][0]["f_index"]) + "\n" + "Last index with balance is: " + str(self._data['account_data'][0]['fal_balance'][0]["l_index"])
            print(fal_data)
        else:
            print("No Data to display!")

    def print_standard_account_info(self):
        """
        Displays all addresses with balance, the total account balance and a deposit address.
        In case that there are no saved addresses it will ask if the account should be scanned for balance
        If the User answers with no, then it will just generate a deposit address (at index 0)

        :return:
        """
        address_count = len(self._data['account_data'][0]['address_data'])
        self.update_addresses_balance(self._data['account_data'][0]['fal_balance'][0]["f_index"])
        self._update_fal_balance()

        if address_count < 1:
            self.find_balance(10)
            self.print_standard_account_info()

        elif address_count > 0:
            all_address_data = ""
            total_balance = 0
            for p in self._data['account_data'][0]['address_data']:
                balance = p["balance"]
                address = p["address"]
                checksum = p["checksum"]
                integrity = verify_checksum(checksum, address, self._seed)
                if balance > 0 and integrity:
                    total_balance += balance
                    data = "Index: " + str(p["index"]) + "   " + address + "   balance: " + convert_units(balance, self._data['account_data'][0]['settings'][0]['units']) + "\n"
                    all_address_data += data

                elif not integrity:
                    total_balance += balance
                    data = "Index: " + str(p["index"]) + "   Invalid Checksum!!!" + "\n"
                    all_address_data += data

            if total_balance > 0:
                print(all_address_data)
                print("\n" + "Deposit address: " + str(self.get_deposit_address()))
                print("\nTotal Balance: " + convert_units(total_balance, self._data['account_data'][0]['settings'][0]['units']))

            else:
                print("No addresses with balance!")
                print("\n" + "Deposit address: " + str(self.get_deposit_address()))

    def on_new_transaction_received(self, transaction, confirmed):
        self._logger.debug('on_new_transaction_received, tag: {0}, is_confirmed: {1}'.format(transaction.tag, confirmed))
        pass

    def get_transfers(self, full_history, print_history=False):
        """
        Gets all associated transactions from the saved addresses and saves the transaction data in the account file

        :param full_history:
        :param print_history:
        :return:
        """
        self._account_history_executing = True
        api = Iota(self.iota_node, self._seed)
        address_count = len(self._data['account_data'][0]['address_data'])
        my_all_txn_hashes = {}
        all_txn_hashes = []
        saved_txn_hashes = []
        new_txn_hashes = []
        i = 0

        while i < address_count:
            address = self._data['account_data'][0]['address_data'][i]["address"]
            address_as_bytes = [address]
            raw_transfers = api.find_transactions(addresses=address_as_bytes)
            transactions_to_check = raw_transfers["hashes"]

            for txn_hash in transactions_to_check:
                str_txn_hash = str(txn_hash)
                all_txn_hashes.append(str_txn_hash)
                my_all_txn_hashes[str_txn_hash] = txn_hash
            i += 1

        for txn_hash in self._data['account_data'][0]['transfers_data']:
            txn_hash = str(txn_hash['transaction_hash'])
            saved_txn_hashes.append(txn_hash)

        for th in my_all_txn_hashes:
            if th not in saved_txn_hashes:
                new_txn_hashes.append(my_all_txn_hashes[th])

        if len(new_txn_hashes) > 0:
            self._logger.info("Retrieving and saving transfer data from " + str(len(new_txn_hashes)) + " transaction(s)! Please wait...")
            for txn_hash in new_txn_hashes:
                li_result = api.get_latest_inclusion(
                    [txn_hash])  # Needs to be integrated into new transactions as well
                is_confirmed = li_result['states'][txn_hash]

                gt_result = api.get_trytes([txn_hash])
                trytes = str(gt_result['trytes'][0])
                txn = Transaction.from_tryte_string(trytes)
                timestamp = str(txn.timestamp)
                tag = str(txn.tag)
                address = str(txn.address)
                message = "some message"  # Placeholder untill message decoding is added
                value = str(txn.value)
                bundle = str(txn.bundle_hash)

                self._write_transfers_data(
                    str(txn_hash),
                    is_confirmed,
                    timestamp,
                    tag,
                    address,
                    message,
                    value,
                    bundle
                )

                self.on_new_transaction_received(txn, is_confirmed)

        if print_history:
            if full_history:
                self.print_full_account_info()

            elif not full_history:
                self.print_standard_account_info()

        self._account_history_executing = False

    def call_history(self, print_history=False):
        if not self._account_history_executing:
            self._logger.debug("loop called for account history")
            self.get_transfers(full_history=False, print_history=print_history)
