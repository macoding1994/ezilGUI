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
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QTimer, QFileInfo, QUrl
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QMainWindow, QApplication

from pyecharts import Bar,Line
from pyecharts_javascripthon.api import TRANSLATOR

from Ui_main import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    infoSignal = pyqtSignal(str)
    handleSignal = pyqtSignal(int)

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self._initSample()

        self._initConfig()
        self._initParameter()
        self._initSheet()
        self._initEvent()
        self._initPool()
        self._initSample()
        self.showMaximized()

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
        self.view = QWebEngineView(self.widget)
        url = QUrl(QFileInfo("./html/template.html").absoluteFilePath())
        self.view.load(url)
        # 一定要先完成加载
        self.view.loadFinished.connect(self.reload_canvas)
        self.echarts = False

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

    def request_eth(self, no, eth_wallet, zil_wallet, flag):
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
        for i in range(1, no + 1):
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
            self.pushButton.setDisabled(False)
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
        x_list = []
        y_list = []
        for res in cursor.fetchall():
            mid = ''
            mid = f'{res[0]}:        {res[1]}'
            self.infoSignal.emit(mid)
            x_list.append(res[0])
            y_list.append(res[1])
            mid = None
        else:
            self.create_bar(x_list, y_list)
            self.handleSignal.emit(3)
            self.infoSignal.emit('*' * self.xx + '每天收益计算完毕' + '*' * self.xx)
            self.real_time_hash()

    def real_time_hash(self):
        eth_wallet = self.lineEdit.text()
        zil_wallet = self.lineEdit_2.text()
        now_time = datetime.now() - timedelta(hours=8)
        day30_time = datetime.now() - timedelta(days=15)
        time_from = day30_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        time_to = now_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        url = f'https://stats.ezil.me/historical_stats/{eth_wallet}.{zil_wallet}?time_from={time_from}&time_to={time_to}'
        headers = {
            "Content-Type": "application/json; charset=UTF-8"
        }
        result = requests.get(url, headers=headers)
        time_name_list = []
        long_average_hashrate = []
        reported_hashrate = []
        short_average_hashrate = []
        for res in json.loads(result.text):
            # print('平均算力', res['long_average_hashrate'])
            # print('理论算力', res['reported_hashrate'])
            # print('短期算力', res['short_average_hashrate'])
            time_name_list.append(datetime.strptime(res["time"], '%Y-%m-%dT%H:%M:%SZ') + timedelta(hours=8))
            long_average_hashrate.append(res['long_average_hashrate'])
            reported_hashrate.append(res['reported_hashrate'])
            short_average_hashrate.append(res['short_average_hashrate'])
        else:
            self.create_line(time_name_list,[long_average_hashrate,reported_hashrate,short_average_hashrate])

    def handle(self, flag):
        '''
        流程处理函数
        :param flag:
        :return:
        '''
        if flag == 2:
            self.show_day_eth()
        if flag == 3:
            self.daytimer.start(1000 * 60)

    def reload_canvas(self):
        if not self.echarts:
            # 初始化echarts
            self.view.page().runJavaScript(
                '''
                    var myChart1 = echarts.init(document.getElementById('main1'), 'light', {renderer: 'canvas'});
                    var myChart2 = echarts.init(document.getElementById('main2'), 'light', {renderer: 'canvas'});
                '''
            )
            self.echarts = True

    def create_bar(self, x_list, y_list):
        # bar = Bar()
        # bar.add_xaxis(["衬衫", "羊毛衫", "雪纺衫", "裤子", "高跟鞋", "袜子"])
        # bar.add_yaxis("商家A", [5, 20, 36, 10, 75, 90])
        bar = Bar('ETH每日收益', '')
        bar.add('ETH', x_list, y_list, is_more_utils=True)
        snippet = TRANSLATOR.translate(bar.options)
        options = snippet.as_snippet()
        self.view.page().runJavaScript(
            f'''
                myChart1.clear();
                var option = eval({options});
                myChart1.setOption(option);
            '''
        )

    def create_line(self, x_list, y_list):
        y_list1, y_list2, y_list3 = y_list
        line = Line('算力曲线', '')
        line.add("平均算力", x_list, y_list1, is_smooth=True, mark_line=["max", "average"])
        line.add("理论算力", x_list, y_list2, is_smooth=True, mark_line=["max", "average"])
        line.add("短期算力", x_list, y_list3, is_smooth=True, mark_line=["max", "average"])
        snippet = TRANSLATOR.translate(line.options)
        options = snippet.as_snippet()
        self.view.page().runJavaScript(
            f'''
                myChart2.clear();
                var option = eval({options});
                myChart2.setOption(option);
            '''
        )

    @pyqtSlot()
    def on_pushButton_clicked(self):
        BASEDIR = os.path.dirname(os.path.abspath(__name__))
        file_path = os.path.join(BASEDIR, 'conf', 'config.ini')
        cf = configparser.ConfigParser()
        cf.read(file_path)
        if self.pushButton.text() == '开始':
            self.lineEdit.setDisabled(True)
            self.lineEdit_2.setDisabled(True)
            self.pushButton.setDisabled(True)
            cf.set('eth', 'eth_wallet', self.lineEdit.text())
            cf.set('zil', 'zil_wallet', self.lineEdit_2.text())
            cf.write(open(file_path, 'w'))
            self.pushButton.setText('结束')
            future1 = self.Pool.submit(self.request_eth, self.count_no, self.lineEdit.text(), self.lineEdit_2.text(), 1)
            future1.add_done_callback(self.infoshow)
        else:
            self.lineEdit.setDisabled(False)
            self.lineEdit_2.setDisabled(False)
            self.pushButton.setText('开始')
            self.infoSignal.emit('*' * self.xx + '关闭实时同步数据功能' + '*' * self.xx)
            self.daytimer.stop()

    def resizeEvent(self, *args, **kwargs):
        # QWebEngineView 跟随 pyqt窗口大小变换
        window_width = self.geometry().width()
        window_height = self.geometry().height()
        self.view.resize(window_width, window_height)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    ui = MainWindow()
    ui.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
