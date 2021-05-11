
# —*- coding: utf-8 -*-

import copy
import curses
import threading

import datetime
import json
import linecache
import keyboard
import re
import os
import pyperclip
import sys

import config
import screeps_api
import screeps_auto_push


class MapView(object):

    def __init__(self):
        self.__room_matrix = [["." for _ in range(50)] for _ in range(50)]
        self.room_name = ""
        self.__api = screeps_api.Api(config.SERVER_HOST, config.SERVER_PORT, config.USERNAME, config.PASSWORD)
        # user_room_list = api.get_user_overview()["rooms"]
        # if len(user_room_list) > 0:
        #     self.room_name = user_room_list[0]
        start_room_info = self.__api.get_start_room()
        if "room" in start_room_info:
            self.room_name = self.__api.get_start_room()["room"][0]
        self.__room_object = dict()
        self.__room_socket = None
        self.__cpu_socket = None
        self.cpu = 0
        self.cpu_max = 100
        self.memory = 0
        self.memory_max = 2 * 1024 * 1024  # 2M
        self.game_time = 0
        self.tick_duration = 0

        self.room_x = 24
        self.room_y = 15

        self.__confirm_menu_template = [
            {
                "item": "CANCEL",
                "sub_menu": None,
            },
            {
                "item": "CONFIRM",
                "sub_menu": None,
            },
        ]
        self.operate_menu = {
            "item": "operation_menu",
            "sub_menu": [
                {
                    "item": "Place spawn",
                    "sub_menu": self.__confirm_menu_template,
                },
                {
                    "item": "Create Construction Site",
                    "sub_menu": [
                        {
                            "item": "road",
                            "sub_menu": self.__confirm_menu_template,
                        },
                        {
                            "item": "container",
                            "sub_menu": self.__confirm_menu_template,
                        },
                        {
                            "item": "extension",
                            "sub_menu": self.__confirm_menu_template,
                        },
                        {
                            "item": "rampart",
                            "sub_menu": self.__confirm_menu_template,
                        },
                        {
                            "item": "tower",
                            "sub_menu": self.__confirm_menu_template,
                        },
                        {
                            "item": "storage",
                            "sub_menu": self.__confirm_menu_template,
                        },
                        {
                            "item": "link",
                            "sub_menu": self.__confirm_menu_template,
                        },
                        {
                            "item": "extractor",
                            "sub_menu": self.__confirm_menu_template,
                        },
                        {
                            "item": "lab",
                            "sub_menu": self.__confirm_menu_template,
                        },
                        {
                            "item": "terminal",
                            "sub_menu": self.__confirm_menu_template,
                        },
                        {
                            "item": "spawn",
                            "sub_menu": self.__confirm_menu_template,
                        },
                        {
                            "item": "observer",
                            "sub_menu": self.__confirm_menu_template,
                        },
                        {
                            "item": "powerSpawn",
                            "sub_menu": self.__confirm_menu_template,
                        },
                    ],
                },
                {
                    "item": "Create Flag",
                    "sub_menu": self.__confirm_menu_template,
                },
                {
                    "item": "Delete",
                    "sub_menu": self.__confirm_menu_template,
                },
            ]
        }
        self.current_menu = None
        self.menu_depth = -1
        self.menu_path = list()
        self.menu_selected = 0

    def watch(self):
        self.__room_matrix = [["." for _ in range(50)] for _ in range(50)]
        self.__room_socket = screeps_api.Socket(config.SERVER_HOST, config.SERVER_PORT,
                                                config.USERNAME, config.PASSWORD)
        self.__room_socket.subscribe("room", self.room_name)
        self.__room_socket.callback = self.__room_callback
        self.__room_socket.start()

        self.__cpu_socket = screeps_api.Socket(config.SERVER_HOST, config.SERVER_PORT, config.USERNAME, config.PASSWORD)
        self.__cpu_socket.subscribe("user", "cpu")
        self.__cpu_socket.callback = self.__cpu_callback
        self.__cpu_socket.start()

    def stop(self):
        self.__room_socket.stop()
        self.__cpu_socket.stop()
        log("socket stopped")
        self.__room_socket.join()
        self.__cpu_socket.join()
        log("socket joined")

    def __room_callback(self, message):
        data = json.loads(message)[1]["objects"]
        for i, item in data.items():
            # log("{} {}".format(i, item))
            if i not in self.__room_object:
                self.__room_object[i] = item
            else:
                self.__room_object[i].update(item)

        # for i in self.__room_object:
        #     if self.__room_object[i]["room"] == self.__room_name and i not in data:
        #         del self.__room_object[i]
        self.__refresh_data()

    def __cpu_callback(self, message):
        data = json.loads(message)[1]
        self.cpu = data["cpu"]
        self.memory = data["memory"]
        self.game_time = self.__api.get_time()["time"]
        self.tick_duration = self.__api.get_tick()["tick"]

    def __refresh_data(self):
        self.__room_matrix = [[config.CHAR_MAP["plain"] for _ in range(50)] for _ in range(50)]
        api = screeps_api.Api(config.SERVER_HOST, config.SERVER_PORT, config.USERNAME, config.PASSWORD)
        terrain_data = api.get_room_terrain(self.room_name)["terrain"]
        for i in terrain_data:
            self.__room_matrix[int(i["y"])][int(i["x"])] = config.CHAR_MAP[i["type"]] \
                if i["type"] in config.CHAR_MAP else "?"
        for i, item in self.__room_object.items():
            if item["room"] == self.room_name:
                self.__room_matrix[int(item["y"])][int(item["x"])] = config.CHAR_MAP[item["type"]] \
                    if item["type"] in config.CHAR_MAP else "?"
        # for i in self.__room_matrix:
        #     log("".join(i))

    def get_matrix(self):
        return self.__room_matrix

    def get_info(self):
        info_list = list()
        for i, item in self.__room_object.items():
            if item is not None and "room" in item and item["room"] == self.room_name \
                    and item["x"] == self.room_x and item["y"] == self.room_y:
                # log(json.dumps(item))
                info = copy.deepcopy(item)
                if "body" in info:
                    body = list()
                    for part in info["body"]:
                        body.append(config.CHAR_BODY_PART[part["type"]]
                                    if part["type"] in config.CHAR_BODY_PART else "?")
                    info["body"] = "".join(body)
                if "creepBody" in info:
                    body = list()
                    for part in info["creepBody"]:
                        body.append(config.CHAR_BODY_PART[part]
                                    if part in config.CHAR_BODY_PART else "?")
                    info["creepBody"] = "".join(body)
                for key in ["meta", "$loki", "actionLog"]:
                    if key in info:
                        del info[key]
                info_list.append(info)
        return info_list[:5]

    def change_room(self, direction_1, direction_2=""):
        self.stop()
        self.room_name = self.__convert_room_name(direction_1, direction_2)
        self.watch()

    def get_mini_map(self):
        name_list = [
            self.__convert_room_name("north", "west"),
            self.__convert_room_name("north"),
            self.__convert_room_name("north", "east"),
            self.__convert_room_name("west"),
            self.room_name,
            self.__convert_room_name("east"),
            self.__convert_room_name("south", "west"),
            self.__convert_room_name("south"),
            self.__convert_room_name("south", "east"),
        ]
        minimap = [
            " {: >6} | {: ^6} | {: <6} ".format(name_list[0], name_list[1], name_list[2]),
            "--------+--------+--------",
            " {: >6} |[{: ^6}]| {: <6} ".format(name_list[3], name_list[4], name_list[5]),
            "--------+--------+--------",
            " {: >6} | {: ^6} | {: <6} ".format(name_list[6], name_list[7], name_list[8])
        ]
        return minimap

    def __convert_room_name(self, direction_1, direction_2=""):
        re_res = re.match(r"(\w)(\d+)(\w)(\d+)", self.room_name)
        if re_res is None:
            return ""
        room_name_list = list(re_res.groups())
        room_name_list[1] = int(room_name_list[1])
        room_name_list[3] = int(room_name_list[3])
        for direction in [direction_1, direction_2]:
            if direction.lower() not in ["west", "south", "north", "east"]:
                continue
            if direction.lower() == "west":
                if room_name_list[0] == "E":
                    if room_name_list[1] == 0:
                        room_name_list[0] = "W"
                    else:
                        room_name_list[1] -= 1
                else:
                    room_name_list[1] += 1
            elif direction.lower() == "south":
                if room_name_list[2] == "N":
                    if room_name_list[3] == 0:
                        room_name_list[2] = "S"
                    else:
                        room_name_list[3] -= 1
                else:
                    room_name_list[3] += 1
            elif direction.lower() == "north":
                if room_name_list[2] == "S":
                    if room_name_list[3] == 0:
                        room_name_list[2] = "N"
                    else:
                        room_name_list[3] -= 1
                else:
                    room_name_list[3] += 1
            elif direction.lower() == "east":
                if room_name_list[0] == "W":
                    if room_name_list[1] == 0:
                        room_name_list[0] = "E"
                    else:
                        room_name_list[1] -= 1
                else:
                    room_name_list[1] += 1
        room_name_list[1] = str(room_name_list[1])
        room_name_list[3] = str(room_name_list[3])
        return "".join(room_name_list)

    def nav_menu(self, op):
        if op == "enter":
            self.menu_depth += 1
            if self.menu_depth < len(self.menu_path):
                self.menu_path[self.menu_depth] = self.menu_selected
            else:
                self.menu_path.append(self.menu_selected)
            self.current_menu = self.operate_menu
            for i in range(1, self.menu_depth + 1):
                self.current_menu = self.current_menu["sub_menu"][self.menu_path[i]]
            if self.current_menu["sub_menu"] is None:
                path = self.get_menu_path_item()
                log(path)
                if path[0] == "Place spawn" and path[1] == "CONFIRM":
                    self.__api.place_spawn(self.room_name, self.room_x, self.room_y, "Spawn1")  # TODO: input
                elif path[0] == "Create Construction Site" and path[2] == "CONFIRM":
                    self.__api.place_construction_site(self.room_name, self.room_x, self.room_y, path[1])
                elif path[0] == "Create Flag":
                    pass  # TODO: Menu -> API
                elif path[0] == "Delete":
                    pass  # TODO: Menu -> API
                self.menu_depth = -1
                self.current_menu = None
            else:
                if self.menu_depth + 1 < len(self.menu_path):
                    self.menu_selected = self.menu_path[self.menu_depth + 1]
                    if self.menu_selected >= len(self.current_menu["sub_menu"]):
                        self.menu_selected = 0
                else:
                    self.menu_selected = 0
        elif op == "back":
            if self.menu_depth > -1:
                self.menu_depth -= 1
            if self.menu_depth == -1:
                self.current_menu = None
            else:
                self.current_menu = self.operate_menu
                for i in range(1, self.menu_depth + 1):
                    self.current_menu = self.current_menu["sub_menu"][self.menu_path[i]]
                self.menu_selected = self.menu_path[self.menu_depth + 1]
        elif op == "down":
            if self.menu_depth != -1:
                self.menu_selected = (self.menu_selected + 1) % len(self.current_menu["sub_menu"])
        elif op == "up":
            if self.menu_depth != -1:
                self.menu_selected = (self.menu_selected - 1) % len(self.current_menu["sub_menu"])
        # for _i, i in enumerate(self.current_menu["sub_menu"]):
        #     if _i == self.menu_selected:
        #         log("menu", i["item"], "selected")
        #     else:
        #         log("menu", i["item"])

    def get_menu_path_item(self):
        res = list()
        if self.menu_depth > 0:
            current_menu = self.operate_menu
            for i in range(1, self.menu_depth + 1):
                current_menu = current_menu["sub_menu"][self.menu_path[i]]
                res.append(current_menu["item"])
        return res


class ConsoleView(object):

    def __init__(self):
        self.line_length = 80

        self.__socket = screeps_api.Socket(config.SERVER_HOST, config.SERVER_PORT, config.USERNAME, config.PASSWORD)
        self.__api = screeps_api.Api(config.SERVER_HOST, config.SERVER_PORT, config.USERNAME, config.PASSWORD)

        self.__log_list = list()
        self.__log_max_length = 2000
        self.__cmd = None

    def watch(self):
        self.__socket.subscribe("user", "console")
        self.__socket.callback = self.__console_callback
        self.__socket.start()

    def stop(self):
        self.__socket.stop()
        self.__socket.join()

    def get_log(self):
        return copy.deepcopy(self.__log_list)

    def send_cmd(self, cmd):
        self.__cmd = cmd

    def __console_callback(self, message):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = json.loads(message)[1]
        if "messages" in data:
            for line in data["messages"]["log"]:
                for _l in self.__parse_line(line):
                    self.__log_list.append({
                        "type": "normal",
                        "log": _l,
                        "time": now,
                    })
            del data["messages"]["log"]
        if "error" in data:
            for line in data["error"].split("\n"):
                for _l in self.__parse_line(line):
                    self.__log_list.append({
                        "type": "error",
                        "log": _l,
                        "time": now,
                    })
            del data["error"]
        if "messages" in data:
            for line in data["messages"]["results"]:
                for _l in self.__parse_line(line):
                    self.__log_list.append({
                        "type": "output",
                        "log": _l,
                        "time": now,
                    })
            del data["messages"]["results"]
        if self.__cmd is not None:
            for _l in self.__parse_line(self.__cmd):
                self.__log_list.append({
                    "type": "command",
                    "log": _l
                })
            self.__api.post_user_console(self.__cmd)
            self.__cmd = None

        if len(data["messages"].keys()) == 0:
            del data["messages"]
        if len(data.keys()) > 0:
            for _l in self.__parse_line(json.dumps(data)):
                self.__log_list.append({
                    "type": "debug",
                    "log": _l
                })

        self.__refresh_data()

    def __parse_line(self, line):
        line_list = list()
        _l = copy.deepcopy(line)
        # line_list.append(_l[:self.line_length - 19])  # len("YYYY-MM-DD HH:MM:SS") = 19
        # _l = _l[self.line_length - 19:]
        while len(_l) > self.line_length:
            line_list.append(_l[:self.line_length])
            _l = _l[self.line_length:]
        if len(_l) > 0:
            line_list.append(_l)
        return line_list

    def __refresh_data(self):
        if len(self.__log_list) > self.__log_max_length:
            self.__log_list = self.__log_list[len(self.__log_list) - 2000:]


class Render(object):

    def __init__(self):
        self.__quit = False
        self.__pause = False

        self.__screen_height = 0
        self.__screen_width = 0

        self.__cursor_x = 0
        self.__cursor_y = 0

        self.__panel = "console"  # default panel

        # Map Panel
        self.__map_view = MapView()
        self.__pause_map = False
        self.__room_display_left, self.__room_display_top = 2, 4
        self.__room_display_width, self.__room_display_height = 50, 30
        self.__room_max_width, self.__room_max_height = 50, 50
        self.__room_view_left, self.__room_view_right = 0, self.__room_display_width
        self.__room_view_top, self.__room_view_bottom = 0, self.__room_display_height
        self.__room_object_info = list()
        self.__room_object_selected = 0
        self.__cursor_x = self.__room_display_left + self.__room_display_width // 2 - 1
        self.__cursor_y = self.__room_display_top + self.__room_display_height // 2 - 1
        self.__shift_step = 5

        self.__map_view.room_x = self.__cursor_x - self.__room_display_left + self.__room_view_left
        self.__map_view.room_y = self.__cursor_y - self.__room_display_top + self.__room_view_top

        # Console Panel
        self.__console_view = ConsoleView()
        self.__log_index = -1
        self.__cmd = ""
        self.__cursor_pos = 0
        self.__cmd_left = 0
        self.__cmd_history = list()
        self.__cmd_history_max = 20
        self.__cmd_index = 0

        self.map_source = None

    def start(self):
        self.__map_view.watch()
        self.__console_view.watch()
        curses.wrapper(self.display)

    def stop(self):
        self.__quit = True

    def display(self, screen):
        keyboard.on_press(lambda event: self.keyboard_handler(event))

        # Clear and refresh the screen for a blank canvas
        # screen.clear()
        self.__screen_height, self.__screen_width = screen.getmaxyx()
        # screen.refresh()

        self.__console_view.line_length = self.__screen_width

        # Start colors in curses
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_WHITE)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_CYAN)

        while not self.__quit:

            if self.__pause:
                screen.move(self.__cursor_y, self.__cursor_x)
                screen.refresh()
                continue

            # Initialization
            screen.clear()
            self.__screen_height, self.__screen_width = screen.getmaxyx()

            if self.__panel == "map":
                screen.addstr(0, 0, "{: <16}".format("[F1]Map"), curses.color_pair(2))
            else:
                screen.addstr(0, 0, "{: <16}".format("[F1]Map"), curses.color_pair(1))

            if self.__panel == "console":
                screen.addstr(0, 16, "{: <16}".format("[F2]Console"), curses.color_pair(2))
            else:
                screen.addstr(0, 16, "{: <16}".format("[F2]Console"), curses.color_pair(1))

            if self.__panel == "memory":
                screen.addstr(0, 32, "{: <16}".format("[F3]Memory"), curses.color_pair(2))
            else:
                screen.addstr(0, 32, "{: <16}".format("[F3]Memory"), curses.color_pair(1))

            screen.addstr(0, 16 * 3, " " * (self.__screen_width - 16 * 4), curses.color_pair(1))
            screen.addstr(0, self.__screen_width - 16, "{: <16}".format("[ESC]Exit"), curses.color_pair(1))

            if self.__panel == "map":
                # render room info
                # TODO: rcl (no api found)
                screen.addstr(2, 2, " Room: {}".format(self.__map_view.room_name), curses.color_pair(0))
                if self.__pause_map:
                    screen.addstr(2, self.__room_display_left + self.__room_display_width - len("PAUSE"),
                                  "PAUSE", curses.color_pair(1))

                # render room detail
                for y, line in enumerate(self.__map_view.get_matrix()[self.__room_view_top: self.__room_view_bottom]):
                    screen.addstr(self.__room_display_top + y, self.__room_display_left,
                                  "".join(line[self.__room_view_left: self.__room_view_right]), curses.color_pair(0))

                # render mini map
                screen.addstr(self.__room_display_top + self.__room_display_height + 1,
                              self.__room_display_left,
                              " Map:",
                              curses.color_pair(0))
                for y, line in enumerate(self.__map_view.get_mini_map()):
                    screen.addstr(self.__room_display_top + self.__room_display_height + 3 + y,
                                  self.__room_display_left,
                                  line, curses.color_pair(0))

                # render object list
                room_x = self.__cursor_x - self.__room_display_left + self.__room_view_left
                room_y = self.__cursor_y - self.__room_display_top + self.__room_view_top
                screen.addstr(self.__room_display_top + self.__room_display_height + 1,
                              self.__room_display_left + self.__room_display_width - len("Position x:XX y:YY") - 1,
                              "Position x:{: >2} y:{: >2}".format(room_x, room_y),
                              curses.color_pair(0))
                for y, obj in enumerate(self.__room_object_info):
                    screen.addstr(self.__room_display_top + self.__room_display_height + 3 + y,
                                  self.__room_display_left + self.__room_display_width - len("Position x:XX y:YY") - 1,
                                  obj["type"],
                                  curses.color_pair(1) if y == self.__room_object_selected else curses.color_pair(0))

                # render stat
                cpu_bar = [1] * (self.__room_display_width - 1)
                for i in range(int(1.0 * self.__map_view.cpu / self.__map_view.cpu_max * len(cpu_bar))):
                    cpu_bar[i] = 6
                cpu_info = "CPU:{: >3}/{: >3}".format(self.__map_view.cpu, self.__map_view.cpu_max)
                for i in range(len(cpu_bar)):
                    screen.addstr(self.__room_display_top + self.__room_display_height + 3 + 6,
                                  self.__room_display_left + i,
                                  cpu_info[i] if i < len(cpu_info) else " ",
                                  curses.color_pair(cpu_bar[i]))

                memory_bar = [1] * (self.__room_display_width - 1)
                for i in range(int(1.0 * self.__map_view.memory / self.__map_view.memory_max * len(memory_bar))):
                    memory_bar[i] = 6
                memory_info = "Memory:{:7.2f}K/{:7.2f}K".format(self.__map_view.memory / 1024.0,
                                                                self.__map_view.memory_max / 1024.0)
                for i in range(len(memory_bar)):
                    screen.addstr(self.__room_display_top + self.__room_display_height + 3 + 7,
                                  self.__room_display_left + i,
                                  memory_info[i] if i < len(memory_info) else " ",
                                  curses.color_pair(memory_bar[i]))

                # TODO: bucket, gcl (api map-stat)
                # TODO: Credits, Power (no api found)
                screen.addstr(self.__room_display_top + self.__room_display_height + 3 + 8,
                              self.__room_display_left,
                              "Tick Duration: {}ms, Game Time: {:,} ".format(self.__map_view.tick_duration,
                                                                             self.__map_view.game_time % 1000000000),
                              curses.color_pair(0))

                if self.__map_view.menu_depth > -1:
                    # render menu
                    screen.addstr(2, 55, "Operation Menu", curses.color_pair(0))
                    menu_path = self.__map_view.get_menu_path_item()
                    for indent, line in enumerate(self.__map_view.get_menu_path_item()):
                        screen.addstr(4 + indent, 55 + 4 * indent,
                                      line, curses.color_pair(0))
                    if self.__map_view.current_menu["sub_menu"] is not None:
                        for y, line in enumerate(self.__map_view.current_menu["sub_menu"]):
                            screen.addstr(4 + len(menu_path) + y, 55 + 4 * len(menu_path),
                                          line["item"][:self.__screen_width - 55 - 4 * len(menu_path)],
                                          curses.color_pair(1)
                                          if y == self.__map_view.menu_selected else curses.color_pair(0))
                else:
                    # render info
                    self.__room_object_info = self.__map_view.get_info()
                    self.__room_object_selected = self.__room_object_selected \
                        if self.__room_object_selected < len(self.__room_object_info) else 0
                    if len(self.__room_object_info) > 0:
                        # log(json.dumps(self.__room_object_info[0], indent=4, sort_keys=True))
                        screen.addstr(2, 55,
                                      "{} {} {}".format(self.__room_object_info[self.__room_object_selected]["type"],
                                                        self.__map_view.room_x, self.__map_view.room_y),
                                      curses.color_pair(0))
                        info_list = json.dumps(self.__room_object_info[self.__room_object_selected],
                                               indent=4, sort_keys=True).splitlines()
                        for y, line in enumerate(info_list[: self.__screen_height - 5]):
                            screen.addstr(4 + y, 55,
                                          line[:self.__screen_width - 55], curses.color_pair(0))

                screen.move(self.__cursor_y, self.__cursor_x)

            elif self.__panel == "console":
                log_list = self.__console_view.get_log()
                index_range = self.__screen_height - 2 if len(log_list) > self.__screen_height else len(log_list)
                if len(log_list) <= self.__screen_height - 2:
                    index_start = 0
                elif self.__log_index == -1:
                    index_start = len(log_list) - index_range
                else:
                    index_start = self.__log_index
                for i in range(index_start, index_start + index_range):
                    if i >= len(log_list):  # BUG: index_start + index_range > len(log_list)
                        break
                    # log("{} {} {}".format(i, log_list[i]["type"], log_list[i]["log"]))
                    if log_list[i]["type"] == "error":
                        screen.addstr(1 + i - index_start, 0, log_list[i]["log"], curses.color_pair(3))
                    elif log_list[i]["type"] == "command":
                        screen.addstr(1 + i - index_start, 0, "> {}".format(log_list[i]["log"]), curses.color_pair(4))
                    elif log_list[i]["type"] == "output":
                        screen.addstr(1 + i - index_start, 0, log_list[i]["log"], curses.color_pair(5))
                    else:
                        screen.addstr(1 + i - index_start, 0, log_list[i]["log"], curses.color_pair(0))
                cmd = copy.deepcopy(self.__cmd)[self.__cmd_left:][:self.__screen_width - 2 - 1]
                screen.addstr(self.__screen_height - 1, 0, "> ", curses.color_pair(1))
                for i, ch in enumerate(cmd):
                    screen.insch(self.__screen_height - 1, 2 + i, str(ch), curses.color_pair(1))
                for i in range(2 + len(cmd), self.__screen_width):
                    screen.insch(self.__screen_height - 1, i, " ", curses.color_pair(1))

                screen.move(self.__screen_height - 1, 2 + self.__cursor_pos)

            # Refresh the screen
            screen.refresh()

        self.__map_view.stop()
        self.__console_view.stop()

    def keyboard_handler(self, event):
        # https://stackoverflow.com/questions/10266281/obtain-active-window-using-python
        if sys.platform == "win32":
            from win32gui import GetWindowText, GetForegroundWindow
            if "screeps-client" not in GetWindowText(GetForegroundWindow()):
                return

        # clear_output()
        log(event.to_json())

        if event.name == "f1":
            self.__panel = "map"
            return
        if event.name == "f2":
            self.__panel = "console"
            return
        if event.name == "f3":
            self.__panel = "memory"
            return
        if event.name == "f12":
            self.__pause = not self.__pause
            return
        if event.name == "esc":
            self.__quit = True
            return

        if self.__panel == "map":
            if event.name == "p" and keyboard.is_pressed("ctrl"):
                self.__pause_map = not self.__pause_map
                if self.__pause_map:
                    self.__map_view.stop()
                else:
                    self.__map_view = MapView()
                    self.__map_view.watch()
                return

            if event.name == "r" and keyboard.is_pressed("ctrl"):
                self.__map_view.stop()
                self.__map_view = MapView()
                self.__map_view.watch()
                return

            if event.name.lower() in "hjklyubn" \
                    and self.__cursor_x in range(self.__room_display_left,
                                                 self.__room_display_left + self.__room_display_width) \
                    and self.__cursor_y in range(self.__room_display_top,
                                                 self.__room_display_top + self.__room_display_height):
                if event.name.lower() == "h":  # left
                    if keyboard.is_pressed("ctrl"):
                        self.__map_view.change_room("west")
                    elif keyboard.is_pressed("shift"):
                        self.__cursor_x = max(self.__room_display_left,
                                              self.__cursor_x - self.__shift_step)
                    else:
                        self.__cursor_x = max(self.__room_display_left, self.__cursor_x - 1)
                    # if self.__cursor_x - 3 < 5:
                    #     self.__room_view_left = max(0, self.__room_view_left - 1)
                    #     self.__room_view_right = max(30, self.__room_view_right - 1)
                if event.name.lower() == "l":  # right
                    if keyboard.is_pressed("ctrl"):
                        self.__map_view.change_room("east")
                    elif keyboard.is_pressed("shift"):
                        self.__cursor_x = min(self.__room_display_left + self.__room_display_width - 1,
                                              self.__cursor_x + self.__shift_step)
                    else:
                        self.__cursor_x = min(self.__room_display_left + self.__room_display_width - 1,
                                              self.__cursor_x + 1)
                    # if 33 - self.__cursor_x < 5:
                    #     self.__room_view_left = min(20, self.__room_view_left + 1)
                    #     self.__room_view_right = min(50, self.__room_view_right + 1)
                if event.name.lower() == "k":  # up
                    if keyboard.is_pressed("ctrl"):
                        self.__map_view.change_room("north")
                    elif keyboard.is_pressed("shift"):
                        if self.__room_display_top == self.__cursor_y \
                                and self.__room_view_top > 0:
                            self.__room_view_top = max(0, self.__room_view_top - self.__shift_step)
                            self.__room_view_bottom = max(self.__room_display_height,
                                                          self.__room_view_bottom - self.__shift_step)
                        else:
                            self.__cursor_y = max(self.__room_display_top,
                                                  self.__cursor_y - self.__shift_step)
                    else:
                        if self.__room_display_top == self.__cursor_y \
                                and self.__room_view_top > 0:
                            self.__room_view_top = max(0, self.__room_view_top - 1)
                            self.__room_view_bottom = max(self.__room_display_height, self.__room_view_bottom - 1)
                        else:
                            self.__cursor_y = max(self.__room_display_top, self.__cursor_y - 1)
                if event.name.lower() == "j":  # down
                    if keyboard.is_pressed("ctrl"):
                        self.__map_view.change_room("south")
                    elif keyboard.is_pressed("shift"):
                        if self.__room_display_top + self.__room_display_height - 1 == self.__cursor_y \
                                and self.__room_view_bottom < self.__room_max_height:
                            self.__room_view_top = min(self.__room_max_height - self.__room_display_height,
                                                       self.__room_view_top + self.__shift_step)
                            self.__room_view_bottom = min(self.__room_max_height,
                                                          self.__room_view_bottom + self.__shift_step)
                        else:
                            self.__cursor_y = min(self.__room_display_top + self.__room_display_height - 1,
                                                  self.__cursor_y + self.__shift_step)
                    else:
                        if self.__room_display_top + self.__room_display_height - 1 == self.__cursor_y \
                                and self.__room_view_bottom < self.__room_max_height:
                            self.__room_view_top = min(self.__room_max_height - self.__room_display_height,
                                                       self.__room_view_top + 1)
                            self.__room_view_bottom = min(self.__room_max_height, self.__room_view_bottom + 1)
                        else:
                            self.__cursor_y = min(self.__room_display_top + self.__room_display_height - 1,
                                                  self.__cursor_y + 1)

                if event.name.lower() == "y":  # up left
                    if keyboard.is_pressed("ctrl"):
                        self.__map_view.change_room("north", "west")
                    elif keyboard.is_pressed("shift"):
                        if self.__room_display_top == self.__cursor_y \
                                and self.__room_view_top > 0:
                            self.__room_view_top = max(0, self.__room_view_top - self.__shift_step)
                            self.__room_view_bottom = max(self.__room_display_height,
                                                          self.__room_view_bottom - self.__shift_step)
                        else:
                            self.__cursor_y = max(self.__room_display_top,
                                                  self.__cursor_y - self.__shift_step)
                        self.__cursor_x = max(self.__room_display_left,
                                              self.__cursor_x - self.__shift_step)
                    else:
                        if self.__room_display_top == self.__cursor_y \
                                and self.__room_view_top > 0:
                            self.__room_view_top = max(0, self.__room_view_top - 1)
                            self.__room_view_bottom = max(self.__room_display_height, self.__room_view_bottom - 1)
                        else:
                            self.__cursor_y = max(self.__room_display_top, self.__cursor_y - 1)
                        self.__cursor_x = max(self.__room_display_left, self.__cursor_x - 1)

                if event.name.lower() == "u":  # up right
                    if keyboard.is_pressed("ctrl"):
                        self.__map_view.change_room("north", "east")
                    elif keyboard.is_pressed("shift"):
                        if self.__room_display_top == self.__cursor_y \
                                and self.__room_view_top > 0:
                            self.__room_view_top = max(0, self.__room_view_top - self.__shift_step)
                            self.__room_view_bottom = max(self.__room_display_height,
                                                          self.__room_view_bottom - self.__shift_step)
                        else:
                            self.__cursor_y = max(self.__room_display_top,
                                                  self.__cursor_y - self.__shift_step)
                        self.__cursor_x = min(self.__room_display_left + self.__room_display_width - 1,
                                              self.__cursor_x + self.__shift_step)
                    else:
                        if self.__room_display_top == self.__cursor_y \
                                and self.__room_view_top > 0:
                            self.__room_view_top = max(0, self.__room_view_top - 1)
                            self.__room_view_bottom = max(self.__room_display_height, self.__room_view_bottom - 1)
                        else:
                            self.__cursor_y = max(self.__room_display_top, self.__cursor_y - 1)
                        self.__cursor_x = min(self.__room_display_left + self.__room_display_width - 1,
                                              self.__cursor_x + 1)

                if event.name.lower() == "b":  # down left
                    if keyboard.is_pressed("ctrl"):
                        self.__map_view.change_room("south", "west")
                    elif keyboard.is_pressed("shift"):
                        if self.__room_display_top + self.__room_display_height - 1 == self.__cursor_y \
                                and self.__room_view_bottom < self.__room_max_height:
                            self.__room_view_top = min(self.__room_max_height - self.__room_display_height,
                                                       self.__room_view_top + self.__shift_step)
                            self.__room_view_bottom = min(self.__room_max_height,
                                                          self.__room_view_bottom + self.__shift_step)
                        else:
                            self.__cursor_y = min(self.__room_display_top + self.__room_display_height - 1,
                                                  self.__cursor_y + self.__shift_step)
                        self.__cursor_x = max(self.__room_display_left,
                                              self.__cursor_x - self.__shift_step)
                    else:
                        if self.__room_display_top + self.__room_display_height - 1 == self.__cursor_y \
                                and self.__room_view_bottom < self.__room_max_height:
                            self.__room_view_top = min(self.__room_max_height - self.__room_display_height,
                                                       self.__room_view_top + 1)
                            self.__room_view_bottom = min(self.__room_max_height, self.__room_view_bottom + 1)
                        else:
                            self.__cursor_y = min(self.__room_display_top + self.__room_display_height - 1,
                                                  self.__cursor_y + 1)
                        self.__cursor_x = max(self.__room_display_left, self.__cursor_x - 1)

                if event.name.lower() == "n":  # down right
                    if keyboard.is_pressed("ctrl"):
                        self.__map_view.change_room("south", "east")
                    elif keyboard.is_pressed("shift"):
                        if self.__room_display_top + self.__room_display_height - 1 == self.__cursor_y \
                                and self.__room_view_bottom < self.__room_max_height:
                            self.__room_view_top = min(self.__room_max_height - self.__room_display_height,
                                                       self.__room_view_top + self.__shift_step)
                            self.__room_view_bottom = min(self.__room_max_height,
                                                          self.__room_view_bottom + self.__shift_step)
                        else:
                            self.__cursor_y = min(self.__room_display_top + self.__room_display_height - 1,
                                                  self.__cursor_y + self.__shift_step)
                        self.__cursor_x = min(self.__room_display_left + self.__room_display_width - 1,
                                              self.__cursor_x + self.__shift_step)
                    else:
                        if self.__room_display_top + self.__room_display_height - 1 == self.__cursor_y \
                                and self.__room_view_bottom < self.__room_max_height:
                            self.__room_view_top = min(self.__room_max_height - self.__room_display_height,
                                                       self.__room_view_top + 1)
                            self.__room_view_bottom = min(self.__room_max_height, self.__room_view_bottom + 1)
                        else:
                            self.__cursor_y = min(self.__room_display_top + self.__room_display_height - 1,
                                                  self.__cursor_y + 1)
                        self.__cursor_x = min(self.__room_display_left + self.__room_display_width - 1,
                                              self.__cursor_x + 1)
                # update position after moving the cursor
                self.__map_view.room_x = self.__cursor_x - self.__room_display_left + self.__room_view_left
                self.__map_view.room_y = self.__cursor_y - self.__room_display_top + self.__room_view_top

            if event.name == "tab":
                if len(self.__room_object_info) > 0:
                    self.__room_object_selected = (self.__room_object_selected + 1) % len(self.__room_object_info)

            if event.name == "enter" or event.name == "right":
                self.__map_view.nav_menu("enter")
            if event.name == "backspace" or event.name == "left":
                self.__map_view.nav_menu("back")
            if event.name == "down":
                self.__map_view.nav_menu("down")
            if event.name == "up":
                self.__map_view.nav_menu("up")
            # else:
            #     if event.name == "left":
            #         self.__cursor_x = max(0, self.__cursor_x - 1)
            #     if event.name == "right":
            #         self.__cursor_x = min(self.__screen_width - 1, self.__cursor_x + 1)
            #     if event.name == "up":
            #         self.__cursor_y = max(0, self.__cursor_y - 1)
            #     if event.name == "down":
            #         self.__cursor_y = min(self.__screen_height - 1, self.__cursor_y + 1)
            return
        elif self.__panel == "console":
            log_max_display_height = (self.__screen_height - 2) // 2
            log_len = len(self.__console_view.get_log())
            if event.name == "page up":
                if self.__log_index == -1:
                    self.__log_index = log_len - log_max_display_height if log_len > log_max_display_height else 0
                self.__log_index = max(0, self.__log_index - log_max_display_height)
            if event.name == "page down":
                if self.__log_index != -1:
                    self.__log_index = min(log_len - log_max_display_height, self.__log_index + log_max_display_height)
                    if self.__log_index >= log_len - log_max_display_height:
                        self.__log_index = -1
            if event.name == "r" and keyboard.is_pressed("ctrl"):
                self.__console_view.stop()
                self.__console_view = ConsoleView()
                self.__console_view.watch()
                return
            cmd_max_display_length = self.__screen_width - 2 - 1
            if event.name.lower() in "abcdefghijklmnopqrstuvwxyz0123456789-_=+!@#$%^&*()[]{}<>,.;:'\"\\/|?":
                self.__cmd = self.__cmd[0: self.__cmd_left + self.__cursor_pos] + event.name + \
                             self.__cmd[self.__cmd_left + self.__cursor_pos:]
                if len(self.__cmd) - self.__cmd_left > cmd_max_display_length:
                    self.__cmd_left += 1
                else:
                    self.__cursor_pos += 1
            if event.name.lower() == "insert" and keyboard.is_pressed("shift"):
                text = pyperclip.paste().replace("\n", "").replace("\r", "")
                self.__cmd = self.__cmd[0: self.__cmd_left + self.__cursor_pos] + text + \
                             self.__cmd[self.__cmd_left + self.__cursor_pos:]
                if len(self.__cmd) - self.__cmd_left > cmd_max_display_length:
                    self.__cmd_left += len(text)
                else:
                    self.__cursor_pos += len(text)
            if event.name == "space":
                self.__cmd = self.__cmd[0: self.__cmd_left + self.__cursor_pos] + " " + \
                             self.__cmd[self.__cmd_left + self.__cursor_pos:]
                self.__cursor_pos += 1
            if event.name == "backspace":
                if self.__cursor_pos > 0:
                    self.__cmd = self.__cmd[0: self.__cmd_left + self.__cursor_pos - 1] + \
                                 self.__cmd[self.__cmd_left + self.__cursor_pos:]
                    self.__cursor_pos -= 1
            if event.name == "delete":
                if self.__cmd_left + self.__cursor_pos < len(self.__cmd):
                    self.__cmd = self.__cmd[0: self.__cmd_left + self.__cursor_pos] + \
                                 self.__cmd[self.__cmd_left + self.__cursor_pos + 1:]
            if event.name == "left":
                if self.__cursor_pos > 0:
                    self.__cursor_pos -= 1
                else:
                    self.__cmd_left = max(0, self.__cmd_left - 1)
            if event.name == "right":
                if self.__cursor_pos < cmd_max_display_length:
                    self.__cursor_pos = min(self.__cursor_pos + 1, len(self.__cmd) - self.__cmd_left)
                else:
                    self.__cmd_left = min(self.__cmd_left + 1, len(self.__cmd) - cmd_max_display_length)
            if event.name == "home":
                self.__cursor_pos = 0
                self.__cmd_left = 0
            if event.name == "end":
                if len(self.__cmd) - self.__cmd_left > cmd_max_display_length:
                    self.__cmd_left = len(self.__cmd) - cmd_max_display_length
                self.__cursor_pos = len(self.__cmd) - self.__cmd_left
            if event.name == "enter":
                if self.__cmd != "":
                    self.__console_view.send_cmd(self.__cmd)
                    self.__cmd_history.append(self.__cmd)
                    if len(self.__cmd_history) > self.__cmd_history_max:
                        self.__cmd_history = self.__cmd_history[len(self.__cmd_history) - self.__cmd_history_max:]
                    self.__cmd_index = len(self.__cmd_history)
                    self.__cmd = ""
                    self.__cursor_pos = 0
            if event.name == "up":
                self.__cmd_index = max(-1, self.__cmd_index - 1)
                if -1 < self.__cmd_index < len(self.__cmd_history):
                    self.__cmd = self.__cmd_history[self.__cmd_index]
                else:
                    self.__cmd = ""
                self.__cursor_pos = len(self.__cmd)
            if event.name == "down":
                self.__cmd_index = min(len(self.__cmd_history), self.__cmd_index + 1)
                if -1 < self.__cmd_index < len(self.__cmd_history):
                    self.__cmd = self.__cmd_history[self.__cmd_index]
                else:
                    self.__cmd = ""
                self.__cursor_pos = len(self.__cmd)


class AutoPush(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        screeps_auto_push.DAEMON_MODE = True
        screeps_auto_push.main("log")

    @staticmethod
    def stop():
        screeps_auto_push.DAEMON_MODE = False


def sign_in():
    api = screeps_api.Api(config.SERVER_HOST, config.SERVER_PORT, config.USERNAME, config.PASSWORD)
    if "ok" not in api.get_time():
        return False
    if "ok" not in api.get_me():
        if api.check_username(config.USERNAME) == {u'error': u'User Exists'}:
            print("Invalid password.")
            return False
        else:
            print("Trying to sign up...")
            if "ok" not in api.set_username(config.USERNAME, config.PASSWORD):
                print("Failed.")
                return False
            else:
                print("Done.")
                if "ok" not in api.get_me():
                    return False
                # upload script and set active branch
                import screeps_auto_push
                screeps_auto_push.main()
                log(api.set_active_branch(config.BRANCH_NAME))
    return True


def log(*args):
    time_mark = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open("log", "a") as f:
        f.write(time_mark)
        for i, v in enumerate(args):
            if i > 0:
                f.write(" ")
            if type(v) in [bool, int, str, unicode]:
                f.write("{}".format(v))
            elif type(v) in [list, dict, tuple, map]:
                f.write("{}".format(json.dumps(v)))
            else:
                f.write("{} {}".format(type(v), v))
        f.write("\n")


def exception_hook(exc_type, exc_value, tb):
    msg = "Traceback (most recent call last):\n"
    while tb is not None:
        frame = tb.tb_frame
        line_no = tb.tb_lineno
        code = frame.f_code
        filename = code.co_filename
        name = code.co_name
        linecache.checkcache(filename)
        line = linecache.getline(filename, line_no, frame.f_globals)
        if line:
            line = line.strip()
        else:
            line = None
        msg += "\tFile \"{}\", line {}, in {}\n".format(filename, line_no, name)
        msg += "\t\t{}\n".format(line)
        tb = tb.tb_next
    msg += "{}: {}\n".format(exc_type.__name__, exc_value)
    log(msg)
    keyboard.unhook_all()


def clear_output():
    os.system("cls" if os.name == "nt" else "clear")


def flush_input():
    try:
        import msvcrt
        while msvcrt.kbhit():
            msvcrt.getch()
    except ImportError:
        import termios
        termios.tcflush(sys.stdin, termios.TCIOFLUSH)


def keyboard_event_test(x):
    clear_output()
    print(x.to_json(), keyboard.is_pressed("ctrl"), keyboard.is_pressed("shift"), keyboard.is_pressed("alt"))


if __name__ == "__main__":
    # keyboard.on_press(lambda event: keyboard_event_test(event))
    # while True:
    #     pass

    if sys.platform == "win32":
        os.system("title screeps-client")
        os.system("mode con: cols=120 lines=50")

    # pre start
    if not sign_in():
        if sys.version_info[0] > 2:
            input()
        else:
            raw_input()
        exit()
    clear_output()
    sys.excepthook = exception_hook

    # on start
    auto_push = AutoPush()
    auto_push.start()

    render = Render()
    render.start()

    # on stop
    auto_push.stop()
    auto_push.join()

    keyboard.unhook_all()
    flush_input()
    clear_output()
