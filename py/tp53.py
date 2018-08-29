
from lib.tcpClient import TcpClient
import tpUtils
import sys
from constant import *
import json
import time


class Tp53:
    """
    #53 Isolated 4-20mA ADC
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """

        self.slot = slot
        self.comm = I2C
        self.host = host

        # アドレス
        self.i2c_addr = 0x48

    def start(self):
        """
        開始処理
        """
        self.tcp_client = TcpClient()
        self.tcp_client.connect_by_conf(self.host, self.slot, self.comm)

        # cmd書き込み
        send_data = []
        send_data.append(
            {"act": "r", "add": self.i2c_addr, "cmd": 0x0C, "len": 3})
        self.__send(json.dumps(send_data))

    def __send(self, msg):
        """
        データを送信します。
        """

        recv_data = self.tcp_client.send(msg)
        return recv_data

    def get_data(self, msg):
        """
        値を取得します。
        """

        # 前回の変換結果を取得
        send_data = []
        send_data.append(
            {"act": "r", "add": self.i2c_addr, "len": 2})
        _result = self.__send(json.dumps(send_data))
        result_data = json.loads(_result.decode())

        byte_hi = result_data[0][0]
        byte_lo = result_data[0][1]

        val = byte_hi * 256 + byte_lo

        # LSB_V = 0.000152587890625 # 5 V / 32768
        # mA_On_V = 0.0032 # (20 mA - 4 mA) / 5000 mV

        # # 電圧(V)への変換例
        # if val <= 0x7FFF:
        #     rtn_v = val * LSB_V
        # else:
        #     rtn_v = 0xFFFF - val + 1
        #     rtn_v = -(rtn_v * LSB_V)
        # print(rtn_v)

        # if rtn_v < -0.6:
        #     return

        # # 電流(A)への変換例
        # rtn_a = rtn_v * mA_On_V
        # rtn_a = rtn_a + 0.004
        # print(rtn_a)

        return val


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
        tp53 = Tp53(slot, host)
        tp53.start()
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            recv_data = tp53.get_data(data)
            tpUtils.nodeOut(recv_data)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
            tpUtils.nodeOut("")
