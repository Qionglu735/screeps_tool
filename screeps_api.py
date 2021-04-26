
# —*- coding: utf-8 -*-

from config import *

import requests
import ssl
import threading
import websocket


def singleton(cls):
    _instance = dict()

    def inner():
        if cls not in _instance:
            _instance[cls] = cls()
        return _instance[cls]

    return inner


@singleton
class Authentication(object):

    def __init__(self):
        self.__token = ""
        self.__url = "{}:{}".format(SERVER_HOST, SERVER_PORT)
        self.__username, self.__password = USERNAME, PASSWORD

    def __get_token(self):
        return requests.post("http://{}/api/auth/signin".format(self.__url),
                             json={
                                 "email": self.__username,
                                 "password": self.__password
                             }).json()["token"]

    def __get_me(self):
        return requests.get("http://{}/api/auth/me".format(self.__url),
                            headers={
                                "X-Token": self.__token,
                                "X-Username": self.__token
                            }).json()

    def get_token(self):
        if "error" in self.__get_me():
            self.__token = self.__get_token()
        return self.__token

    def get_me(self):
        self.__token = self.get_token()
        return self.__get_me()


class Socket(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

        self.__debug_socket = False

        self.__ws = None
        self.__url = "{}:{}".format(SERVER_HOST, SERVER_PORT)
        self.__auth = Authentication()
        self.__subscribe_target = ""
        self.__interval = 0.05
        self.subscribe("user", "console")
        self.__run_flag = threading.Event()
        self.__stop_flag = threading.Event()

        self.callback = lambda x: self.__print(x)

    def subscribe(self, _type, _name):
        if _type == "user":
            _name = "{}/{}".format(self.__auth.get_me()["_id"], _name)
        self.__subscribe_target = "{}:{}".format(_type, _name)

    def run(self):
        if not self.__run_flag.is_set():
            if self.__debug_socket:
                websocket.enableTrace(True)
            self.__ws = websocket.WebSocketApp("ws://{}/socket/websocket".format(self.__url),
                                               on_open=self.__on_open,
                                               on_message=self.__on_message,
                                               on_error=self.__on_error,
                                               on_close=self.__on_close)

            ssl_defaults = ssl.get_default_verify_paths()
            ssl_opt_ca_certs = {'ca_certs': ssl_defaults.cafile}
            self.__run_flag.set()
            self.__ws.run_forever(ping_interval=self.__interval, sslopt=ssl_opt_ca_certs)

    def stop(self):
        if not self.__stop_flag.isSet():
            self.__stop_flag.set()
            self.__ws.close()

    def set_debug(self, mode=True):
        self.__debug_socket = mode

    def set_interval(self, t=0.05):
        self.__interval = t

    def is_running(self):
        return self.__run_flag.is_set()

    def is_stopping(self):
        return self.__stop_flag.is_set()

    @staticmethod
    def __print(x):
        print(x)

    def __on_open(self, ws):
        if self.__debug_socket:
            print("[socket send]auth {}".format(self.__auth.get_token()))
        ws.send("auth {}".format(self.__auth.get_token()))

    def __on_message(self, ws, message):
        if self.__debug_socket:
            print("[socket message]{}".format(message))
        if message.startswith("time"):
            return
        if message.startswith("protocol"):
            return
        if message.startswith("auth ok"):
            if self.__debug_socket:
                print("[socket send]" + "subscribe {}".format(self.__subscribe_target))
            ws.send("subscribe {}".format(self.__subscribe_target))
            return
        self.callback(message)

    def __on_close(self, ws):
        if self.__debug_socket:
            print("[socket close]")
        self.__run_flag.clear()

    def __on_error(self, ws, error):
        if self.__debug_socket:
            print("[socket error]".format(error))
        self.__run_flag.clear()


class Api(object):

    def __init__(self):
        self.__url = "http://{}:{}".format(SERVER_HOST, SERVER_PORT)
        self.__auth = Authentication()

    def get(self, url, params=None):
        return requests.get("{}{}".format(self.__url, url),
                            headers={
                                "X-Token": self.__auth.get_token(),
                                "X-Username": self.__auth.get_token()
                            },
                            params=params)

    def post(self, url, json=None):
        return requests.post("{}{}".format(self.__url, url),
                             headers={
                                 "X-Token": self.__auth.get_token(),
                                 "X-Username": self.__auth.get_token()
                             },
                             json=json)

    def get_user_code(self):
        return self.get("/api/user/code").json()

    def post_user_code(self, dict_data):
        return self.post("/api/user/code",
                         json=dict_data).json()

    def post_user_console(self, expression):
        return self.post("/api/user/console",
                         json={
                             "expression": expression
                         }).json()

    def get_user_memory(self):
        return self.get("/api/user/memory").json()

    def get_user_overview(self):
        return self.get("/api/user/overview").json()

    def get_time(self):
        return self.get("/api/game/time").json()

    def get_room_terrain(self, room):
        return self.get("/api/game/room-terrain",
                        params={
                            "room": room,
                        }).json()


if __name__ == "__main__":
    api = Api()
    print api.get_time()
