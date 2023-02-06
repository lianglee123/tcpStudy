以题促学，其乐无穷。
## 理论篇
### 1. TCP如何保证可靠性?
可靠性是指保证接收者会有序的无丢失的接收到发送的数据。

实现上，TCP把要发送的数据按次序编号(seq),
对于每个发送的seq, 都需要接收方明确的回应一个ACK。表示接收方已经接收到了。
另外接收方在组装数据时，也要按照seq的顺序组装。

TCP用32bit的无符号数对要发送的数据编号，序号到达2^32－1后又从0开始。

### 2.TCP的滑动窗口是什么？
发送方在发送数据时，可以同时发送一个窗口的所有数据，来增加发送速度。

窗口的大小是 拥塞窗口大小、接收方接收窗口大小中的最小值。

### 3. TCP的窗口通知机制是什么？有什么问题
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
窗口探查动作可以被一个定时器触发,该定时器称为坚持定时器。

### 4. 窗口探查的包要必须携带数据吗？
必须。窗口探查有两种做法
1. 使用正常要发送的数据发送一个字节。
2. 发送一个已经被确认的数据。
以上实现都符合RFC标准。这两种情况接收方都有义务回应ACK。
如果使用0字节的TCP ACK来探测winSize, 接收端时没有强制义务去回应的。
参见[知乎车小胖的回答](https://www.zhihu.com/question/266624387)
### 5.TCP能发送字节0的数据吗？
TCP的三次连接握手，TCP不含数据的ACK, TCP的四次连接断开。
这些报文都不含数据。可以视为字节为零的数据包。
参见[知乎车小胖的回答](https://www.zhihu.com/question/266624387)
### 6. 你能描述ACK, SEQ Number的变化吗
经过握手，client和server已经各自协商出来一个
自己起始seqNumber。以seqNumber为起点，发送方给给每个seq编号，发送。
TCP Frame 里的数据SeqNumber指的是自己所带数据的第一个
接收方的ACK里的确认号，指明的期待的下一个seqNumber, 说明该seqNumber前的数据都已接收完毕。

### 7. TCP协议握手为什么要个随机一个数字并加一？
主要为了安全。否则黑客可以RST 别人的TCP连接。
参见[知乎车小胖的回答](https://www.zhihu.com/question/34400902)
### 8. ACK的值和SEQ的值的含义是什么？
ACK的值含义是ack值前面的字节我都收到了，现在期望收到ack以及后面的字节。
SEQ的值含义是当前数据包第一个字节的编号。
更详细的请参考：
https://www.cs.miami.edu/home/burt/learning/Csc524.032/
### 9. TCP如何进行窗口协商？
在TCP报文的有16位的数据用来表示窗口大小，使用Tcp 选项还可以使用窗口Scale因子来加大窗口。最大是2^16 * 2^14
### 10.TCP是怎么重传的?
有两种情况触发重传
1.ACK接收超时
2.发送方使用ACK触发了快速重传机制
https://blog.csdn.net/whgtheone/article/details/80983882
### 11.TCP如何确定滑动窗口的大小
swnd = min(rwnd, cwnd*mss)
rwnd为协商出的接收方的接收窗口的大小。
cwnd为拥塞控制窗口的大小，但是其单位MSS(最大分段大小)
rwnd是为了防止 [发送方] 的数据填满 [接收方] 的缓存，但是并不知道网络中发生了什么。
在网络出现拥堵时，如果继续发生大量数据包，可能会导致数据包时延，丢失等，这时TCP就会重传，
一重传加重网络负担，于是更多包延迟或者丢包，形成恶性循环。
拥塞控制就是用来避免[发送方] 的数据填满整个网络。
为了在[发送方]调节要发送数据的量，定义了一个叫做 拥塞窗口(congest window)的概念。
参考：https://blog.csdn.net/weixin_50911232/article/details/126911476

### 12.说下TCP拥塞控制的机制
TCP的发送端滑动窗口是min(receiveWindow, cwnd)
TCP是通过通知控制cwnd(congestion windows, 其单位为MSS)的变动,来进行拥塞控制的。
首先发送方会选择一个较小的cwnd初始值，还有一个ssthresh(slow start threshold)
刚开始每经过一次RTT(每经过一次ACK), cwnd就增长一倍，知道cwnd到达ssthresh时，开始每次只增长1,
当发送方判定线路发生拥堵时:例如超时未收到ACK, 重复收到ACK, sshthresh会降到cwnd/2
cwnd会降到一个较小的值(小于等于当前sshthresh), 然后重新开始刚刚的过程。

其中涉及到以下几个算法：
慢启动: cwnd从一个较小的值开始，先逐渐成倍增加，过了ssthresh后，每次只增加1
快速恢复：当探测到拥堵，cwnd会将到一个合理的值，而不是从0开始。比如说之间从ssthresh开始
快速重传：最简单的是超时重传，还有SACK机制等使其可以快速重传数据.SACk是接受方把自己现在缺的数据告诉发送方。
腾讯技术对TCP 拥塞控制详解(https://zhuanlan.zhihu.com/p/144273871)
### 13. TCP收到还未发送的seq的ACK会怎么处理？
不再发送窗口内，应该直接丢弃。
### 14. TCP如何处理seq回环的问题
因为seq的最大取值范围为0~2**32, 所以发送4G数据就会回绕，如果回绕时间<MST,
那么有可能第一次使用seq发送的数据在第二次使用的该seq再次出现，造成干扰。
其实做法是使用使用TCP 的Timstame option来扩展seq
接收方将时间戳视为序列号的一个32 bit的扩展
时间戳每个时间窗口必须加1.

通过TCP option增加了一个timestamp机制，通过seq和timestamp共同判定是否发生了回环。
可以通过timestamp把seq扩展到了64位。
### 15. 在单个TCP连接上能达到的最大吞吐量是多少？
maxWindowSize/RTT
2**30 / RTT
所以假设RTT 10ms，那么最大吞吐量为100G/s

### 16. TCP如何确定自己的超时重传时间？
TCP需要不停的测量自己的RTT，
最简单一点RTO=2*RTT
### 17.描述TCP的握手和挥手过程及其状态变化
client：主动方
server: 被动方
1. client发送一个SYN包进入SYN_SEND状态)， 向server通过自己的seq初始值
2. server回应一个(SYN+ACK包), 进入SYN_RCVD状态，向client确认他的seq和通告自己的seq初始值。
3. client接收到SYN+ACK, 进入ESTABLISHED, 并向server发送ACK回应他的SYN
4. server收到ACK, 也进入ESTABLISHED

此时连接建立。可以开始发送数据。

关闭时：
1. client发送Fin包，进入FIN_WAIT_1的状态
2. server接收到Fin包，进入CLOSE_WAIT状态。发送ACK。
3. client接收到ACK, 进入到FIN_WAIT_2状态。此时client到server的发送链路已经宣告结束了。
4. server发送Fin包，进入LAST_ACK状态
5. client进入接收到该Fin, 进入TIME_WAIT状态，发送ACK
6. server接收到ACK, 关闭连接
7. client进入TIME_WAIT，等2*MSL(最大报文生存时间)后关闭

### 18. TCP为什么要三次握手四次挥手
全双工。
红蓝通讯问题：建立连接时双方都需要知道自己的话对方能听得见。所以需要三次握手。
关闭时，两个方向的信道要分别关闭。所以需要四次挥手。

### 19. 为什么主动关闭连接的一方要在TIME_WAIT状态等2*MSL才关闭》
 - client发送的ACK可能未被接收到所以他需要重传
 - 等待当前连接的所有报文都在网络上消失。防止对该连接的后续使用造成干扰。

### 20. 一台Linux能建立多少TCP连接？
看情况。
一个TCP连接是由(srcIp, srcPort, dstIp, dstPort)确定的
一台机器的srcIp一般只有一个，srcPort的范围是65536 = 2^16
假设Linux是server程序，外界的client来连接。dstIp-dstPort(假设为ipv4)的组合为2^32 * 2^16 * 2^16 = 2^64种
如果在Linux上让client程序去连接特定的server地址, 那么就只能有65535个连接了，因为自身端口只有这么多。

另外，一个连接对Linux来说是一个TCP连接是一个文件，Linux对最大可打开文件数有限制，需要设置。

### 21. 有自己抓过TCP的包吗？
抓过。Windows上的Wireshark, linux上用tcpdump。(没抓过的赶紧去试试)
### 22. 为什么说TCP是面向流的，UDP是面向报文的
TCP依次发送小报文，在接收方接收的到这几个报文按顺序连接在一起。
UDP你发送一个特定大小的数据包，接收到时还是这个包。
TCP你发送的数据可能会被拆分为多个包，或者合并为一个包。对使用者来说是流式的。
### 23. TCP的粘包问题怎么解决？
怂包回答法：粘包是指发送方发送了数据包，接收方接收的数据是多个数据包首尾相接，无法按发送时的样子进行切割。这个问题需要应用层去做。比如应用层在发送数据段的首部加入数据长度、使用特殊的字符表示一段数据结束等。
正直的杠精回答法：单TCP是流协议，不存在在粘包问题。
所谓的粘包就是指发送方发送的若干包数据到达接收方时粘成了一包，这是TCP协议允许的。所以必须在应用层找方法解决。

### 24. Nagle算法和Delay-Ack算法分别是什么，他们一起使用有什么问题？
Nagle是优化发送方发送较小数据包的算法，他的精髓在于：靠链路RTT来动态调整发包速率。
Nagle算法讲的最好的[文章](https://mp.weixin.qq.com/s?__biz=MzIxODU5MDYwNg==&mid=2247483731&idx=1&sn=e7edde77fad4bcb459c6a84e7ba401ba&chksm=97e97db2a09ef4a4665b8cfb3edd590f793c43d5f4253989a5257ebadc6acc7c931dbe2e899e#rd)
Delay-Ack是接受方收到数据后，暂时不发ACK，当有多个ACK要发时，可以合并这些ACK一起发送。
当Nagle和Delay-Ack搭配使用时，有可能存在发送方等待接收方的ACK, 接收方等待更多的数据一起发送ACK。
直到Delayed-ACK超时后，发送回来ACK。才开始重新发送。

## 实践题
### 1. 假设有这样一个网络通道：
  - 每次只能传送1byte的数据包
  - 有可能丢包
  - 无时延

基于该网络实现一种点对点传送算法，该算法应该具有以下特性：
  - 数据保证有序传达

请参考[src/tcp_v1.py](./src/tcp_v1.py)
### 2. 假设有这样一个网络通道：
  - 每次只能传送1byte的数据包
  - 有可能丢包
  - 传送包时有随机的时延(在1ms~20ms之间)

基于该网络实现一种点对点传送算法，该算法应该具有以下特性：
  - 数据保证有序传达
  - 尽量不重复传送数据
  - 传送速度尽可能大

请参考[src/tcp_v2.py](./src/tcp_v2.py): 无滑动窗口版

请参考[src/tcp_v3.py](./src/tcp_v3.py): 有固定大小滑动窗口版

### 3. 假设有这样一个网络通道:
  - 每次只能传送1byte大小的数据包
  - 有可能丢包
  - 传送数据包时有随机的时延, 正常情况在1ms~5ms之间,但是当发送速率大过某个阈值后,其丢包概率和时延会急剧增加，并随时间推移逐渐恢复正常。该阈值是动态变化的，但是变动频率为1min

基于该网络实现一种点对点传送算法，该算法应该具有以下特性：
  - 数据保证有序传达
  - 尽量不重复传送数据
  - 传送速度尽量大
  - 尽量不导致网络性能下降

你是想让我增加拥塞控制功能吧？我挺忙，没时间做，你自己做吧。
