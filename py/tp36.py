import sys
from tp00 import Tp00
import tpUtils
from constant import *
import json
import time


class Tp36:
    """
    # 36 3-axis accelerometer
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """

        self.slot = slot
        self.comm = I2C
        self.host = host

        # アドレス
        self.i2c_addr = 0x53

        # tp00
        self.tp00 = Tp00(self.slot, self.comm, self.host)
        self.tp00.start()

        format = 0x00 | 0x08 | 0x0b

        send_data = []
        # set resolution + range
        send_data.append(
            {"act": "w", "add": self.i2c_addr, "cmd": 0x31, "v": [format]})
        # set measure bit
        send_data.append(
            {"act": "w", "add": self.i2c_addr, "cmd": 0x2d, "v": [0x08]})
        # set as bypass mode
        send_data.append(
            {"act": "w", "add": self.i2c_addr, "cmd": 0x38, "v": [0x80]})
        self.tp00.send(json.dumps(send_data))

    def get_data(self):
        """
        値を取得します。
        """

        # Lock
        self.tp00.lock(self.slot)
        try:
            # set measure bit
            send_data = []
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": 0x2d, "v": [0x08]})
            self.tp00.send(json.dumps(send_data))
            time.sleep(0.1)

            send_data = []
            send_data.append(
                {"act": "r", "add": self.i2c_addr, "cmd": 0x32, "len": 6})
            _result = self.tp00.send(json.dumps(send_data))

            result_data = json.loads(_result.decode())
            result_data = result_data[0]

            data0 = result_data[1]
            data1 = result_data[0]
            data2 = result_data[3]
            data3 = result_data[2]
            data4 = result_data[5]
            data5 = result_data[4]

            hi_byte = data0
            lo_byte = data1
            x = hi_byte*256+lo_byte

            hi_byte = data2
            lo_byte = data3
            y = hi_byte*256+lo_byte

            hi_byte = data4
            lo_byte = data5
            z = hi_byte*256+lo_byte

            send_data = []
            send_data.append(
                {"act": "r", "add": self.i2c_addr, "cmd": 0x2e, "len": 1})
            _result = self.tp00.send(json.dumps(send_data))

            result_data = json.loads(_result.decode())
            tmp = result_data[0][0]
            tmp = tmp & 0xFE

            send_data = []
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": 0x2e, "v": [tmp]})
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": 0x2d, "v": [0x00]})
            self.tp00.send(json.dumps(send_data))

        finally:
            # unLock
            self.tp00.unlock(self.slot)

        # 12G
        SIGN_MASK = 0xE000
        DATA_MASK = 0x1FFF

        x = x
        if (x & SIGN_MASK) != 0:
            x = x & DATA_MASK
            x_value = DATA_MASK-x
            x_value = (-x_value)
        else:
            x_value = x & DATA_MASK

        y = y
        if (y & SIGN_MASK) != 0:
            y = y & DATA_MASK
            y_value = DATA_MASK-y
            y_value = (-y_value)
        else:
            y_value = y & DATA_MASK

        z = z
        if (z & SIGN_MASK) != 0:
            z = z & DATA_MASK
            z_value = DATA_MASK-z
            z_value = (-z_value)
        else:
            z_value = z & DATA_MASK

        #'The scale is -4096 (-12G) to +4095 (+12G).
        # mGに変換
        x_value = (x_value*2930)/1000
        y_value = (y_value*2930)/1000
        z_value = (z_value*2930)/1000

        return {"x": x_value, "y": y_value, "z": z_value}


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
        tp36 = Tp36(slot, host)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            recv_data = tp36.get_data()
            tpUtils.nodeOut(json.dumps(recv_data))
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
            tpUtils.nodeOut("")
