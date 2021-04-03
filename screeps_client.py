
# —*- coding: utf-8 -*-

import copy
import curses
import json
import keyboard
import time

import screeps_api


def clear_output():
    import os
    os.system('cls' if os.name == 'nt' else 'clear')


def flush_input():
    try:
        import msvcrt
        while msvcrt.kbhit():
            msvcrt.getch()
    except ImportError:
        import sys
        import termios
        termios.tcflush(sys.stdin, termios.TCIOFLUSH)


def keyboard_event(x, sc):
    clear_output()
    print(x.to_json())
    if x.name == "c" and keyboard.is_pressed("ctrl"):
        sc.stop()


def room_callback(message):
    data = json.loads(message)[1]["objects"]
    for i in data:
        print i, data[i]


def main():
    socket = screeps_api.Socket()
    keyboard.on_press(lambda x: keyboard_event(x, socket))
    socket.subscribe("room", "W8N3")
    socket.callback = room_callback
    socket.start()
    socket.join()


def draw_menu(stdscr):
    k = 0
    cursor_x = 0
    cursor_y = 0

    # Clear and refresh the screen for a blank canvas
    stdscr.clear()
    stdscr.refresh()

    # Start colors in curses
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

    # Loop where k is the last character pressed
    while k != ord('q'):

        # Initialization
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        if k == curses.KEY_DOWN:
            cursor_y = cursor_y + 1
        elif k == curses.KEY_UP:
            cursor_y = cursor_y - 1
        elif k == curses.KEY_RIGHT:
            cursor_x = cursor_x + 1
        elif k == curses.KEY_LEFT:
            cursor_x = cursor_x - 1

        cursor_x = max(0, cursor_x)
        cursor_x = min(width-1, cursor_x)

        cursor_y = max(0, cursor_y)
        cursor_y = min(height-1, cursor_y)

        # Declaration of strings
        title = "Curses example"[:width-1]
        subtitle = "Written by Clay McLeod"[:width-1]
        keystr = "Last key pressed: {}".format(k)[:width-1]
        statusbarstr = "Press 'q' to exit | STATUS BAR | Pos: {}, {}".format(cursor_x, cursor_y)
        if k == 0:
            keystr = "No key press detected..."[:width-1]

        # Centering calculations
        start_x_title = int((width // 2) - (len(title) // 2) - len(title) % 2)
        start_x_subtitle = int((width // 2) - (len(subtitle) // 2) - len(subtitle) % 2)
        start_x_keystr = int((width // 2) - (len(keystr) // 2) - len(keystr) % 2)
        start_y = int((height // 2) - 2)

        # Rendering some text
        whstr = "Width: {}, Height: {}".format(width, height)
        stdscr.addstr(0, 0, whstr, curses.color_pair(1))

        # Render status bar
        stdscr.attron(curses.color_pair(3))
        stdscr.addstr(height-1, 0, statusbarstr)
        stdscr.addstr(height-1, len(statusbarstr), " " * (width - len(statusbarstr) - 1))
        stdscr.attroff(curses.color_pair(3))

        # Turning on attributes for title
        stdscr.attron(curses.color_pair(2))
        stdscr.attron(curses.A_BOLD)

        # Rendering title
        stdscr.addstr(start_y, start_x_title, title)

        # Turning off attributes for title
        stdscr.attroff(curses.color_pair(2))
        stdscr.attroff(curses.A_BOLD)

        # Print rest of text
        stdscr.addstr(start_y + 1, start_x_subtitle, subtitle)
        stdscr.addstr(start_y + 3, (width // 2) - 2, '-' * 4)
        stdscr.addstr(start_y + 5, start_x_keystr, keystr)
        stdscr.move(cursor_y, cursor_x)

        # Refresh the screen
        stdscr.refresh()

        # Wait for next input
        k = stdscr.getch()


class RoomView(object):

    def __init__(self):
        self.__room_matrix = [["." for _ in range(50)] for _ in range(50)]
        self.__room_name = "W8N3"
        self.__room_object = dict()

        self.__socket = screeps_api.Socket()

    def watch(self):
        self.__socket.subscribe("room", self.__room_name)
        self.__socket.callback = self.__room_callback
        self.__socket.start()

    def stop(self):
        self.__socket.stop()
        self.__socket.join()

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
        self.refresh()

    def refresh(self):
        self.__room_matrix = [["." for _ in range(50)] for _ in range(50)]
        api = screeps_api.Api()
        terrain_data = api.get_room_terrain(self.__room_name)["terrain"]
        for i in terrain_data:
            if i["type"] == "wall":
                self.__room_matrix[int(i["y"])][int(i["x"])] = "#"
            else:
                self.__room_matrix[int(i["y"])][int(i["x"])] = "?"
        for i, item in self.__room_object.items():
            char_map = {
                "source": "$",
                "mineral": "&",
                "creep": "@",
                "controller": "C",
                "spawn": "W",
                "tower": "T",
                "container": "N",
                "extension": "X",
                "storage": "R",
                "road": "o",
            }
            if item["room"] == self.__room_name:
                self.__room_matrix[int(item["y"])][int(item["x"])] = char_map[item["type"]] \
                    if item["type"] in char_map else "?"
        # for i in self.__room_matrix:
        #     log("".join(i))

    def get_matrix(self):
        return self.__room_matrix

    def get_info(self, x, y):
        info_list = list()
        for i, item in self.__room_object.items():
            if item["x"] == x and item["y"] == y:
                log(json.dumps(item))
                # info = {
                #     "_id": item["_id"],
                #     "type": item["type"],
                #     "x": item["x"],
                #     "y": item["y"],
                # }
                # if "hits" in item:
                #     info["hits"] = item["hits"]
                #     info["hitsMax"] = item["hitsMax"]
                # if "store" in item:
                #     info["store"] = item["store"]
                #     info["storeCapacityResource"] = item["storeCapacityResource"]
                # if "safeModeAvailable" in item:  # controller
                #     info["safeModeAvailable"] = item["safeModeAvailable"]
                #     info["safeModeCooldown"] = item["safeModeCooldown"]
                #     info["level"] = item["level"]
                #     info["progress"] = item["progress"]
                # if "mineralType" in item:  # mineral
                #     info["mineralType"] = item["mineralType"]
                info = copy.deepcopy(item)
                for key in ["meta", "$loki"]:
                    del info[key]
                info_list.append(info)
        return info_list


class Render(object):

    def __init__(self):
        self.__quit = False

        self.__screen_height = 0
        self.__screen_width = 0

        self.__cursor_x = 0
        self.__cursor_y = 0

        self.__room_display_left, self.__room_display_top = 3, 1
        self.__room_display_width, self.__room_display_height = 50, 30
        self.__room_max_width, self.__room_max_height = 50, 50
        self.__room_view = RoomView()
        self.__room_view_left, self.__room_view_right = 0, self.__room_display_width
        self.__room_view_top, self.__room_view_bottom = 0, self.__room_display_height
        self.__room_object_info = list()

        self.map_source = None

    def start(self):
        self.__room_view.watch()
        curses.wrapper(self.display)

    def display(self, screen):
        keyboard.on_press(lambda event: self.keyboard_handler(event))

        # Clear and refresh the screen for a blank canvas
        screen.clear()
        # screen.refresh()

        # Start colors in curses
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)

        while not self.__quit:
            # Initialization
            screen.clear()
            self.__screen_height, self.__screen_width = screen.getmaxyx()

            # TODO: Menu: [1]room panel, [2]log panel, [3]memory panel, [esc]Exit
            # TODO: room panel: room view, object view, info view
            # TODO: room panel: [h|j|k|l] to move in room view
            # TODO: room panel: [up|down] to switch between object
            # TODO: room panel: [page up|page down] to scroll info
            # TODO: log panel: log view with scrolling[page up|page down]
            # TODO: log panel: console command with history[up|down]

            # # Rendering some text
            # test = "Width: {}, Height: {}".format(self.__screen_width, self.__screen_height)
            # screen.addstr(5, 2, test, curses.color_pair(1))
            # test = "x: {}, y: {}".format(self.__cursor_x, self.__cursor_y)
            # screen.addstr(6, 2, test, curses.color_pair(1))

            # render room
            for y, line in enumerate(self.__room_view.get_matrix()[self.__room_view_top: self.__room_view_bottom]):
                screen.addstr(self.__room_display_top + y, self.__room_display_left,
                              "".join(line[self.__room_view_left: self.__room_view_right]), curses.color_pair(0))
            # TODO: render object list
            # TODO: render info
            if len(self.__room_object_info) > 0:
                log(json.dumps(self.__room_object_info, indent=4, sort_keys=True))
                info_list = json.dumps(self.__room_object_info, indent=4, sort_keys=True).splitlines()
                for y, line in enumerate(info_list[: self.__screen_height - 5]):
                    screen.addstr(1 + y, 60,
                                  line[:self.__screen_width - 60], curses.color_pair(0))

            screen.move(self.__cursor_y, self.__cursor_x)

            # Refresh the screen
            screen.refresh()

        self.__room_view.stop()

    def keyboard_handler(self, event):
        clear_output()
        log(event.name)
        if event.name == "esc":
            self.__quit = True
        if self.__cursor_x in range(self.__room_display_left,
                                    self.__room_display_left + self.__room_display_width) \
                and self.__cursor_y in range(self.__room_display_top,
                                             self.__room_display_top + self.__room_display_height):
            if event.name == "left":
                self.__cursor_x = max(0, self.__cursor_x - 1)
                # if self.__cursor_x - 3 < 5:
                #     self.__room_view_left = max(0, self.__room_view_left - 1)
                #     self.__room_view_right = max(30, self.__room_view_right - 1)
            if event.name == "right":
                self.__cursor_x = min(self.__screen_width - 1, self.__cursor_x + 1)
                # if 33 - self.__cursor_x < 5:
                #     self.__room_view_left = min(20, self.__room_view_left + 1)
                #     self.__room_view_right = min(50, self.__room_view_right + 1)
            if event.name == "up":
                if self.__room_display_top == self.__cursor_y \
                        and self.__room_view_top > 0:
                    self.__room_view_top = max(0, self.__room_view_top - 1)
                    self.__room_view_bottom = max(self.__room_display_height, self.__room_view_bottom - 1)
                else:
                    self.__cursor_y = max(0, self.__cursor_y - 1)
            if event.name == "down":
                if self.__room_display_top + self.__room_display_height - 1 == self.__cursor_y \
                        and self.__room_view_bottom < self.__room_max_height:
                    self.__room_view_top = min(self.__room_max_height - self.__room_display_height,
                                               self.__room_view_top + 1)
                    self.__room_view_bottom = min(self.__room_max_height, self.__room_view_bottom + 1)
                else:
                    self.__cursor_y = min(self.__screen_height - 1, self.__cursor_y + 1)

            self.__room_object_info = self.__room_view.get_info(
                    self.__cursor_x - self.__room_display_left + self.__room_view_left,
                    self.__cursor_y - self.__room_display_top + self.__room_view_top)
        else:
            if event.name == "left":
                self.__cursor_x = max(0, self.__cursor_x - 1)
            if event.name == "right":
                self.__cursor_x = min(self.__screen_width - 1, self.__cursor_x + 1)
            if event.name == "up":
                self.__cursor_y = max(0, self.__cursor_y - 1)
            if event.name == "down":
                self.__cursor_y = min(self.__screen_height - 1, self.__cursor_y + 1)


def log(line, filename="log"):
    with open(filename, "a") as f:
        f.write(line + "\n")


def keyboard_event_test(x):
    clear_output()
    print(x.to_json())


if __name__ == "__main__":
    # main()

    # curses.wrapper(draw_menu)

    # keyboard.on_press(lambda event: keyboard_event_test(event))
    # while True:
    #     pass

    render = Render()
    render.start()

    keyboard.unhook_all()
    flush_input()


