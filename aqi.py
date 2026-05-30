import pymysql
import pandas as pd
import requests, io
from datetime import datetime
import urllib3
import os
from dotenv import load_dotenv

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TARGET_COLUMNS = [
    "sitename",
    "county",
    "aqi",
    "pollutant",
    "status",
    "so2",
    "co",
    "o3",
    "o3_8hr",
    "pm10",
    "pm2_5",
    "no2",
    "nox",
    "no",
    "wind_speed",
    "wind_direc",
    "publishtime",
    "co_8hr",
    "pm2_5_avg",
    "pm10_avg",
    "so2_avg",
    "longitude",
    "latitude",
    "siteid",
]


def get_data():
    print("取得AQI資料中")
    try:
        api_url = "https://data.moenv.gov.tw/api/v2/aqx_p_432?api_key=e75b1660-e564-4107-aad5-a8be1f905dd9&limit=1000&sort=ImportDate%20desc&format=JSON"
        resp = requests.get(api_url, verify=False)

        res_json = resp.json()

        # ✨【安全修正】相容環境部 API 各種回傳外殼
        if isinstance(res_json, dict) and "records" in res_json:
            df = pd.DataFrame(res_json["records"])
        elif isinstance(res_json, list):
            df = pd.DataFrame(res_json)
        else:
            # 有時候外殼可能是 {"records": [...]} 以外的其他 key 組合
            df = pd.DataFrame(res_json)

        # 1. 欄位名稱轉小寫
        df.columns = df.columns.str.lower()

        # 2. 點號轉底線
        df = df.rename(columns={"pm2.5": "pm2_5", "pm2.5_avg": "pm2_5_avg"})

        # 3. 鎖定 24 個欄位與順序
        df = df[TARGET_COLUMNS]

        # 4. 只阻擋「核心主鍵」有空值的資料，其他欄位允許為空 (NULL)
        df_filtered = df.dropna(subset=["sitename", "publishtime"]).drop_duplicates(
            subset=["sitename", "publishtime"]
        )
        df_filtered = df_filtered.astype(object).where(pd.notnull(df_filtered), None)

        data = df_filtered.values.tolist()
        return data

    except Exception as e:
        print(f"取得資料失敗: {e}")
    return None


def insert_data(data):
    try:
        # 這裡的欄位順序與名稱必須與上方 create_table 100% 完全一致
        sqlstr = (
            "insert ignore into data (sitename,county,aqi,pollutant,status,so2,co,o3,o3_8hr,pm10,pm2_5,no2,nox,no,wind_speed,wind_direc,publishtime,co_8hr,pm2_5_avg,pm10_avg,so2_avg,longitude,latitude,siteid) "
            "values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        )
        cursor.executemany(sqlstr, data)
        conn.commit()
        if cursor.rowcount == 0:
            print("目前無更新資料")
        else:
            print(f"更新 {cursor.rowcount} 筆資料")
    except Exception as e:
        print(f"寫入資料庫失敗: {e}")


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
        # 統一將 pm2.5 相關欄位改用底線命名（安全且不易產生 SQL 語法衝突）
        sqlstr = """
        create table if not exists data(        
        sitename varchar(50),
        county varchar(20),
        aqi int,
        status varchar(20),
        publishtime datetime,
        pollutant varchar(20),
        so2 float,
        co float,
        o3 float,
        o3_8hr float,
        pm10 float,
        pm2_5 float,          -- 確保是底線
        no2 float,
        nox float,
        no float,
        wind_speed float,
        wind_direc float,
        co_8hr float,
        pm2_5_avg float,      -- 確保是底線
        pm10_avg float,
        so2_avg float,
        longitude float,
        latitude float,
        siteid int,
        
        unique key uq_sitename_publishtime (sitename, publishtime)
        )
        """
        cursor.execute(sqlstr)
        conn.commit()
        print("檢查/建立資料表完成")
    except Exception as e:
        print(f"建立資料表失敗: {e}")


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
