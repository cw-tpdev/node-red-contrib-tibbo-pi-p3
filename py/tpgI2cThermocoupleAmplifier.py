import sys
from tp00 import Tp00
import tpUtils
from constant import *
import json
import time


class TpgI2cThermocoupleAmplifier:
    """
    TP Grove - I2C Thermocouple Amplifier
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

        self.tp00 = Tp00(self.slot, self.comm, self.host)
        self.tp00.start()

    def get_data(self):
        """
        値を取得します。
        """

        send_data = []
        send_data.append(
            {"act": "r", "add": self.i2c_addr, "cmd": 0x00, "len": 2})
        _result = self.tp00.send(json.dumps(send_data))
        result_data = json.loads(_result.decode())

        upper = result_data[0][0]
        lower = result_data[0][1]

        if (upper & 0x80) == 0x80:
            temp = (upper * 16 + lower / 16) - 4096.0
        else:
            temp = (upper * 16 + lower / 16)
        temp = round(temp, 2)

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
        tpgI2cThermocoupleAmplifier = TpgI2cThermocoupleAmplifier(slot, host)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            recv_data = tpgI2cThermocoupleAmplifier.get_data()
            tpUtils.nodeOut(recv_data)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
            tpUtils.nodeOut("")
