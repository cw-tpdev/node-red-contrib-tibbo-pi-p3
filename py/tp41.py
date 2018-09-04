import sys
from tp00 import Tp00
import tpUtils
from constant import *
import json
import time


class Tp41:
    """
    #41 8-bit port (supplied with 200mm cable)
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """

        self.slot = slot
        self.comm = I2C
        self.host = host

        # アドレス
        self.i2c_addr = 0x20

        # tp00
        self.tp00 = Tp00(self.slot, self.comm, self.host)
        self.tp00.start()

        # ピンの設定
        send_data = []
        send_data.append(
            {"act": "w", "add": self.i2c_addr, "cmd": 0x00, "v": [0xFF]})
        send_data.append(
            {"act": "r", "add": self.i2c_addr, "cmd": 0x00, "len": 1})
        send_data.append(
            {"act": "w", "add": self.i2c_addr, "cmd": 0x01, "v": [0x0]})
        send_data.append(
            {"act": "r", "add": self.i2c_addr, "cmd": 0x01, "len": 1})
        self.tp00.send(json.dumps(send_data))

        # 初期化
        send_data = []
        for i in range(0, 8):
            cmd = 0x02 + i
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": cmd, "v": [0x00]})
        self.tp00.send(json.dumps(send_data))

    def __bit_access(self, data, bit, act):
        """
        bit access
        """

        if bit == 7:
            if act == 0:
                return data | 0x80
            else:
                return data & 0x7F
        elif bit == 6:
            if act == 0:
                return data | 0x40
            else:
                return data & 0xBF
        elif bit == 5:
            if act == 0:
                return data | 0x20
            else:
                return data & 0xDF
        elif bit == 4:
            if act == 0:
                return data | 0x10
            else:
                return data & 0xEF
        elif bit == 3:
            if act == 0:
                return data | 0x08
            else:
                return data & 0xF7
        elif bit == 2:
            if act == 0:
                return data | 0x04
            else:
                return data & 0xFB
        elif bit == 1:
            if act == 0:
                return data | 0x02
            else:
                return data & 0xFD
        elif bit == 0:
            if act == 0:
                return data | 0x01
            else:
                return data & 0xFE

        raise ValueError('Tibbit #41 bit access error!')

    def send(self, msg):
        """
        値を送信します。
        """

        # 戻り値配列
        rtn = []

        datas = json.loads(msg)

        for data in datas:

            # GP
            gp = data['gp']

            if data['act'] == 'io':
                # 入出力の設定

                send_data = []
                send_data.append(
                    {"act": "r", "add": self.i2c_addr, "cmd": 0x00, "len": 1})
                _result = self.tp00.send(json.dumps(send_data))
                result_data = json.loads(_result.decode())

                v = data['v']

                value = result_data[0][0]
                nval = self.__bit_access(value, gp, v)

                send_data = []
                send_data.append(
                    {"act": "w", "add": self.i2c_addr, "cmd": 0x00, "v": [nval]})
                self.tp00.send(json.dumps(send_data))

            elif data['act'] == 'pup':
                # プルアップの設定

                send_data = []
                send_data.append(
                    {"act": "r", "add": self.i2c_addr, "cmd": 0x06, "len": 1})
                _result = self.tp00.send(json.dumps(send_data))
                result_data = json.loads(_result.decode())

                v = data['v']

                value = result_data[0][0]
                if v == 1:
                    nval = self.__bit_access(value, gp, 0)
                else:
                    nval = self.__bit_access(value, gp, 1)

                send_data = []
                send_data.append(
                    {"act": "w", "add": self.i2c_addr, "cmd": 0x06, "v": [nval]})
                self.tp00.send(json.dumps(send_data))

            elif data['act'] == 'set':
                # ピンの状態のセット

                send_data = []
                send_data.append(
                    {"act": "r", "add": self.i2c_addr, "cmd": 0x09, "len": 1})
                _result = self.tp00.send(json.dumps(send_data))
                result_data = json.loads(_result.decode())

                v = data['v']

                value = result_data[0][0]
                if v == 0:
                    nval = self.__bit_access(value, gp, 1)
                else:
                    nval = self.__bit_access(value, gp, 0)

                send_data = []
                send_data.append(
                    {"act": "w", "add": self.i2c_addr, "cmd": 0x09, "v": [nval]})
                self.tp00.send(json.dumps(send_data))

            elif data['act'] == 'get':
                # ピンの状態のゲット

                send_data = []
                send_data.append(
                    {"act": "r", "add": self.i2c_addr, "cmd": 0x09, "len": 1})
                _result = self.tp00.send(json.dumps(send_data))
                result_data = json.loads(_result.decode())
                value = result_data[0][0]

                if gp == 7:
                    tmp = 0x80
                elif gp == 6:
                    tmp = 0x40
                elif gp == 5:
                    tmp = 0x20
                elif gp == 4:
                    tmp = 0x10
                elif gp == 3:
                    tmp = 0x08
                elif gp == 2:
                    tmp = 0x04
                elif gp == 1:
                    tmp = 0x02
                elif gp == 0:
                    tmp = 0x01

                if value & tmp:
                    # HIGH
                    rtn.append(1)
                else:
                    # LOW
                    rtn.append(0)

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
        tp41 = Tp41(slot, host)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            recv_data = tp41.send(data)
            tpUtils.nodeOut(json.dumps(recv_data))
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
            tpUtils.nodeOut("")
