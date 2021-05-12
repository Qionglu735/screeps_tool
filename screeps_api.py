
# —*- coding: utf-8 -*-

import requests
import ssl
import threading
import websocket


def singleton(cls):
    _instance = dict()

    def inner(*args):
        if cls not in _instance:
            _instance[cls] = cls(*args)
        return _instance[cls]

    return inner


@singleton
class Authentication(object):

    def __init__(self, server_host, server_port, username, password):
        self.__url = "{}:{}".format(server_host, server_port)
        self.__username, self.__password = username, password
        self.__token = ""
        self.auth_succeed, self.auth_msg = False, ""

    def __sign_in(self):
        print("[api]Sign In")
        try:
            self.__token = ""
            res = requests.post(
                # api from screepsmod-auth
                # https://github.com/ScreepsMods/screepsmod-auth/blob/master/lib/backend.js
                "http://{}/api/auth/signin".format(self.__url),
                json={
                    "email": self.__username,
                    "password": self.__password
                }
            )
            if res.status_code == 200:
                self.__token = res.json()["token"]
                print("[api]Succeed")
                return True, "Authentication Succeed"
            else:
                if res.status_code == 404:
                    print("[api]User/Pass Auth Not Allowed")
                    return False, "User/Pass Auth Not Allowed"
                elif res.status_code == 401:
                    print("[api]Authentication Failed")
                    return False, "Authentication Failed"
                else:
                    print("[api]{}".format(res.status_code))
                    return False, "[api]{}".format(res.status_code)
        except requests.exceptions.ConnectionError:
            print("[api]Connection Failed")
            return False, "Connection Failed"

    def __get_me(self):
        try:
            res = requests.get(
                "http://{}/api/auth/me".format(self.__url),
                headers={
                    "X-Token": self.__token,
                    "X-Username": self.__token
                }
            )
            if res.status_code == 200:
                return res.json()
            else:
                if res.status_code == 401:
                    self.auth_succeed = False
                    return res.json()
                else:
                    print("[api]{}".format(res.status_code))
                    return dict()
        except requests.exceptions.ConnectionError:
            print("[api]Connection Failed")
            return dict()

    def get_token(self):
        if "error" in self.__get_me() or not self.auth_succeed:
            self.auth_succeed, self.auth_msg = self.__sign_in()
        return self.__token

    def get_me(self):
        if "error" in self.__get_me():
            self.auth_succeed, self.auth_msg = self.__sign_in()
        return self.__get_me()


class Socket(threading.Thread):

    def __init__(self, server_host, server_port, username, password):
        threading.Thread.__init__(self)

        self.__debug_socket = False

        self.__ws = None
        self.__url = "{}:{}".format(server_host, server_port)
        self.__auth = Authentication(server_host, server_port, username, password)
        self.__subscribe_target = ""
        self.__interval = 0.05
        self.subscribe("user", "console")
        self.__run_flag = threading.Event()
        self.__stop_flag = threading.Event()

        self.callback = lambda x: self.__print(x)

    def subscribe(self, _type, _name):
        if _type == "user":
            my_info = self.__auth.get_me()
            if "_id" in my_info:
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

    def __init__(self, server_host, server_port, username, password):
        self.__url = "http://{}:{}".format(server_host, server_port)
        self.__auth = Authentication(server_host, server_port, username, password)

    def get(self, url, params=None, without_auth=False):
        headers = dict()
        if not without_auth:
            token = self.__auth.get_token()
            headers = {
                "X-Token": token,
                "X-Username": token,
            }
        try:
            res = requests.get(
                "{}{}".format(self.__url, url),
                headers=headers,
                params=params)
            if res.status_code == 200:
                return res.json()
            else:
                if res.status_code == 401:
                    print("[api]Not Allowed")
                else:
                    print("[api]{}".format(res.status_code))
                return dict()
        except requests.exceptions.ConnectionError:
            print("[api]Connection Failed")
            return dict()

    def post(self, url, body=None, without_auth=False):
        headers = dict()
        if not without_auth:
            token = self.__auth.get_token()
            headers = {
                "X-Token": token,
                "X-Username": token,
            }
        try:
            res = requests.post(
                "{}{}".format(self.__url, url),
                headers=headers,
                json=body)
            if res.status_code == 200:
                return res.json()
            else:
                if res.status_code == 401:
                    print("[api]Not Allowed")
                else:
                    print("[api]{}".format(res.status_code))
                return dict()
        except requests.exceptions.ConnectionError:
            print("[api]Connection Failed")
            return dict()

    # /api/auth
    def get_me(self):
        # return self.get(
        #     "/api/auth/me",
        # )
        return self.__auth.get_me()

    # /api/game
    def get_room_status(self, room):
        return self.get(
            "/api/game/room-status",
            params={
                "room": room,
            }
        )

    def get_room_terrain(self, room):
        return self.get(
            "/api/game/room-terrain",
            params={
                "room": room,
            },
            without_auth=True,
        )

    def get_rooms_terrain(self, room_list):
        return self.post(
            "/api/game/rooms",
            body={
                "rooms": room_list,
            },
            without_auth=True,
        )
        # 0 == plain, 1 == wall, 2 == swamp, 3 == wall & swamp

    def get_tick(self):  # no used
        return self.get(
            "/api/game/tick",
            without_auth=True,
        )

    def get_time(self):
        return self.get(
            "/api/game/time",
            without_auth=True,
        )

    def get_world_size(self):
        return self.get(
            "/api/game/world-size",
            without_auth=True,
        )

    def map_stat(self, room_list, stat_name="owner", interval=0):
        """
        /api/game/map-stats.
        get room info and user info of given room list.
        :param room_list: room name list.
        :param stat_name: owner, claim,
        creepsLost, creepsProduced, energyConstruction, energyControl, energyCreeps, energyHarvested.
        :param interval: 8, 180, 1440.
        :return: room info and user info
        (lastUsedCpu, lastUsedDirtyTime: unknown, cpuAvailable: bucket, cpu: max cpu, gcl),
        stats parameter is not effective, probable abandoned.
        """
        if stat_name in ["owner", "claim"]:
            stat_name += str(0)
        elif stat_name in ["creepsLost", "creepsProduced", "energyConstruction",
                           "energyControl", "energyCreeps", "energyHarvested"]:
            if interval in [8, 180, 1440]:
                stat_name += str(interval)
            else:
                stat_name += str(0)
        return self.post(
            "/api/game/map-stats",
            body={
                "rooms": room_list,
                "statName": stat_name,
            }
        )

    def room_overview(self, room):
        """
        /api/game/room-overview.
        :param room: room name.
        :return: nothing, probable abandoned.
        """
        return self.get(
            "/api/game/room-overview",
            params={
                "room": room,
                "interval": 8,
            }
        )
        # https://screeps.com/api/game/room-overview?interval=8&room=E1N8
        #
        # { ok, owner: { username, badge: { type, color1, color2, color3, param, flip } }, stats: { energyHarvested:
        # [ { value, endTime } ], energyConstruction: [ { value, endTime } ], energyCreeps: [ { value, endTime } ],
        # energyControl: [ { value, endTime } ],
        # creepsProduced: [ { value, endTime } ],
        # creepsLost: [ { value, endTime } ] },
        # statsMax: { energy1440, energyCreeps1440, energy8, energyControl8, creepsLost180, energyHarvested8, energy180,
        # energyConstruction180, creepsProduced8, energyControl1440, energyCreeps8, energyHarvested1440, creepsLost1440,
        # energyConstruction1440, energyHarvested180, creepsProduced180, creepsProduced1440, energyCreeps180,
        # energyControl180, energyConstruction8, creepsLost8 } }

    def place_construction_site(self, room, x, y, structure_type):
        return self.post(
            "/api/game/create-construction",
            body={
                "room": room,
                "x": x,
                "y": y,
                "structureType": structure_type,
            }
        )

    def place_spawn(self, room, x, y, name):
        return self.post(
            "/api/game/place-spawn",
            body={
                "room": room,
                "x": x,
                "y": y,
                "name": name,
            }
        )

    def remove_construction_site(self, _id):
        """
        remove construction site.
        /api/game/add-object-intent return ok, but not effective.
        use /api/user/console instead.
        :param _id: target _id.
        :return: result
        """
        # return self.post(  # API return ok, but not effective
        #     "/api/game/add-object-intent",
        #     body={
        #         "_id": _id,
        #         "room": room,
        #         "name": "remove",
        #         "intent": {},
        #     }
        # )
        return self.post_user_console("Game.getObjectById('{}').remove()".format(_id))

    def remove_creep(self, _id):
        """
        kill a creep.
        /api/game/add-object-intent return ok, but not effective.
        use /api/user/console instead.
        :param _id: target _id.
        :return: result
        """
        return self.post_user_console("Game.getObjectById('{}').suicide()".format(_id))

    def remove_structure(self, _id):
        """
        remove structure.
        /api/game/add-object-intent return ok, but not effective.
        use /api/user/console instead.
        :param _id: target _id.
        :return: result
        """
        # return self.post(  # API return ok, but not effective
        #     "/api/game/add-object-intent",
        #     body={
        #         "_id": "room",
        #         "room": room,
        #         "name": "destroyStructure",
        #         "intent": [{
        #             "id": _id,
        #             "roomName": room,
        #             "user": self.get_me()["_id"],
        #         }]
        #     }
        # )
        return self.post_user_console("Game.getObjectById('{}').destroy()".format(_id))

    def unclaim_controller(self, _id):  # TODO: untested
        """
        unclaim controller.
        /api/game/add-object-intent return ok, but not effective.
        use /api/user/console instead.
        :param _id: target _id.
        :return: result
        """
        return self.post_user_console("Game.getObjectById('{}').unclaim()".format(_id))

    # [POST] https://screeps.com/api/game/add-object-intent
    #
    # post data: { _id, room, name, intent }
    # response: { ok, result: { nModified, ok, upserted: [ { index, _id } ], n }, connection: { host, id, port } }
    # _id is the game id of the object to affect (except for destroying structures),
    # room is the name of the room it's in this method is used for a variety of actions,
    # depending on the name and intent parameters
    #       remove flag: name = "remove", intent = {}
    #       destroy structure: _id = "room",
    #                           name = "destroyStructure",
    #                           intent = [ {id: <structure id>, roomName, <room name>, user: <user id>} ]
    #               can destroy multiple structures at once
    #       suicide creep: name = "suicide", intent = {id: <creep id>}
    #       unclaim controller: name = "unclaim", intent = {id: <controller id>}
    #               intent can be an empty object for suicide and unclaim,
    #               but the web interface sends the id in it, as described
    #       remove construction site: name = "remove", intent = {}

    #     COLOR_RED: 1,
    #     COLOR_PURPLE: 2,
    #     COLOR_BLUE: 3,
    #     COLOR_CYAN: 4,
    #     COLOR_GREEN: 5,
    #     COLOR_YELLOW: 6,
    #     COLOR_ORANGE: 7,
    #     COLOR_BROWN: 8,
    #     COLOR_GREY: 9,
    #     COLOR_WHITE: 10,

    # /api/register
    def check_email(self, email):
        return self.get(
            "/api/register/check-email",
            params={
                "email": email
            },
            without_auth=True,
        )

    def check_username(self, username):
        return self.get(
            "/api/register/check-username",
            params={
                "username": username
            },
            without_auth=True,
        )

    def set_password(self, password):
        res = self.post(
            # api from screepsmod-auth
            # https://github.com/ScreepsMods/screepsmod-auth/blob/master/lib/register.js
            "/api/user/password",
            body={
                "oldPassword": config.PASSWORD,
                "password": password,
            }
        )
        if "ok" in res and res["ok"] == 1:
            config.PASSWORD = password
        return res

    def set_username(self, username, password, email=None):
        body = {
            "username": username,
            "password": password,
        }
        if email is not None:
            body["email"] = email
        return self.post(
            # api from screepsmod-auth
            # https://github.com/ScreepsMods/screepsmod-auth/blob/master/lib/register.js
            "/api/register/submit",
            body=body,
            without_auth=True,
        )

    # /api/user
    def clone_branch(self, old_branch, new_branch):
        return self.post(
            "/api/user/clone-branch",
            body={
                "branch": old_branch,
                "newName": new_branch,
            }
        )

    def delete_branch(self, branch):
        return self.post(
            "/api/user/delete-branch",
            body={
                "branch": branch
            }
        )

    def find_user(self, username="", _id=None):
        """
        /api/user/find, get user info in game.
        :param username: username.
        :param _id: user _id.
        :return: username, _id, gcl.
        """
        return self.get(
            "/api/user/find",
            params={
                "username": username,
            }
            if _id is None else
            {
                "id": _id
            },
            without_auth=True,
        )

    def get_start_room(self):
        return self.get(
            "/api/user/world-start-room",
        )

    def get_all_code(self):
        return self.get(
            "/api/user/branches",
        )

    def get_code(self, branch=None):
        params = dict()
        if branch is not None:
            params["branch"] = branch
        return self.get(
            "/api/user/code",
            params=params,
        )

    def get_user_memory(self, raw=False):
        memory = self.get(
            "/api/user/memory",
        )
        if raw:
            return memory
        import base64
        import zlib
        import json
        byte_string = base64.b64decode(memory["data"][3:])
        json_string = zlib.decompress(byte_string, 15 + 32)
        memory["data"] = json.loads(json_string)
        return memory

    def get_user_stat(self):
        """
        /api/user/stats.
        :return: nothing, probable abandoned.
        """
        return self.get(
            "/api/user/stats",
            params={
                "interval": 8,
            },
            without_auth=True,
        )

    def get_user_overview(self):
        """
        /api/user/overview.
        :return: room list only, probable abandoned.
        """
        return self.get(
            "/api/user/overview",
        )

    def get_world_status(self):
        """
        /api/user/world-status.
        :return: empty, normal, lost.
        """
        return self.get(
            "/api/user/world-status",
        )

    def post_code(self, modules, branch):
        return self.post(
            "/api/user/code",
            body={
                "modules": modules,
                "branch": branch,
            }
        )

    def post_user_console(self, expression):
        return self.post(
            "/api/user/console",
            body={
                "expression": expression
            }
        )

    def respawn(self):  # TODO: untested
        return self.post(
            "/api/user/respawn",
        )

    def set_active_branch(self, branch):
        return self.post(
            "/api/user/set-active-branch",
            body={
                "activeName": "activeWorld",
                "branch": branch,
            }
        )

    def set_user_memory(self, value, path=None):  # TODO: untested
        body = {
            "value": value
        }
        if path is not None:
            body["path"] = path
        return self.post(
            "/api/user/memory",
            body=body,
        )


if __name__ == "__main__":
    import config
    api = Api(config.SERVER_HOST, config.SERVER_PORT, config.USERNAME, config.PASSWORD)
    print(api.get_time())
