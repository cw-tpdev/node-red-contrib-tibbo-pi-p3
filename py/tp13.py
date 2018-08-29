
from lib.tcpClient import TcpClient
import tpUtils
import sys
from constant import *
import json
import time


class Tp13:
    """
    #13 Four-channel ADC
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """

        self.slot = slot
        self.comm = I2C
        self.host = host

        # アドレス
        self.i2c_addr = 0x08

    def start(self):
        """
        開始処理
        """
        self.tcp_client = TcpClient()
        self.tcp_client.connect_by_conf(self.host, self.slot, self.comm)

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

        # 戻り値配列
        rtn = []

        datas = json.loads(msg)

        for data in datas:

            # ch
            ch = None

            # channel select
            if data['ch'] == 1:
                ch = 0x88
            elif data['ch'] == 2:
                ch = 0x98
            elif data['ch'] == 3:
                ch = 0xA8
            elif data['ch'] == 4:
                ch = 0xB8
            else:
                raise ValueError('Tibbit #13 ch error!')

            send_data = []
            # 前回の値が取得できるため、1個目は読み捨てる
            send_data.append(
                {"act": "r", "add": self.i2c_addr, "cmd": ch, "len": 2})
            # 取得する値
            send_data.append(
                {"act": "r", "add": self.i2c_addr, "cmd": ch, "len": 2})
            _result = self.__send(json.dumps(send_data))
            result_data = json.loads(_result.decode())

            # 1個目は不要
            byte_hi = result_data[1][0]
            byte_lo = result_data[1][1]
            val = byte_lo/16 + byte_hi*16

            # mvへの変換例
            #val = (val*488281-1000000000)/100000
            #val = int(val)

            rtn.append(val)

        return rtn


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
        tp13 = Tp13(slot, host)
        tp13.start()
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            recv_data = tp13.get_data(data)
            tpUtils.nodeOut(json.dumps(recv_data))
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
            tpUtils.nodeOut("")
