
import sys
from tp00 import Tp00
import json
from constant import *
import tpUtils
from lib.tcpClient import TcpClient
from tpConfig import TpConfig


class Tp40_out:
    """
    # 40 Digital potentiometer
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """
        self.slot = slot
        self.comm = I2C
        self.host = host

        # アドレス
        self.i2c_addr = 0x2F

        self.tcp_client = TcpClient()
        self.tcp_client.connect_by_conf(self.host, self.slot, self.comm)

        # 初期化
        send_data = []
        send_data.append(self.__reg_read(0x50))
        send_data.append(self.__reg_write(0x40, 0x000F))
        send_data.append(self.__reg_read(0x40))
        send_data.append(self.__reg_read(0x20))
        self.tcp_client.send(json.dumps(send_data))

    def send(self, data):
        """
        値を送信します。
        """

        level = tpUtils.to_num(data)
        level = level % 257

        send_data = []
        send_data.append(self.__reg_write(0x0, level))
        self.tcp_client.send(json.dumps(send_data))

    def __reg_write(self, addr, data):
        """
        reg_write
        """

        if data & 0x0100:
            cmd = addr + 1
        else:
            cmd = addr

        return {"act": "w", "add": self.i2c_addr, "cmd": cmd, "v": [(data & 0x00FF)]}

    def __reg_read(self, addr):
        """
        reg_read
        """

        cmd = addr + 0xC
        return {"act": "r", "add": self.i2c_addr, "cmd": cmd, "len": 2}


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
        tp40_out = Tp40_out(slot, host)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            tp40_out.send(data)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
