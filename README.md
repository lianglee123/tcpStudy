- TCP如何保证可靠性?
可靠性是指保证接收者会有序的接收到发送的数据。

实现上，TCP把要发送的数据一次按次序编号(seq),
对于每个发送的seq, 都需要接收方明确的回应一个ACK。表示接收方已经接收到了。
另外接收方在组装数据时，也要按照seq的顺序组装。

TCP用序号对每个字节进行计数。序号是32bit的无符号数，序号到达232－1后又从0开始。


2.TCP的滑动窗口是什么？
发送方在发送数据时，可以同时发送一个窗口的所有数据，来增加发送速度。
窗口的大小是min(拥堵窗口(congestion window)大小，接收方通过ACK包回传的windSize)。

3. TCP的窗口通知机制是什么？有什么问题
为防止发送方过快，超出接收方的处理能力。所以接收方发送ACK数据包时，
会指定一个winSize, 来表示自己现在的接收缓存剩余大小。发送方不能同时发送大于winSize
的数据，这种接收方通知发送方winSize的机制叫做窗口通知)

但是，窗口通知在有些极端情况下会导致死锁问题。

例如：接收方接收到一个数据包后，发现自己的接收缓存已经满了，
于是在发送给发送方的ACK报文中设置winSize为0，发送方于是把自己的
winSize设置为0，不再发送。当应用程序读取了接收方的接收缓存，那么接收方又可以接收数据了，
但是接收方要等发送方给自己发送一个数据后，自己才能把最新的winSize设置在回应的ACK报文中。
所以接收方也进入等待，此时TCP处于死锁状态。

为了处理这种死锁，发送方需要主动发送一个窗口探查的包，去探查接收方当前的winSize。
窗口探查动作可以被一个坚持定时器触发。

3. 窗口探查的包要必须携带数据吗？
必须。窗口探查有两种做法
1.使用正常要发送的数据发送一个字节。
2.发送一个已经被确认的数据。
以上实现都符合RFC标准。这两种情况接收方都有义务回应ACK。
如果使用0字节的TCP ACK来探测winSize, 接收端时没有强制义务去回应的。

4.TCP能发送字节0的数据吗？
TCP的三次连接握手，TCP不含数据的ACK, TCP的四次连接断开。
这些报文都不含数据。可以视为字节为零的数据包。
https://www.zhihu.com/question/266624387

5. 你能描述ACK, SEQ Number的变化吗
经过握手，client和server已经各自协商出来一个
自己起始seqNumber。以seqNumber为起点，发送方给给每个seq编号，发送。
TCP Frame 里的数据SeqNumber指的是自己所带数据的第一个
接收方的ACK里的确认号，指明的期待的下一个seqNumber, 说明该seqNumber前的数据都已接收完毕。

6. TCP协议握手为什么要个随机一个数字并加一？
主要为了安全。否则黑客可以RST 不属于别人的TCP
https://www.zhihu.com/question/34400902
握手时为什么要选用把ACK设置为SYN + 1 https://blog.csdn.net/oldfish_C/article/details/105150516

ACK的含义是ack值前面的字节我都收到了，现在期望收到ack以及后面的字节。
SEQ的含义是当前数据包第一个字节的编号

https://www.cs.miami.edu/home/burt/learning/Csc524.032/notes/tcp_nutshell.html#:~:text=Sequence%20Numbers&text=The%20SYN%20packets%20consume%20one,the%20receiver%20expects%20to%20receive.

Sequence Numbers

All bytes in a TCP connection are numbered, beginning at a randomly chosen initial sequence number (ISN).
The SYN packets consume one sequence number, so actual data will begin at ISN+1.
The sequence number is the byte number of the first byte of data in the TCP packet sent (
also called a TCP segment).
The acknowledgement number is the sequence number of the next byte the receiver expects to receive.

The receiver ack'ing sequence number x acknowledges receipt of all data bytes less than (but not including) byte number x.

The sequence number is always valid.
The acknowledgement number is only valid when the ACK flag is one.
The only time the ACK flag is not set, that is,
the only time there is not a valid acknowledgement number in the TCP header, is during the first packet of connection set-up.

https://www.cs.miami.edu/home/burt/learning/Csc524.032/

7. TCP如何进行窗口协商？
在TCP报文的有16位的数据用来表示窗口大小，使用Tcp 选项还可以使用窗口Scale因子来加大窗口。
最大是2^16 * 2^14

8.TCP是怎么重传的?
有两种情况触发重传
1.ACK接收超时
2.发送方使用ACK触发了快速重传机制
https://blog.csdn.net/whgtheone/article/details/80983882
重传会触发拥塞控制机制
TCP采用的是累计确认机制

9.TCP如何确定滑动窗口的大小
swnd = min(rwnd, cwnd*mss)
腾讯技术对TCP 拥塞控制详解(https://zhuanlan.zhihu.com/p/144273871)


11.说下拥塞控制的机制
TCP的发送滑动窗口是min(receiveWindow, cwnd)
TCP是通过通知控制cwnd(congestion windows, 其单位位MSS)的变动,来进行拥塞控制的。
首先发送方会选择一个较小的cwnd初始值，还有一个ssthresh(slow start threshold)
刚开始每经过一次RTT(每经过一次ACK), cwnd就增长一倍，知道cwnd到达ssthresh时，开始每次只增长1,
当发送方判定线路发生拥堵时:例如超时未收到ACK, 重复收到ACK, sshthresh会降到cwnd/2
cwnd会降到一个较小的值(小于等于当前sshthresh), 然后重新开始刚刚的过程。

其中涉及到以下几个算法：
慢启动: cwnd从一个较小的值开始，先逐渐成倍增加，过了ssthresh后，每次只增加1
快速恢复：当探测到拥堵，cwnd会将到一个合理的值，而不是之间从0开始。比如说之间从ssthresh开始
快速重传：最简单的是超时重传，还有SACK机制等使其可以快速重传数据.SACk是接受方把自己现在缺的数据告诉发送方。

11. TCP收到还未发送的seq的ACK会怎么处理？
不再发送窗口内，应该直接丢弃。

12. TCP如何处理seq回环的问题
通过TCP option增加了一个timestamp机制，通过seq和timestamp共同判定是否发生了回环。
可以通过timestamp把seq扩展到了64位。

13. 在单个TCP连接上能达到的最大吞吐量是多少？
maxWindowSize/RTT
2**30 / RTT
所以假设RTT 10ms，那么最大吞吐量为100G/s

14. 如何处理Seq回绕的情况？
seq(2**32)发送4G数据就会回绕，如果回绕时间<MST,
那么第一遍发送的数据，就有可能在第二次时出现。
其实做法是使用使用TCP 的Timstame option来扩展seq
接收方将时间戳视为序列号的一个32 bit的扩展
时间戳每个时间窗口必须加1.

15. TCP如何确定自己的超时重传时间？
TCP需要不停的测量自己的RTT，
最简单一点RTO=2*RTT

16.描述TCP的握手和挥手过程及其状态变化
client：主动方
server: 被动方
1. client发送一个SYN包进入SYN_SEND状态)， 向server通过自己的seq初始值
2. server回应一个(SYN+ACK包), 进入SYN_RCVD状态，向client确认他的seq和通告自己的seq初始值。
3. client接收到SYN+ACK, 进入ESTABLISHED, 并向server发送ACK回应他的SYN
4. server收到ACK, 也进入ESTABLISHED
此时连接建立。可以开始发送数据。

1. client发送Fin包，进入FIN_WAIT_1的状态
2. server接收到Fin包，进入CLOSE_WAIT状态。发送ACK。
3. client接收到ACK, 进入到FIN_WAIT_2状态。此时client到server的发送链路已经宣告结束了。

4. server发送Fin包，进入LAST_ACK状态
5. client进入接收到该Fin, 进入TIME_WAIT状态，发送ACK
6. server接收到ACK, 关闭连接
7. client进入TIME_WAIT，等2*MSL(最大报文生存时间)后关闭

17. TCP为什么要三次握手四次挥手
全双工。红蓝通讯问题。

18. client 为什么要在TIME_WAIT状态等2*MSL才关闭》
 - client发送的ACK可能未被接收到所以他需要重传
 - 等待当前连接的所有报文都在网络上消失。防止对该连接的后续使用造成干扰。

19. 一台Linux能建立多少TCP连接？
看情况。一个TCP连接是由(srcIp, srcPort, dstIp, dstPort)确定的
1. TCP自身的限制
一台机器的srcIp一般只有一个，srcPort的范围是65536 = 2**16
假设Linux是server程序，外界的client来连接。dstIp-dstPort(假设为ipv4)的组合为2**32 * 2**16 * 2**16 = 2**64中

如果在Linux上允许client程序去连接特定的server, 那么就只能有65535个连接了，因为自身端口只有这么多。
但是client去连接不同的server是不是可以复用连接了？
一个连接对Linux来说是一个TCP连接是一个文件，Linux对最大可打开文件数有限制，需要设置。

20. 有自己抓过TCP的包吗？
抓过。Windows上的Wireshark, linux上用tcpdump。(没抓过的赶紧去试试)

21. 为什么说TCP是面向流的，UDP是面向报文的

22. TCP的粘包问题怎么解决
## 实践题
1. 假设有这样一个网络通道：
    - 每次只能传送1byte的数据包
    - 有可能丢包
    - 无时延
基于该网络实现一种点对点传送算法，该算法应该具有以下特性：
    - 数据保证有序传达

请参考tcp_v1.py

2. 假设有这样一个网络通道：
     - 每次只能传送1byte的数据包
     - 有可能丢包
     - 传送包时有随机的时延(在1ms~20ms之间)
基于该网络实现一种点对点传送算法，该算法应该具有以下特性：
       - 数据保证有序传达
       - 尽量不重复传送数据
       - 传送速度尽可能大
请参考tcp_v2.py: 无滑动窗口版
请参考tcp_v3.py: 有固定大小滑动窗口版

3. 假设有这样一个网络通道:
  - 每次只能传送1byte大小的数据包
  - 有可能丢包
  - 传送数据包时有随机的时延, 正常情况在1ms~5ms之间,但是当发送速率大过某个阈值后，
    其丢包概率和时延会急剧增加，并随时间推移逐渐恢复正常。
    该阈值是动态变化的，但是变动频率为1min
基于该网络实现一种点对点传送算法，该算法应该具有以下特性：
  - 数据保证有序传达
  - 尽量不重复传送数据
  - 传送速度尽量大
  - 尽量不导致网络性能下降
你是想让我增加拥塞控制功能吧？我很忙，没时间做。