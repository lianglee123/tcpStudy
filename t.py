from typing import *


def run():
    a = [0, 1, 2, 3]
    seq = 8
    a.extend([None for i in range(len(a), 8)])
    print(a)
    a.append(seq)
    print(a, len(a))


if __name__ == '__main__':
    with open("tale-of-two-cities.txt", encoding="utf8") as f:
        data = f.read()
    print("dataSize: %s " % len(data))

