import sys
from tp00 import Tp00
import tpUtils
from constant import *
import json


class Tp29:
    """
    #29 Ambient temperature meter
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """

        self.slot = slot
        self.comm = I2C
        self.host = host

        # アドレス
        self.i2c_addr = 0x18

        # tp00
        self.tp00 = Tp00(self.slot, self.comm, self.host)
        self.tp00.start()

    def get_data(self):
        """
        値を取得します。
        """
        send_data = []
        send_data.append(
            {"act": "r", "add": self.i2c_addr, "cmd": 0x05, "len": 2})
        _result = self.tp00.send(json.dumps(send_data))

        # jsonで受け取る
        result_data = json.loads(_result.decode())
        result = result_data[0]

        # 値の取得
        val = (result[0] & 0x0F) * 16 + result[1] / 16

        if result[0] & 0x10 != 0:
            # マイナス
            temp = round(256 - val, 1)
        else:
            # プラス
            temp = round(val, 1)

        return temp


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
        tp29 = Tp29(slot, host)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            recv_data = tp29.get_data()
            tpUtils.nodeOut(recv_data)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
            tpUtils.nodeOut("")
