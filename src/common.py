from typing import *

class PipeDst:
    def put(self, data):
        """
        This Method should Return Immediately, and should not raise any Exception
        """
        raise NotImplementedError("put not impl")


class Frame:

    def __init__(self, seq: int, data):
        """
        当Frame为ACK时,Seq表示期待的下一个Frame序列号,表示小于seq的Frame以及接收完毕
        Seq之所以要使用期待的下个序列号，而不是使用已确认的最后一个序列号，是因为后者语义不一致性。
        假设sender发的第一个包丢失了，那么Receiver该怎么发送ACK？可以发送seq的初始值-1，但是语义以及不统一了
        :param seq:
        :param data:
        """
        self.seq = seq
        self.data = data

    def __len__(self):
        return len(self.data)

    def __str__(self):
        return "Frame(seq=%s, data=%s)" % (self.seq, self.data)
