import os
import time
from datetime import datetime,timedelta

import requests
import json
import sqlite3

def create_table():
    if not os.path.isfile('./eth.db'):
        conn  = sqlite3.connect("./eth.db")
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
    else:
        conn = sqlite3.connect('eth.db')
        cursor = conn.cursor()
    return conn,cursor

def check_eid(cursor,eid):
    res = cursor.execute('select * from eth where eid={}'.format(eid))
    if not len(res.fetchall()):
        return True
    return False

def save_eth(url):
    headers = {
        "Content-Type": "application/json; charset=UTF-8"
    }
    result = requests.get(url, headers=headers)
    if result.status_code == 200:
        print(url,'请求成功')
        for res in json.loads(result.text):
            created_at = datetime.strptime(res["created_at"], '%Y-%m-%dT%H:%M:%SZ') + timedelta(hours=8)
            amount = float(res["amount"])
            eid = int(res["id"])
            if check_eid(cursor,eid):
                print(f'{eid}-{created_at}--{amount}')
                cursor.execute(insert_sql,(None,eid,created_at,amount))
            else:
                continue
        else:
            conn.commit()
    else:
        print(url,'请求失败')


if __name__ == '__main__':
    # conn,cursor = create_table()
    # insert_sql = "insert into eth values (?, ?, ?, ?)"
    # query_sql = "select strftime('%Y-%m-%d', time),sum(amount),count(amount),group_concat(amount) from eth group by strftime('%Y-%m-%d',time)"
    # #
    # # cursor.execute(query_sql)
    # # for res in cursor.fetchall():
    # #     # print(res[:3])
    # #     # amount_list = [float(i) for i in res[3].split(',')]
    # #     # print(sum(amount_list))
    # #     print(res[0],':  ',res[1])
    #
    #
    # url = 'https://billing.ezil.me/rewards/0x8a0ddf1b6780debd11ac388f9ce97987c3ab824f.zil1tgcc93dsseu3e2nmmczexkyaf3gz4k8f99yhyf?page={}&per_page=10&coin=eth'
    #
    # for i in range(1,10):
    #     save_eth(url.format(i))
    #     time.sleep(3)
    eth_wallet = '0x8a0ddf1b6780debd11ac388f9ce97987c3ab824f'
    zil_wallet = 'zil1tgcc93dsseu3e2nmmczexkyaf3gz4k8f99yhyf'
    now_time = datetime.now() - timedelta(hours=8)
    day30_time = datetime.now() - timedelta(days=15)
    time_from = day30_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    time_to = now_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    url = f'https://stats.ezil.me/historical_stats/{eth_wallet}.{zil_wallet}?time_from={time_from}&time_to={time_to}'
    headers = {
        "Content-Type": "application/json; charset=UTF-8"
    }
    result = requests.get(url, headers=headers)
    for res in json.loads(result.text):
        print('平均算力',res['long_average_hashrate'])
        print('理论算力',res['reported_hashrate'])
        print('短期算力',res['short_average_hashrate'])


