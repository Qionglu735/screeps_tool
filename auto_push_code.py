
# -*- coding: utf-8 -*-

import datetime
import difflib
import json
import os
import requests
import time
import sys

from config import *




DAEMON_MODE = False


class Color:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    NORMAL = "\033[0m"
    BOLD = "\033[1m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    REVERSE = "\033[7m"


def main():
    local_modules = read_file(BRANCH_NAME)
    token = requests.post("http://{}:{}/api/auth/signin".format(SERVER_HOST, SERVER_PORT),
                          json={
                              "email": USERNAME,
                              "password": PASSWORD
                          }).json()["token"]
    server_modules = requests.get("http://{}:{}/api/user/code".format(SERVER_HOST, SERVER_PORT),
                                  headers={
                                      "X-Token": token,
                                      "X-Username": token
                                  }).json()["modules"]
    diff_module("modules", server_modules, local_modules)
    if server_modules == local_modules:
        print("Everything updated.")
    else:
        if DAEMON_MODE:
            confirm = "yes"
        else:
            confirm = raw_input("Push to \"{}\"? [yes/no]".format(BRANCH_NAME))
        if confirm.lower() == "yes":
            print("Pushing...")
            res = requests.post("http://{}:{}/api/user/code".format(SERVER_HOST, SERVER_PORT),
                                headers={
                                    "X-Token": token,
                                    "X-Username": token
                                }, json={
                                    "branch": BRANCH_NAME,
                                    "modules": local_modules,
                                }).json()
            if res["ok"] == 1:
                print("Done.")
            else:
                print("Failed.")
        else:
            print("Aborted.")


def read_file(path):
    modules = dict()
    root, dirs, files = next(os.walk(path))
    # print(root, dirs, files)
    for _file in files:
        if not _file.endswith(".js"):
            continue
        filename = _file.rstrip(".js")
        with open(os.path.join(root, _file)) as f:
            data = f.read()
            modules[filename] = data.decode("utf-8")
    for _dir in dirs:
        modules[_dir] = read_file(os.path.join(root, _dir))
    return modules


def diff_module(key, server_module, local_module):
    if server_module == local_module:
        pass
    elif type(server_module) == unicode and type(local_module) == unicode:
        if local_module == server_module.replace("\r", ""):
            pass
        else:
            print("=== module: {}".format(key + ".js"))
            differ = difflib.Differ()
            diff_res = list(differ.compare(server_module.splitlines(), local_module.replace("\r", "").splitlines()))

            line_num = 0
            last_printed_index = -1
            lines_before, lines_after = [], []
            for _index, i in enumerate(diff_res):
                if i[0] in [" ", "+"]:
                    line_num += 1
                if i[0] != " ":
                    if 0 <= last_printed_index < _index - 7:
                        print("   {} |   {}".format(Color.CYAN + "..." + Color.NORMAL,
                                                   Color.CYAN + "... ..." + Color.NORMAL))
                    while len(lines_before) > 0:
                        if i[0] == "-":
                            line_num += 1
                        print("{:>6} | {}".format(line_num - (len(lines_before)), lines_before[0]))
                        if i[0] == "-":
                            line_num -= 1
                        lines_before.pop(0)
                    if i[0] in ["+"]:
                        print("{:>6} | {}".format(line_num, Color.GREEN + i.replace("\n", "") + Color.NORMAL))
                    elif i[0] in ["-"]:
                        print("       | {}".format(Color.RED + i.replace("\n", "") + Color.NORMAL))
                    elif i[0] in ["?"]:
                        print("       | {}".format(Color.YELLOW + i.replace("\n", "") + Color.NORMAL))
                    else:
                        print("       | {}".format(i.replace("\n", "")))
                    last_printed_index = _index
                else:
                    if 0 <= last_printed_index and _index - 3 <= last_printed_index:
                        print("{:>6} | {}".format(line_num, i.replace("\n", "")))
                    else:
                        while len(lines_before) >= 3:
                            lines_before.pop(0)
                        lines_before.append(i)
                        # print("{:>6} | {}".format(line_num, i.replace("\n", "")))
            print("")
    elif type(server_module) == unicode:
        print("--- module(file): {}".format(key))
        print("+++ module(dir): {}".format(key))
    elif type(local_module) == unicode:
        print("--- module(dir): {}".format(key))
        print("+++ module(file): {}".format(key))
    else:
        server_key_list = server_module.keys()
        local_key_list = local_module.keys()
        for i in set(server_key_list).difference(set(local_key_list)):
            print("--- module: {}".format(i))
        for i in set(local_key_list).difference(set(server_key_list)):
            print("+++ module: {}".format(i))
        for i in set(server_key_list).intersection(set(local_key_list)):
            diff_module(i, server_module[i], local_module[i])


if __name__ == "__main__":
    for arg in sys.argv:
        if arg in ["-d", "--daemon"]:
            DAEMON_MODE = True

    now = datetime.datetime.now()
    main()
    if DAEMON_MODE:
        print("Start watching \"{}\"...".format(BRANCH_NAME))
    while DAEMON_MODE:
        break_flag = False
        for root, dirs, files in os.walk(BRANCH_NAME):
            for f in files:
                modify_time = datetime.datetime.fromtimestamp(os.stat(os.path.join(root, f)).st_mtime)
                if modify_time > now:
                    now = datetime.datetime.now()
                    # print(os.path.join(root, f), modify_time)
                    main()
                    break_flag = True
                    break
            if break_flag:
                break
        time.sleep(1)
