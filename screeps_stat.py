
# —*- coding: utf-8 -*-

import base64
import json
import MySQLdb
import requests
import time
import traceback
import zlib

from config import DB_HOST, DB_USERNAME, DB_PASSWORD, DB_PORT, DB_NAME
from config import SERVER_HOST, SERVER_PORT, USERNAME, PASSWORD


def main():
    db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, port=DB_PORT, charset="utf8")
    cursor = db.cursor()
    try:
        cursor.execute("USE {}".format(DB_NAME))
    except MySQLdb.OperationalError:
        if "Unknown database" in traceback.format_exc():
            print("database not exists: {}".format(DB_NAME))
            cursor.execute("CREATE DATABASE {}".format(DB_NAME))
            cursor.execute("USE {}".format(DB_NAME))

    if cursor.execute("SELECT table_name "
                      "FROM information_schema.TABLES "
                      "WHERE table_name ='cpu'") == 0:
        print("table not exist: {}".format("cpu"))
        cursor.execute("CREATE TABLE `cpu` ("
                       "time_stamp DATETIME, "
                       "used FLOAT, "
                       "cap INT, "
                       "bucket INT"
                       ")")

    if cursor.execute("SELECT table_name "
                      "FROM information_schema.TABLES "
                      "WHERE table_name ='energy'") == 0:
        print("table not exist: {}".format("energy"))
        cursor.execute("CREATE TABLE `energy` ("
                       "time_stamp DATETIME, "
                       "room VARCHAR(8), "
                       "spawn INT, "
                       "spawn_cap INT, "
                       "storage INT"
                       ")")

    if cursor.execute("SELECT table_name "
                      "FROM information_schema.TABLES "
                      "WHERE table_name ='rcl'") == 0:
        print("table not exist: {}".format("rcl"))
        cursor.execute("CREATE TABLE `rcl` ("
                       "time_stamp DATETIME, "
                       "room VARCHAR(8), "
                       "progress INT, "
                       "progress_total INT, "
                       "level INT"
                       ")")

    if cursor.execute("SELECT table_name "
                      "FROM information_schema.TABLES "
                      "WHERE table_name ='room_info'") == 0:
        print("table not exist: {}".format("room_info"))
        cursor.execute("CREATE TABLE `room_info` ("
                       "id INT, "
                       "room VARCHAR(8), "
                       "claim_status VARCHAR(32), "
                       "hostile_status VARCHAR(32)"
                       ")")

    if cursor.execute("SELECT table_name "
                      "FROM information_schema.TABLES "
                      "WHERE table_name ='misc_info'") == 0:
        print("table not exist: {}".format("misc_info"))
        cursor.execute("CREATE TABLE `misc_info` ("
                       "id INT, "
                       "room VARCHAR(8), "
                       "info_key VARCHAR(256), "
                       "info_value VARCHAR(256)"
                       ")")

    token = requests.post("http://{}:{}/api/auth/signin".format(SERVER_HOST, SERVER_PORT),
                          json={
                              "email": USERNAME,
                              "password": PASSWORD
                          }).json()["token"]
    raw_memory = requests.get("http://{}:{}/api/user/memory".format(SERVER_HOST, SERVER_PORT),
                              headers={
                                  "X-Token": token,
                                  "X-Username": token
                              }).json()
    byte_string = base64.b64decode(raw_memory["data"][3:])
    json_string = zlib.decompress(byte_string, 15 + 32)
    memory = json.loads(json_string)
    print(memory["stat"])
    cpu = memory["stat"]["cpu"]
    cursor.execute("INSERT INTO `cpu` "
                   "VALUES (NOW(), '{}', {}, {});".format(cpu["used"], cpu["cap"], cpu["bucket"]))
    for room in memory["stat"]["energy"]:
        data = memory["stat"]["energy"][room]
        cursor.execute("INSERT INTO `energy` "
                       "VALUES (NOW(), '{}', {}, {}, {});".format(room, data["spawn"], data["spawn_cap"], data["storage"]))
    for room in memory["stat"]["rcl"]:
        data = memory["stat"]["rcl"][room]
        cursor.execute("INSERT INTO `rcl` "
                       "VALUES (NOW(), '{}', {}, {}, {});".format(
                            room, data["progress"], data["progress_total"], data["level"]))
    cursor.execute("DELETE FROM `room_info`;")
    for _i, data in enumerate(memory["stat"]["room_info"]):
        cursor.execute("INSERT INTO `room_info` "
                       "VALUES ({}, '{}', '{}', '{}');".format(
                            _i, data["room_name"], data["claim_status"], data["hostile_status"]))
    cursor.execute("DELETE FROM `misc_info`;")
    _i = 0
    for info_key in memory["stat"]["misc_info"]:
        cursor.execute("INSERT INTO `misc_info` "
                       "VALUES ({}, '{}', '{}', '{}');".format(
                            _i, info_key.split("|")[0], info_key.split("|")[1], memory["stat"]["misc_info"][info_key]))
    db.commit()
    db.close()


if __name__ == "__main__":
    while True:
        main()
        time.sleep(5)
