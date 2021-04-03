
# —*- coding: utf-8 -*-

import json
import keyboard

import screeps_api


def clear_output():
    import os
    os.system('cls' if os.name == 'nt' else 'clear')


def keyboard_event(x, sc):
    clear_output()
    if x.name == "c" and keyboard.is_pressed("ctrl"):
        sc.stop()


def console_callback(message):
    data = json.loads(message)[1]["messages"]
    log = data["log"]
    for i in log:
        print i
    result = data["results"]
    if len(result) > 0:
        for i in result:
            print "> {}".format(i)


def flush_input():
    try:
        import msvcrt
        while msvcrt.kbhit():
            msvcrt.getch()
    except ImportError:
        import sys
        import termios
        termios.tcflush(sys.stdin, termios.TCIOFLUSH)


def main():
    sc = screeps_api.Socket()
    keyboard.on_press(lambda x: keyboard_event(x, sc))
    sc.subscribe("user", "console")
    sc.callback = console_callback
    # sc.set_debug(True)
    sc.start()
    sc.join()
    keyboard.unhook_all()
    flush_input()


if __name__ == "__main__":
    main()








