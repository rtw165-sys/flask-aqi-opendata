import pymysql
import pandas as pd
import requests, io
from datetime import datetime
import urllib3
import os
from dotenv import load_dotenv

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_data():
    print("取得AQI資料中")
    try:
        # api_url="https://data.moenv.gov.tw/api/v2/aqx_p_02?api_key=af57253c-e838-46da-a1f5-12b43afd75f3&limit=1000&sort=datacreationdate%20desc&format=CSV"
        api_url = "https://data.moenv.gov.tw/api/v2/aqx_p_432?api_key=e75b1660-e564-4107-aad5-a8be1f905dd9&limit=1000&sort=ImportDate%20desc&format=JSON"
        resp = requests.get(api_url, verify=False)
        df = pd.read_json(io.StringIO(resp.text))
        df1 = df.drop_duplicates(subset=["sitename", "publishtime"]).dropna()
        data = df1.values.tolist()

        return data
    except Exception as e:
        print(e)

    return None


def insert_data(data):
    # mysql 忽略語法跟佔位符不一樣
    try:
        sqlstr = "insert ignore into data (sitename,county,aqi,status,publishtime)\
        values(%s,%s,%s,%s,%s)"
        cursor.executemany(sqlstr, data)
        conn.commit()
        if cursor.rowcount == 0:
            print("目前無更新資料")
        else:
            print(f"更新{cursor.rowcount}筆資料")
    except Exception as e:
        print(e)


def open_db():

    try:
        # print(os.getenv("HOST")) // os.getenv給本地端dotenv使用
        conn = pymysql.connect(
            host=os.environ.get("HOST"),
            port=int(os.environ.get("PORT")),
            user=os.environ.get("USER"),
            password=os.environ.get("PASSWORD"),
            database=os.environ.get("NAME"),
            ssl={"ca": None},
        )

        cursor = conn.cursor()
        return conn, cursor
    except Exception as e:
        print(e)

    return None, None


def create_table():
    global conn, cursor
    try:
        # unique  插入資料唯一的約束
        sqlstr = """
        create table if not exists data(
        id int primary key auto_increment,
        sitename varchar(50),
        county varchar(20),
        aqi int,
        status varchar(20),
        publishtime datetime,
        unique key uq_sitename_publishtime (sitename,publishtime)
        )
        """

        index = cursor.execute(sqlstr)
        conn.commit()
        if index:
            print("建立資料表成功!")
    except Exception as e:
        print(e)


print("-----------------------------------------")
print(f"運行時間:{datetime.now()}")

conn, cursor = open_db()
if conn:
    print("開啟資料庫成功")
    create_table()
    data = get_data()
    if data:
        insert_data(data)
    else:
        print("目前無資料")
    conn.close()
else:
    print("資料庫開啟失敗!")
