# -*- coding: utf-8 -*-

"""
Module implementing MainWindow.
"""
import configparser
import json
import os
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from queue import Queue

import requests
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QTimer
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QMainWindow, QApplication

from Ui_main import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    infoSignal = pyqtSignal(str)
    handleSignal = pyqtSignal(int)

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self._initConfig()
        self._initParameter()
        self._initSheet()
        self._initEvent()
        self._initPool()
        self._initSample()

    def _initConfig(self):
        '''配置初始化'''
        BASEDIR = os.path.dirname(os.path.abspath(__name__))
        file_path = os.path.join(BASEDIR, 'conf', 'config.ini')
        if not os.path.isfile(file_path):
            dir_path = os.path.join(BASEDIR, 'conf')  # 生成本地路径（到文件夹）
            if not os.path.isdir(dir_path):
                os.mkdir(dir_path)
            with open(file_path, 'w') as f:
                f.write('[eth]\reth_wallet = \r[zil]\rzil_wallet = ')

        if not os.path.isfile('./eth.db'):
            conn = sqlite3.connect("./eth.db")
            cursor = conn.cursor()
            sql = '''
                CREATE TABLE eth
                    (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        eid INTEGER,
                        time DATETIME ,
                        amount float
                    );
            '''
            cursor.execute(sql)
            conn.commit()


    def _initParameter(self):
        '''参数初始化'''
        BASEDIR = os.path.dirname(os.path.abspath(__name__))
        file_path = os.path.join(BASEDIR, 'conf', 'config.ini')
        self.cf = configparser.ConfigParser()
        self.cf.read(file_path)

        self.timer = QTimer()
        self.daytimer = QTimer()

        self.count_no = 200
        self.info_q = Queue()

        self.xx = 30
        self.data_flag = 0

    def _initSheet(self):
        '''QT样式初始化'''
        eth_wallet = self.cf.get('eth', 'eth_wallet')
        zil_wallet = self.cf.get('zil', 'zil_wallet')

        self.lineEdit.setText(eth_wallet)
        self.lineEdit_2.setText(zil_wallet)

    def _initEvent(self):
        '''Event绑定'''
        self.daytimer.timeout.connect(self.day_eth)
        self.infoSignal.connect(self.infoshow)
        self.handleSignal.connect(self.handle)

    def _initPool(self):
        '''线程池初始化'''
        self.Pool = ThreadPoolExecutor(max_workers=1)

    def _initSample(self):
        '''例子初始化'''
        pass

    def infoshow(self, res):
        if isinstance(res, str):
            self.textBrowser.append(res + '\n')
        else:
            self.textBrowser.append(str(res.result()) + '\n')
        try:
            self.textBrowser.moveCursor(QTextCursor.End)
        except Exception:
            pass

    def check_eid(self, cursor, eid):
        res = cursor.execute('select * from eth where eid={}'.format(eid))
        if not len(res.fetchall()):
            return True
        return False

    def day_eth(self):
        future1 = self.Pool.submit(self.request_eth, 1, self.lineEdit.text(), self.lineEdit_2.text(), 3)
        future1.add_done_callback(self.infoshow)


    def request_eth(self,no,eth_wallet,zil_wallet,flag):
        conn = sqlite3.connect('./eth.db')
        cursor = conn.cursor()
        insert_sql = "insert into eth values (?, ?, ?, ?)"
        isflag = True
        if flag == 1:
            context = '*' * self.xx + '开始同步历史数据' + '*' * self.xx
        if flag == 2:
            context = '*' * self.xx + '正在计算每天收益' + '*' * self.xx
        if flag == 3:
            context = '*' * self.xx + '实时同步数据' + '*' * self.xx
        self.infoSignal.emit(context)
        for i in range(1,no+1):
            url = f'https://billing.ezil.me/rewards/{eth_wallet}.' \
                  f'{zil_wallet}?page={i}&per_page=10&coin=eth'
            headers = {
                "Content-Type": "application/json; charset=UTF-8"
            }
            if not isflag:
                continue
            time.sleep(1)
            result = requests.get(url, headers=headers)
            if result.status_code == 200:
                self.infoSignal.emit(f'{url}请求成功')
                for res in json.loads(result.text):
                    created_at = datetime.strptime(res["created_at"], '%Y-%m-%dT%H:%M:%SZ') + timedelta(hours=8)
                    amount = float(res["amount"])
                    eid = int(res["id"])
                    if self.check_eid(cursor, eid):
                        self.infoSignal.emit(f'{eid}-{created_at}--{amount}')
                        cursor.execute(insert_sql, (None, eid, created_at, amount))
                    else:
                        isflag = False
                else:
                    conn.commit()
            else:
                self.infoSignal.emit(f'{url}请求失败')
        cursor.close()
        conn.close()
        time.sleep(1)
        if flag == 1:
            time.sleep(0.5)
            self.handleSignal.emit(2)
            conn, cursor, result = None, None, None
            return '*' * self.xx + '历史数据同步结束' + '*' * self.xx
        if flag == 2:
            time.sleep(0.5)
            self.handleSignal.emit(3)
            conn, cursor, result = None, None, None
            return '*' * self.xx + '每天收益计算完毕' + '*' * self.xx
        if flag == 3:
            time.sleep(0.5)
            conn, cursor, result = None, None, None
            return '*' * self.xx + '实时同步数据结束' + '*' * self.xx


    def show_day_eth(self):
        self.infoSignal.emit('*' * self.xx + '正在计算每天收益' + '*' * self.xx)
        conn = sqlite3.connect('./eth.db')
        cursor = conn.cursor()
        query_sql = "select strftime('%Y-%m-%d', time),sum(amount),count(amount),group_concat(amount) from eth group by strftime('%Y-%m-%d',time)"
        cursor.execute(query_sql)
        for res in cursor.fetchall():
            mid = ''
            mid = f'{res[0]}:        {res[1]}'
            self.infoSignal.emit(mid)
            mid = None
        else:
            self.handleSignal.emit(3)
            self.infoSignal.emit('*'*self.xx+'每天收益计算完毕'+'*'*self.xx)



    def handle(self,flag):
        if flag == 2:
            self.show_day_eth()
        if flag == 3:
            self.daytimer.start(1000*60)

    @pyqtSlot()
    def on_pushButton_clicked(self):
        BASEDIR = os.path.dirname(os.path.abspath(__name__))
        file_path = os.path.join(BASEDIR, 'conf', 'config.ini')
        cf = configparser.ConfigParser()
        cf.read(file_path)
        if self.pushButton.text() == '开始':
            cf.set('eth', 'eth_wallet', self.lineEdit.text())
            cf.set('zil', 'zil_wallet', self.lineEdit_2.text())
            cf.write(open(file_path, 'w'))
            self.pushButton.setText('结束')
            future1 = self.Pool.submit(self.request_eth,self.count_no,self.lineEdit.text(),self.lineEdit_2.text(),1)
            future1.add_done_callback(self.infoshow)
        else:
            self.pushButton.setText('开始')
            self.daytimer.stop()



def main():
    app = QApplication(sys.argv)
    ui = MainWindow()
    ui.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
