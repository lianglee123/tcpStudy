from typing import *

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


基于tcp_2, 我要在Sender端实现一个固定大小的滑动窗口,大小为100。
如果，只更改Sender, 那么Sender第一次发送100个frame

Receiver端，暂时依然是收到一个ack就发送一个ack
    - 问题1：当seq无序到达时,他会将其抛弃，并发送自己所期望的ack, 那么，Sender应该如何处理这个ACK?

所以干脆一步到位：Receiver和Sender同时拥有一个大小相同的窗口

那么Sender在什么情况下应该重发呢？
  1. 一个frame超时没有收到ack
  2. 
Sender应该重发哪些数据？

Receiver应该如何回应Sender, ?


下一步：
Receiver可以暂时缓存那些无序到达的数据
"""
from typing import *
import time
import random
from common import PipeDst, Frame
from threading import Lock, Thread
import _thread

import queue


def curMillSecond():
    return time.time() * 1000


def log(*args):
    print(*args)
    pass


class Pipe:
    """
2. 假设有这样一个网络通道：
    - 每次只能传送1byte的数据包
    - 有可能丢包
    - 传送包时有随机的时延(在1ms~20ms之间)
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
            time.sleep(0.001)

    def checkSend(self):
        # print("check", list(self.q.queue))
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

    WindowSize的大小为100
    发送数据，可以连续发送100个frame, 然后等待ack的到达，seq=50的ack到达，那么可以再发送50个
    总是一直有50的frame被发送在pipe上，等待ack
    如果50ms内没有等到滑动窗口内的任何ack, 那么从头开始重发

    如果Sender加入和windows, 但是Receiver不加Windows, 那么传送速度变快了，代价是sender传送的总的
    数据量=windowSize * len(data)

    另外，滑动之后，不是立即的重发窗口的所有数据，而是发送窗口所有未发数据,并等待窗口内第一个fram的超时时间
    每次要发送的数据为，窗口扩展出来的部分(oldRight, newRight], 超时时间，暂且都为静态的。
    """
    def __init__(self, pipe, receiver, winSize=100):
        self.pipe = pipe
        self.receiver = receiver
        self.count = 0
        self.ackQueue = queue.Queue(20)
        self.wSize = winSize
        self.reSendDuration = 50
        self.leftStepAverage = 0
        self.leftStepSum = 0
        self.rightStepAverage = 0
        self.rightStepSum = 0
        self.sliceCnt = 0

    def __str__(self):
        return "Sender"

    def __repr__(self):
        return self.__str__()

    def send(self, data: str):
        # [left, right]之间为需要发送的数据
        left = 0
        right = min(left + self.wSize - 1, len(data)-1)
        oldRight = -1
        while left < len(data):
            # 发送整个窗口
            sendIndex = oldRight + 1
            while sendIndex <= right:
                fra = Frame(seq=sendIndex, data = data[sendIndex])
                self.pipe.send(self.receiver, fra)
                sendIndex += 1
                self.count += 1
            log("S: window: [%s,%s %s] send over" % (left, oldRight+1, right))
            # 等待ACK
            st = curMillSecond()
            ack = None
            while curMillSecond() - st < self.reSendDuration:
                ack = self.get(True, 5)
                # print("sender get ack ", ack)
                if ack is None or not (left <= ack.seq <= right):
                    ack = None
                    continue
                else:
                    break

            if ack is None: # 超时未收到期望的ACK, 重新发送整个窗口
                log("S: Wait ACK Timeout")
                oldRight = left - 1
                continue
            elif left <= ack.seq <= right:
                oldLeft = left
                oldRight = right
                left = ack.seq + 1
                right = min(left + self.wSize - 1, len(data)-1)
                self.leftStepSum += (left - oldLeft)
                self.rightStepSum += (right - oldRight)
                self.sliceCnt += 1
                log("S: get valid Ack, %s slide windows, [%s, %s] ==> [%s, %s], step: %s" %
                    (ack, oldLeft, oldRight, left, right, left-oldLeft))
            elif ack.seq < left:
                log("S: 收到重复ACK, 丢弃")
            else:
                raise ValueError("S: Invalid Ack: %s" % ack)

    def get(self, block=False, timeout=None):
        if timeout:
            sec = timeout / 1000
        else:
            sec = None
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

    现在发力点要让Sender的窗口一次多滑动几步

    可以做的事：缓存收到的Frame, 每次都发送最大的ACK而不是为每个Frame都发送

    """
    def __init__(self, pipe, sender, winSize=3):
        self.data = []
        self.cache = {}
        self.sender = sender
        self.pipe = pipe
        self.locker = Lock()
        self.winSize = winSize
        self.expectSeq = 0

    def getAll(self):
        return "".join(self.data)


    def put(self, frame):
        # ACK 中Seq的含义是该<=seq的数据已经确认收到
        # print("frame: ", frame)
        if frame.seq == self.expectSeq:
            log("R: 收到期待数据，", frame)
            if self.expectSeq < len(self.data):
                self.data[self.expectSeq] = frame.data
            else:
                self.data.append(frame.data)
            oldExpectSeq = self.expectSeq
            while self.expectSeq < len(self.data):
                if self.data[self.expectSeq] is not None:
                    self.expectSeq += 1
                else:
                    break
            log("R: expectSeq change %s --> %s" % (oldExpectSeq, self.expectSeq))
            self.pipe.send(self.sender, Frame(self.expectSeq-1, "ACK"))
        elif frame.seq < self.expectSeq: # 接收到重复数据，且该重复数据为收到的最后一个数据，那么就重复发送ACK
            if frame.seq == self.expectSeq - 1:
                log("R: 收到上一个重复数据:", frame, self.expectSeq)
                self.pipe.send(self.sender, Frame(frame.seq, "ACK"))
            log("R: 收到已有的重复数据, do nothing", frame, self.expectSeq)
        else: # 现在有可能收到大于期望的了
            # raise ValueError("frame seq(%s) > expect(%s)" % (frame.seq, expectSeq))
            log("R: 收到seq过大数据， 缓存, len(data) %s, frame.seq: %s" % (len(self.data), frame.seq))
            if len(self.data) <= frame.seq: # 填充空位
                self.data.extend([None for _ in range(len(self.data), frame.seq+1)])
                self.data[frame.seq] = frame.data
                # log("R: 填充后：", self.data)
                self.pipe.send(self.sender, Frame(self.expectSeq-1, "ACK"))
            else:
                if self.data[frame.seq] is not None:
                    log("R: 收到重复数据，丢弃 %s, oldData: %s", frame, self.data[frame.seq])
                else:
                    self.data[frame.seq] = frame.data
                    log("R: 收到乱序数据，缓存, %s", frame)


    def __repr__(self):
        return  "Receiver"


def send(srcfile, dstFile):
    pipe = Pipe(1)
    winSize = 10000
    receiver = Receiver(pipe, None, winSize=winSize)
    sender = Sender(pipe, receiver, winSize=winSize)

    receiver.sender = sender
    with open(srcfile, encoding="utf8") as f:
        data = f.read()
    print("dataSize: %s " % len(data))
    st = time.time()
    sender.send(data)
    print("send spend: %.2f seonds" % (time.time()-st))
    if len(data) != 0:
        print("sender counter: %s, senderCount/len(data): %s" % (sender.count, (sender.count/float(len(data)))))
    receiverData = receiver.getAll()
    with open(dstFile, mode='w', encoding="utf8") as f:
        f.write(receiverData)
    print("left step average: leftStepSum/sliceCnt: %s/%s = %s" % (sender.leftStepSum, sender.sliceCnt,
                                                                   sender.leftStepSum/sender.sliceCnt))
    print("right step average: rightStepSum/sliceCnt: %s/%s = %s" % (sender.rightStepSum, sender.sliceCnt,
                                                                   sender.rightStepSum/sender.sliceCnt))


def fileSame(file1, file2):
    with open(file1, mode="rb") as f:
        data1 = f.read()
    with open(file2, mode='rb') as f:
        data2 = f.read()
    return data1 == data2


def run(sourceFile, dstFile):
    send(sourceFile, dstFile)
    if not fileSame(sourceFile, dstFile):
        raise Exception("send data not equal!")
    print("send ok!")


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
    # run("data.txt", "data.2.txt")
    # run("hello.txt", "hello.2.txt")
    run("tale-of-two-cities.txt", "tale-of-two-cities.2.txt")

