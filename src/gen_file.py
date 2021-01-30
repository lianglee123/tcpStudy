import sys


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
    with open("1W.txt", mode='w', encoding='utf8') as f:
        f.write("".join(data[:10000]))
    print("dataSize: %s " % len(data))

