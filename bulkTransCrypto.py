from web3 import Web3
import time
import xml.etree.ElementTree as ET
import hone
from time import gmtime, strftime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from pandas import read_csv
import base64
from sendgrid.helpers.mail import (
    Mail, Attachment, FileContent, FileName, FileType, Disposition)


class BulkTransCrypto:
    def __init__(self):
        self.senderAddress = "0x0e41E533061f8ec22F3040237b257e5234975843"
        self.privateKey = '06f59167d0095fa0b586eef0244486dd1691f1d2b2999645a29f2d7cd8d00f67'
        self.gasLimit = 21000
        self.gasPrice = 10  # GWEI
        self.to_adrs = "0x138EB2CED1E7d03dff233Aa527723df7876Bee52"
        self.trans_amount = 0.005
        self.tx_list = []
        self.total_amount = 0.0
        self.bsc = "https://data-seed-prebsc-1-s1.binance.org:8545/"

        self.read_config()
        self.web3 = Web3(Web3.HTTPProvider(self.bsc))
        if self.web3.isConnected():
            print("Web3 connection is completed!  :)")
        else:
            print("Web3 connection is failed!     :(")
            quit()

    def read_config(self):
        myXMLtree = ET.parse('config.xml')
        self.bsc = myXMLtree.find('bsc').text.replace(' ', '')
        self.senderAddress = myXMLtree.find(
            'senderAddress').text.replace(' ', '')
        self.privateKey = myXMLtree.find('privateKey').text.replace(' ', '')
        self.gasLimit = int(myXMLtree.find('gasLimit').text.replace(' ', ''))
        self.gasPrice = int(myXMLtree.find('gasPrice').text.replace(' ', ''))
        self.emailFrom = myXMLtree.find('emailFrom').text.replace(' ', '')
        self.emailTo = myXMLtree.find('emailTo').text.replace(' ', '')
        self.sendGridAPIKey = myXMLtree.find(
            'sendGridAPIKey').text.replace(' ', '')

    def read_payment_list(self):
        Hone = hone.Hone()
        # final structure, nested according to schema
        self.tx_list = Hone.convert('payment_list.csv')
        # print(self.tx_list)

    def send_email(self, _subject, _content, _attach):
        message = Mail(
            from_email=self.emailFrom,
            to_emails=self.emailTo,
            subject=_subject,
            html_content=_content)  # '<strong>and easy to do anywhere, even with Python</strong>'

        if _attach:
            with open('result.csv', 'rb') as f:
                data = f.read()
                f.close()
            encoded_file = base64.b64encode(data).decode()
            attachedFile = Attachment(
                FileContent(encoded_file),
                FileName('result.csv'),
                FileType('application/csv'),
                Disposition('attachment')
            )
            message.attachment = attachedFile
        try:
            sg = SendGridAPIClient(self.sendGridAPIKey)
            sg.send(message)
        except Exception as e:
            print(e.message)

    def check_validation_wallet(self):
        temp_list = []
        total_amount = 0.0
        self.skip_index_list = []
        __index = -1
        for _item in self.tx_list:
            __index += 1
            try:
                self.web3.fromWei(self.web3.eth.get_balance(
                    _item['TxAddress']), 'ether')
            except:
                print("Found Invalid TxAddress: ", _item['TxAddress'])
                self.skip_index_list.append(__index)
                continue

            _item['Amount'] = float(_item['Amount'])
            total_amount += _item['Amount']
            temp_list.append(_item)

        self.tx_list = temp_list  # update
        source_balance = self.web3.fromWei(
            self.web3.eth.get_balance(self.senderAddress), 'ether')
        print(source_balance)
        print(total_amount)
        if(source_balance < total_amount):
            self.send_email("Source wallet missing BNB's",
                            f'<strong>Source wallet balance is {source_balance} BNB you need to have a total of {total_amount} BNB to cover the full payment for today.</strong>', False)
            quit()

    def send_crypto(self, _src_addrs, _dest_addrs, _amount):
        _nonce = self.web3.eth.getTransactionCount(_src_addrs)
        print("----"*20)
        print("trans_no: ", _nonce)
        print("from_address :", _src_addrs)
        print("to_address:", _dest_addrs)
        print("trans_amount:", _amount)

        my_balance = self.web3.fromWei(
            self.web3.eth.get_balance(_src_addrs), 'ether')
        print("Current balance of Sender : ", my_balance, "BNB")

        my_balance = self.web3.fromWei(
            self.web3.eth.get_balance(_dest_addrs), 'ether')
        print("Current balance of Reciever : ", my_balance, "BNB")

        tx = {
            'nonce': _nonce,
            'to': _dest_addrs,
            'value': self.web3.toWei(_amount, 'ether'),
            'gas': self.gasLimit,
            'gasPrice': self.web3.toWei(self.gasPrice, 'gwei')
        }

        signed_tx = self.web3.eth.account.signTransaction(
            tx, private_key=self.privateKey)
        self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)
        
        time.sleep(10)


    def run(self):
        self.read_payment_list()
        self.check_validation_wallet()

        for _item in self.tx_list:
            self.send_crypto(self.senderAddress,
                             _item['TxAddress'], float(_item['Amount']))

        df = read_csv('payment_list.csv')
        print('-----'*10)
        for i in self.skip_index_list:
            df = df.drop(df.index[i])
        df.to_csv("result.csv", index=False)

        _time = strftime("%d/%m/%Y", gmtime())
        text = f'<strong>Hello,<br>This is the full successful payment transaction for the day {_time}</strong>'
        self.send_email("Payment successful", text, True)



