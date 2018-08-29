from datetime import datetime

from lib.tcpClient import TcpClient
import tpUtils
import sys
import json
from constant import *


class Tp42:
    """
    #42 RTC and NVRAM with backup
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """
        self.slot = slot
        self.comm = SPI
        self.host = host

    def start(self):
        """
        開始処理
        """
        self.tcp_client = TcpClient()
        self.tcp_client.connect_by_conf(self.host, self.slot, self.comm)

    def send(self, msg):
        """
        データを送信します。
        """
        recv_data = self.tcp_client.send(msg)
        return recv_data

    def get_data(self):
        """
        日付を取得
        """

        send_data = []

        READ = 0x00
        vals = [0] * 7
        send_data.append({"add": READ, "v": vals})

        recv = self.send(json.dumps(send_data))
        return self.__convert(recv)

    def __convert(self, msg):
        """
        日付に変換
        """

        buff = json.loads(msg.decode())

        # 年
        year = 2000 + tpUtils.bcd_to_dec(buff[0][6])
        # 月
        month = tpUtils.bcd_to_dec(buff[0][5])
        # 日
        day = tpUtils.bcd_to_dec(buff[0][4])
        # 時
        hour = tpUtils.bcd_to_dec(buff[0][2])
        # 分
        minute = tpUtils.bcd_to_dec(buff[0][1])
        # 秒
        sec = tpUtils.bcd_to_dec(buff[0][0])

        dt = datetime(year, month, day, hour, minute, sec)
        return dt.strftime("%Y/%m/%d %H:%M:%S")

    def send_data(self, msg):
        """
        日付をセット
        """

        # check
        try:
            datetime.strptime(msg, '%Y/%m/%d %H:%M:%S')
        except ValueError:
            raise ValueError(
                "Incorrect data format, should be yyyy-MM-dd HH:mm:ss - " + msg)

        send_data = []

        vals = []
        # 秒
        vals.append(tpUtils.dec_to_bcd(int(msg[17:19])))
        # 分
        vals.append(tpUtils.dec_to_bcd(int(msg[14:16])))
        # 時
        vals.append(tpUtils.dec_to_bcd(int(msg[11:13])))

        WRITE = 0x80
        send_data.append({"add": WRITE, "v": vals})

        vals = []
        # 日
        vals.append(tpUtils.dec_to_bcd(int(msg[8:10])))
        # 月
        vals.append(tpUtils.dec_to_bcd(int(msg[5:7])))
        # 年
        vals.append(tpUtils.dec_to_bcd(int(msg[2:4])))

        WRITE = 0x84
        send_data.append({"add": WRITE, "v": vals})

        # send
        self.send(json.dumps(send_data))

        # SET
        return "SET: " + msg


if __name__ == '__main__':

    argvs = sys.argv
    if (len(argvs) <= 1):
        tpUtils.stderr('Need argv! [1]: slot')
        sys.exit(0)

    try:
        slot = argvs[1]
        host = None
        if (len(argvs) > 2):
            host = argvs[2]
        tp42 = Tp42(slot, host)
        tp42.start()
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            tmp = json.loads(data)
            if (tpUtils.to_num(tmp['ctrl']) == 1):
                recv = tp42.get_data()
            elif (tpUtils.to_num(tmp['ctrl']) == 2):
                recv = tp42.send_data(tmp['v'])
            else:
                raise ValueError("Incorrect data")
            tpUtils.nodeOut(recv)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
            tpUtils.nodeOut("")
