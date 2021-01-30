"""
参考TCP的原理，使用python完成以下任务：

2. 假设有这样一个网络通道：
    - 每次只能传送1byte的数据包
    - 有可能丢包
    - 传送包时有随机的时延(在1ms~20ms之间)
基于该网络实现一种点对点传送算法，该算法应该具有以下特性：
    - 数据保证有序传达
    - 尽量不重复传送数据
    - 传送速度尽可能大

"""
from typing import *
import time
import random
from common import PipeDst, Frame
from threading import Lock, Thread
import _thread

import queue

def log(*args):
    print(*args)
    pass


def curMillSecond():
    return time.time() * 1000


class Pipe:
    """
2. 假设有这样一个网络通道：
    - 每次只能传送1byte的数据包
    - 有可能丢包
    - 传送包时有随机的时延(在10ms~20ms之间)
    """
    def __init__(self, sendPercent: float, minDelay=1, maxDelay=20):
        self.sendPercent = sendPercent
        self.minDelay = minDelay
        self.maxDelay = maxDelay
        self.q = queue.Queue(100000)
        _thread.start_new(self.run, ())

    def send(self, dst: PipeDst, frame):
        assert len(frame) <= 10, "data is not larger byte"
        if self.sendPercent >= 1:
            self.q.put((self.randomSendTime(), dst, frame))
        else:
            if random.random() > self.sendPercent:
                log("\tpipe---> discard put ", frame, " to ", dst)
                return
            else:
                self.q.put((self.randomSendTime(), dst, frame))

    def randomSendTime(self):
        millSec = self.minDelay + random.random() * (self.maxDelay - self.minDelay)
        return curMillSecond() + millSec

    def run(self):
        while True:
            self.checkSend()
            time.sleep(0.005)

    def checkSend(self):
        # log("check", list(self.q.queue))
        nowMill = curMillSecond()
        l = self.q.qsize()
        for i in range(l):
            v = self.q.get(block=False)
            if v is not None:
                t, d, f = v
                if t <= nowMill:
                    log("\tpipe--->real put ", f, " to ", d)
                    d.put(f)
                else:
                    self.q.put((t, d, f))



class Sender(PipeDst):
    """
    发一个，确认一个。
    正常情况：
    1. 发送数据，50ms之内， 对应的ACK到达
    异常情况：
    1. 发送数据，经过50ms后， 对应的ACK未到达, 可能原因
       - 无ACK:
        Pipe丢弃了数据-->重发
        Pipe丢弃了ACK-->重发
    2. 发送数据，在50ms的时间之内，有对应的ACK未到达,但是ACK不是期望的ACK
       可能原因:
           - 以前的ACK现在才到达

    """
    def __init__(self, pipe, receiver):
        self.pipe = pipe
        self.receiver = receiver
        self.count = 0
        self.ackQueue = queue.Queue(20)

    def __str__(self):
        return "Sender"
    def __repr__(self):
        return self.__str__()

    def send(self, data: str):
        l = len(data)
        i = 0
        while i < l:
            # log("i: ", i)
            self.count += 1
            fra = Frame(seq=i, data = data[i])
            log("S: send ", fra)
            self.pipe.send(self.receiver, fra)

            st = curMillSecond()
            ack = None
            while curMillSecond() - st < 50:
                ack = self.get(True, 10)
                # log("sender get ack ", ack)
                if ack is None or ack.seq != i:
                    ack = None
                    continue
                else:
                    break

            if ack is None: # 超时未收到期望的ACK, 重新发送
                log("S: Wait ACK Timeout")
                continue
            log("S: get ACK", ack)

            i += 1 # 发送下一个

    def get(self, block=False, timeout=None):
        if timeout:
            sec = timeout / 1000
        try:
            return self.ackQueue.get(block=block, timeout=sec)
        except Exception:
            return None

    def put(self, frame):
        try:
            self.ackQueue.put(frame, block=False)
        except Exception:
            pass


class Receiver(PipeDst):
    """
    收到一条期望的seq数据，就发送一条ACK
    收到重复数据，要分情况分析:
    假设数据1,2,3,4已经确认过了，现在又收到了数据包1/2/3,
    那么不应该重新发送ACK, 因为这种情况的可能原因：
       - 这些数据在线路中停留时间过长，发送方导致已经重发.

    假设1,2,3,4已经确认过了，现在期望5，但是还是重复收到4的数据包，
    那么，应该重复发送对4的数据包，因为这种情况，可能接收方没有接收到ACK
    """
    def __init__(self, pipe, sender):
        self.data = []
        self.cache = {}
        self.sender = sender
        self.pipe = pipe
        self.locker = Lock()

    def getAll(self):
        return "".join(self.data)


    def put(self, frame):
        # ACK 中Seq的含义是该<=seq的数据已经确认收到
        expectSeq = len(self.data)
        # log("frame: ", frame)
        if frame.seq == expectSeq:
            log("R: 收到期待数据，", frame)
            self.data.append(frame.data)
            self.pipe.send(self.sender, Frame(frame.seq, "ACK"))  # seq
        elif frame.seq < expectSeq: # 接收到重复数据，且该重复数据为收到的最后一个数据，那么就重复发送ACK
            if frame.seq == expectSeq - 1:
                log("R: 收到上一个重复数据:", frame, expectSeq)
                self.pipe.send(self.sender, Frame(frame.seq, "ACK"))
            log("R: 收到重复数据:", frame, expectSeq)
        else: # 收到大于期待的，直接抛弃，什么都不做，现阶段不可能出现大于期待的seq
            raise ValueError("frame seq(%s) > expect(%s)" % (frame.seq, expectSeq))

    def __str__(self):
        return "Receiver"

    def __repr__(self):
        return self.__str__()


def send(srcfile, dstFile):
    pipe = Pipe(0.8)
    receiver = Receiver(pipe, None)
    sender = Sender(pipe, receiver)

    receiver.sender = sender
    with open(srcfile, encoding="utf8") as f:
        data = f.read()
    print("dataSize: %s " % len(data))
    st = time.time()
    sender.send(data)
    print("send spend: %.2f seonds" % (time.time()-st))
    if len(data) != 0:
        print("sender counter: %s, dst/sender: %s" % (sender.count, (sender.count/float(len(data)))))
    receiverData = receiver.getAll()
    with open(dstFile, mode='w', encoding="utf8") as f:
        f.write(receiverData)


def fileSame(file1, file2):
    with open(file1, mode="rb") as f:
        data1 = f.read()
    with open(file2, mode='rb') as f:
        data2 = f.read()
    return data1 == data2


def trans(sourceFile, dstFile):
    send(sourceFile, dstFile)
    if not fileSame(sourceFile, dstFile):
        raise Exception("send data not equal!")
    log("send ok!")


if __name__ == '__main__':
    # 因为有丢包概率，所以而且一个数据包的完整传送需要两次传送(一次数据，一次ACK),
    # 在不丢包的情况下, 平均延迟为10ms的情况下，理论发送时长为 0.01*len(data)*2
    # 测试结果基本符合这个理论值.
    # 丢包概率为p, 则概率发送次数为1/(1-p)*len(data),
    # 理论发送时长：1/(1-p)*len(data), 但是这是不准确的，因为Send设置重复传送超时时间的缘故。
    # 总是就是，每发一个就等待ACK的方法，速度太慢，完全取决于丢包率和信道延迟（主要是信道延迟)
    # 对大容量高延迟的信道非常不公平。请看2.0有窗口版的实现
    # 假设RTT为10ms, TCP的发送速率为：windowsSize*(1/0.01)
    # 按照这个公式阿里云内网的单个TCP最大传送速度其实为（43690 << 7)/1024/1024 = 5.33Mb
    # 难道这就是TCP的上限？满心疑惑
    # 因为TCP的WindowsSize是静态的？所以到底是不是真的。
    # (注意在思考时，带宽是影响RTT的因素，所以我们不用直接思考带宽，只用思考RTT就行)
    trans("data.txt", "data.2.txt")
    # trans("tale-of-two-cities.txt", "tale-of-two-cities.2.txt")

