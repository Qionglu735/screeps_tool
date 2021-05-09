
# -*- coding: utf-8 -*-

from __future__ import print_function

import datetime
import difflib
import os
import time
import sys

import config
import screeps_api


DAEMON_MODE = False
LOG_FILE = None


class Color(object):
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


def push():
    api = screeps_api.Api(config.SERVER_HOST, config.SERVER_PORT, config.USERNAME, config.PASSWORD)
    server_branch_object = api.get_all_code()
    server_branch_list = list()
    if "list" in server_branch_object:
        server_branch_list = [_["branch"] for _ in server_branch_object["list"]]
    if config.BRANCH_NAME not in server_branch_list:
        print("{} not existed. Try to create a new branch...".format(config.BRANCH_NAME), file=LOG_FILE)
        res = api.clone_branch(server_branch_list[0], config.BRANCH_NAME)
        if "ok" in res and res["ok"] == 1:
            print("{} Created.".format(config.BRANCH_NAME))
        else:
            print("{} Creation Failed.".format(config.BRANCH_NAME))
            return

    local_modules = read_file(os.path.join(config.SCRIPT_PATH, config.BRANCH_NAME))
    # token = requests.post("http://{}:{}/api/auth/signin".format(SERVER_HOST, SERVER_PORT),
    #                       json={
    #                           "email": USERNAME,
    #                           "password": PASSWORD
    #                       }).json()["token"]
    # server_modules = requests.get("http://{}:{}/api/user/code".format(SERVER_HOST, SERVER_PORT),
    #                               headers={
    #                                   "X-Token": token,
    #                                   "X-Username": token
    #                               }).json()["modules"]
    server_modules = api.get_code(branch=config.BRANCH_NAME)["modules"]
    diff_module("modules", server_modules, local_modules)
    if server_modules == local_modules:
        print("Everything updated.", file=LOG_FILE)
        return True
    else:
        if DAEMON_MODE:
            confirm = "yes"
        else:
            if sys.version_info[0] > 2:
                confirm = input("Push to \"{}\"? [yes/no]".format(config.BRANCH_NAME))
            else:
                confirm = raw_input("Push to \"{}\"? [yes/no]".format(config.BRANCH_NAME))
        if confirm.lower() == "yes":
            print("Pushing...", file=LOG_FILE)
            # res = requests.post("http://{}:{}/api/user/code".format(SERVER_HOST, SERVER_PORT),
            #                     headers={
            #                         "X-Token": token,
            #                         "X-Username": token
            #                     }, json={
            #                         "branch": BRANCH_NAME,
            #                         "modules": local_modules,
            #                     }).json()
            res = api.post_code(local_modules, config.BRANCH_NAME)
            if "ok" in res and res["ok"] == 1:
                print("Done.", file=LOG_FILE)
                return True
            else:
                print(res, file=LOG_FILE)
                print("Failed.", file=LOG_FILE)
                return False
        else:
            print("Aborted.", file=LOG_FILE)
            return False


def read_file(path):
    modules = dict()
    root, dirs, files = next(os.walk(path))
    # print(root, dirs, files, file=LOG_FILE)
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
            print("=== module: {}".format(key + ".js"), file=LOG_FILE)
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
                                                    Color.CYAN + "... ..." + Color.NORMAL), file=LOG_FILE)
                    while len(lines_before) > 0:
                        if i[0] == "-":
                            line_num += 1
                        print("{:>6} | {}".format(line_num - (len(lines_before)), lines_before[0]), file=LOG_FILE)
                        if i[0] == "-":
                            line_num -= 1
                        lines_before.pop(0)
                    if i[0] in ["+"]:
                        print("{:>6} | {}".format(line_num,
                                                  Color.GREEN + i.replace("\n", "") + Color.NORMAL), file=LOG_FILE)
                    elif i[0] in ["-"]:
                        print("       | {}".format(Color.RED + i.replace("\n", "") + Color.NORMAL), file=LOG_FILE)
                    elif i[0] in ["?"]:
                        print("       | {}".format(Color.YELLOW + i.replace("\n", "") + Color.NORMAL), file=LOG_FILE)
                    else:
                        print("       | {}".format(i.replace("\n", "")), file=LOG_FILE)
                    last_printed_index = _index
                else:
                    if 0 <= last_printed_index and _index - 3 <= last_printed_index:
                        print("{:>6} | {}".format(line_num, i.replace("\n", "")), file=LOG_FILE)
                    else:
                        while len(lines_before) >= 3:
                            lines_before.pop(0)
                        lines_before.append(i)
                        # print("{:>6} | {}".format(line_num, i.replace("\n", "")), file=LOG_FILE)
            print("", file=LOG_FILE)
    elif type(server_module) == unicode:
        print("--- module(file): {}".format(key), file=LOG_FILE)
        print("+++ module(dir): {}".format(key), file=LOG_FILE)
    elif type(local_module) == unicode:
        print("--- module(dir): {}".format(key), file=LOG_FILE)
        print("+++ module(file): {}".format(key), file=LOG_FILE)
    else:
        server_key_list = server_module.keys()
        local_key_list = local_module.keys()
        for i in set(server_key_list).difference(set(local_key_list)):
            print("--- module: {}".format(i), file=LOG_FILE)
        for i in set(local_key_list).difference(set(server_key_list)):
            print("+++ module: {}".format(i), file=LOG_FILE)
        for i in set(server_key_list).intersection(set(local_key_list)):
            diff_module(i, server_module[i], local_module[i])


def main(log_file=None):
    global DAEMON_MODE
    global LOG_FILE
    # TODO: stop print color if using log file

    now = datetime.datetime.now()
    if log_file is not None:
        LOG_FILE = open(log_file, "a")
    push_res = push()
    if log_file is not None:
        LOG_FILE.flush()
        LOG_FILE.close()

    if push_res and DAEMON_MODE:
        if log_file is not None:
            LOG_FILE = open(log_file, "a")
        print("Start watching \"{}\"...".format(config.BRANCH_NAME), file=LOG_FILE)
        if log_file is not None:
            LOG_FILE.flush()
            LOG_FILE.close()
    while push_res and DAEMON_MODE:
        time.sleep(1)
        break_flag = False
        for root, dirs, files in os.walk(os.path.join(config.SCRIPT_PATH, config.BRANCH_NAME)):
            for f in files:
                modify_time = datetime.datetime.fromtimestamp(os.stat(os.path.join(root, f)).st_mtime)
                if modify_time > now:
                    now = datetime.datetime.now()
                    if log_file is not None:
                        LOG_FILE = open(log_file, "a")
                    print("Modify detected @ {}".format(modify_time.strftime("%Y-%m-%d %H:%M:%S")), file=LOG_FILE)
                    push_res = push()
                    if log_file is not None:
                        LOG_FILE.flush()
                        LOG_FILE.close()
                    break_flag = True
                    break
            if break_flag:
                break


if __name__ == "__main__":
    for arg in sys.argv:
        if arg in ["-d", "--daemon"]:
            DAEMON_MODE = True
    main("log")
