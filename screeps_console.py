
# —*- coding: utf-8 -*-

import json

import config
import screeps_api


def console_callback(message):
    data = json.loads(message)[1]["messages"]
    log = data["log"]
    for i in log:
        print(i)
    result = data["results"]
    if len(result) > 0:
        for i in result:
            print("> {}".format(i))


def main():
    sc = screeps_api.Socket(config.SERVER_HOST, config.SERVER_PORT, config.USERNAME, config.PASSWORD)
    sc.subscribe("user", "console")
    sc.callback = console_callback
    # sc.set_debug(True)
    sc.start()
    sc.join()


if __name__ == "__main__":
    main()
