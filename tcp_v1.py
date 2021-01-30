"""
参考TCP的原理，使用python完成以下任务：

1. 假设有这样一个网络通道：
    - 每次只能传送1byte的数据包
    - 有可能丢包
    - 无时延
基于该网络实现一种点对点传送算法，该算法应该具有以下特性：
    - 数据保证有序传达

直接使用SEND-ACK机制即可.连编号也不用，因为根本没有时延
发送方发送一个包，如果接收不到接收方回应，就重新发送。

"""
from typing import *
import time
import random


from common import PipeDst, Frame

def log(*args):
    print(*args)


class Pipe:
    """
    这里搞错了，send函数不应该直接返回true/false表示是否丢包
    是否丢包的检测需要sender/receiver自己检测
    """
    def __init__(self, sendPercent: float):
        self.sendPercent = sendPercent

    def send(self, dst, data: str):
        if len(data) >= 20:
            raise ValueError("send data is larger than 20")
        if self.sendPercent >= 1:
            dst.put(data)
        else:
            if random.random() > self.sendPercent:
                return
            else:
                dst.put(data)


class Sender(PipeDst):

    def __init__(self, pipe, receiver):
        self.pipe = pipe
        self.receiver = receiver
        self.count = 0
        self.ack = None

    def send(self, data: str):
        l = len(data)
        i = 0
        while i < l:
            self.count += 1
            seg = Frame(seq=i, data = data[i])
            self.pipe.send(self.receiver, seg)
            while self.ack is None or self.ack.seq != i:
                if self.ack is None:  # 未收到ACK, 重发该数据
                    seg = Frame(seq=i, data=data[i])
                else: # 收到的ACK.seq小于当前i, 就从按照ACK的期望开始
                    i = self.ack.seq
                    if i >= l:
                        return
                    seg = Frame(seq=i, data=data[i])
                self.ack = None
                self.pipe.send(self.receiver, seg)
                self.count += 1
            self.ack = None
            i += 1

    def put(self, frame):
        self.ack = frame


class Receiver(PipeDst):
    def __init__(self, pipe, sender):
        self.data = []
        self.cache = {}
        self.sender = sender
        self.pipe = pipe

    def getAll(self):
        return "".join(self.data)


    def put(self, frame):
        expectSeq = len(self.data)
        if frame.seq == expectSeq:
            self.data.append(frame.data)
            self.pipe.send(self.sender, Frame(len(self.data), ""))
        elif frame.seq < expectSeq: # 接收到重复数据，那么就重复发送ACK
            self.pipe.send(self.sender, Frame(expectSeq, ""))
        else: # 收到大于期待的，直接抛弃，什么都不做，现阶段不可能出现大于期待的seq
            raise ValueError("frame seq > expect")


def send(srcfile, dstFile):
    pipe = Pipe(0.8)
    receiver = Receiver(pipe, None)
    sender = Sender(pipe, receiver)
    receiver.sender = sender
    with open(srcfile, encoding="utf8") as f:
        data = f.read()
    log("dataSize: %s " % len(data))
    st = time.time()
    sender.send(data)
    log("send spend: %.2f seonds" % (time.time()-st))
    log("sender counter: %s, dst/sender: %s" % (sender.count, (sender.count/float(len(data)))))
    receiverData = receiver.getAll()
    with open(dstFile, mode='w', encoding="utf8") as f:
        f.write(receiverData)


def fileSame(file1, file2):
    with open(file1, mode="rb") as f:
        data1 = f.read()
    with open(file2, mode='rb') as f:
        data2 = f.read()
    return data1 == data2


def run():
    send("tale-of-two-cities.txt", "tale-of-two-cities.2.txt")
    if not fileSame("tale-of-two-cities.txt", "tale-of-two-cities.2.txt"):
        raise Exception("send data not equal!")
    log("send ok!")


if __name__ == '__main__':
    run()

