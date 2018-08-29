
from lib.tcpClient import TcpClient
import tpUtils
import sys
from constant import *
import json
import time


class Tp14_out:
    """
    #14 Four-channel DAC
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """

        self.slot = slot
        self.comm = I2C
        self.host = host

        # アドレス
        self.i2c_addr = 0x60

    def start(self):
        """
        開始処理
        """

        self.tcp_client = TcpClient()
        self.tcp_client.connect_by_conf(self.host, self.slot, self.comm)

        # 初期化(0V)
        data = '[{"ch":1,"v":2048},{"ch":2,"v":2048},{"ch":3,"v":2048},{"ch":4,"v":2048}]'
        self.send(data)

    def send(self, msg):
        """
        データを送信します。
        """

        datas = json.loads(msg)

        for data in datas:

            # ch
            ch = None

            # channel select
            if data['ch'] == 1:
                ch = 0
            elif data['ch'] == 2:
                ch = 1
            elif data['ch'] == 3:
                ch = 2
            elif data['ch'] == 4:
                ch = 3
            else:
                raise ValueError('Tibbit #14 ch error!')

            dw = int(data['v'])

            # mvから変換例
            #dw = dw*100000
            #dw = dw+1000000000
            #v = round(dw/488281)
            v = dw

            if v > 4095:
                v = 4095
            if v < 0:
                v = 0

            tmp = 0x40+(ch % 4)*2
            tmp0 = int(0x90 + v / 256)
            tmp1 = v & 0x00FF

            send_data = []
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": tmp, "v": [tmp0, tmp1]})
            self.tcp_client.send(json.dumps(send_data))


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
        tp14_out = Tp14_out(slot, host)
        tp14_out.start()
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            tp14_out.send(data)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
