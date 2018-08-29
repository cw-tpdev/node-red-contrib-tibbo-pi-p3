import sys
from tp00 import Tp00
import tpUtils
from constant import *
import json
import time


class Tp35:
    """
    #35 Barometric pressure sensor
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

        # tp00
        self.tp00 = Tp00(self.slot, self.comm, self.host)
        self.tp00.start()

    def __coefficient(self, msb, lsb, total_bits, fractional_bits, zero_pad):
        """
        coefficient
        """
        data = (msb << 8) | lsb
        period = float(1 << 16 - total_bits + fractional_bits + zero_pad)
        if (msb >> 7) == 0:
            result = float(data / period)
        else:
            result = -float(((data ^ 0xFFFF) + 1) / period)

        return result

    def get_data(self):
        """
        値を取得します。
        """

        # Lock
        self.tp00.lock(self.slot)
        try:
            send_data = []
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": 0x12, "v": [0x00]})
            self.tp00.send(json.dumps(send_data))
            time.sleep(0.003)

            send_data = []
            send_data.append(
                {"act": "r", "add": self.i2c_addr, "cmd": 0x00, "len": 12})
            _result = self.tp00.send(json.dumps(send_data))

        finally:
            # unLock
            self.tp00.unlock(self.slot)

        result_data = json.loads(_result.decode())
        data = result_data[0]

        a0 = self.__coefficient(data[4], data[5], 16, 3, 0)
        b1 = self.__coefficient(data[6], data[7], 16, 13, 0)
        b2 = self.__coefficient(data[8], data[9], 16, 14, 0)
        c12 = self.__coefficient(data[10], data[11], 14, 13, 9)

        padc = (data[0] << 8 | data[1]) >> 6
        tadc = (data[2] << 8 | data[3]) >> 6

        c12x2 = c12 * tadc
        a1 = b1 + c12x2
        a1x1 = a1 * padc
        y1 = a0 + a1x1
        a2x2 = b2 * tadc
        pcomp = y1 + a2x2

        pressure = (pcomp * 65 / 1023) + 50
        return round(pressure, 2)


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
        tp35 = Tp35(slot, host)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            recv_data = tp35.get_data()
            tpUtils.nodeOut(recv_data)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
            tpUtils.nodeOut("")
