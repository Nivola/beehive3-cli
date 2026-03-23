#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


import os
import random
import time
import platform

snowflakes = {}

def get_terminal_size():
    def ioctl_gwinsz(fd):
        try:
            import fcntl
            import termios
            import struct

            cr = struct.unpack("hh", fcntl.ioctl(fd, termios.TIOCGWINSZ, "1234"))
        except:
            return None
        return cr

    cr = ioctl_gwinsz(0) or ioctl_gwinsz(1) or ioctl_gwinsz(2)

    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_gwinsz(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        try:
            cr = (os.environ["LINES"], os.environ["COLUMNS"])
        except:
            cr = (25, 80)
    return int(cr[1]), int(cr[0])


columns_merry, rows_merry = get_terminal_size()


def clear_screen():
    """Clear the console.
    numlines is an optional argument used only as a fall-back.
    """
    if os.name == "posix":
        # Unix/Linux/MacOS/BSD/etc
        os.system("clear")
    elif os.name in ("nt", "dos", "ce"):
        # DOS/Windows
        os.system("cls")
    else:
        # Fallback for other operating systems.
        print("\n" * rows_merry)


def get_random_flake(col):
    if not platform.system() == "Windows":
        try:
            flakes = "*NIVOLA"
            # print(flakes)
            i = col % len(flakes)
            # print(i)
            flake = flakes[i : i + 1]
            # flake = cmd(random.choice(range(0x2740, 0x2749)))

            return flake
        except:
            pass

    return " *"


def move_flake(col):
    if snowflakes[col][0] + 1 == rows_merry:
        snowflakes[col] = [1, get_random_flake(col)]
    else:
        print(f"\x1b[{snowflakes[col][0]};{col}H  ")

        snowflakes[col][0] += 1

        print(f"\x1b[{snowflakes[col][0]};{col}H{snowflakes[col][1]}")

        print("\033[1;1H")


# if __name__ == "__main__":
def merry():
    clear_screen()

    while True:
        col = random.choice(range(1, int(columns_merry)))

        # its already on the screen, move it
        if col in snowflakes:
            move_flake(col)
        else:
            # otherwise put it on the screen
            flake = get_random_flake(col)
            snowflakes[col] = [1, flake]

            print(f"\x1b[{snowflakes[col][0]};{col}H{snowflakes[col][1]}")

        # key any flakes on the screen moving
        for flake in snowflakes:
            move_flake(flake)

        time.sleep(0.1)
