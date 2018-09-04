import sys
from tp00 import Tp00
import tpUtils
from constant import *
import json
import time
from lib.tcpClient import TcpClient


class Tp31:
    """
    #31 PIC coprocessor
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """

        self.slot = slot
        self.comm = I2C
        self.host = host

        self.tcp_client = TcpClient()
        self.tcp_client.connect_by_conf(self.host, self.slot, self.comm)

        # RST / INT
        self.rst_tcp_client = TcpClient()
        self.rst_tcp_client.connect_by_conf(self.host, self.slot, GPIO)

    def pic_reg_read(self, address, num):
        """
        PICのレジスタRead
        """
        addr1 = address >> 8
        addr2 = address & 0x00FF

        send_data = []
        send_data.append(
            {"act": "w", "add": 0x03, "cmd": 0xFE, "v": [addr1, addr2]})
        self.tcp_client.send(json.dumps(send_data))

        time.sleep(0.01)

        send_data = []
        send_data.append(
            {"act": "r", "add": 0x03, "cmd": 0, "len": num})
        _result = self.tcp_client.send(json.dumps(send_data))
        result_data = json.loads(_result.decode())

        return result_data[0]

    def pic_reg_write(self, address, vals):
        """
        PICのレジスタWrite
        """
        addr1 = address >> 8
        addr2 = address & 0x00FF
        dat = [addr1, addr2]
        dat.extend(vals)

        send_data = []
        send_data.append(
            {"act": "w", "add": 0x03, "cmd": 0xFE, "v": dat})
        self.tcp_client.send(json.dumps(send_data))

    def pic_reg_reset(self):
        """
        PICのレジスタReset
        """

        send_data = []
        tmp_data = {}
        tmp_data["line"] = 'C'
        tmp_data["v"] = 0
        send_data.append(tmp_data)
        self.rst_tcp_client.send(json.dumps(send_data))

        time.sleep(0.01)

        send_data = []
        tmp_data = {}
        tmp_data["line"] = 'C'
        tmp_data["v"] = 1
        send_data.append(tmp_data)
        self.rst_tcp_client.send(json.dumps(send_data))

    def pic_reg_int(self):
        """
        PICのINT取得
        """
        send_data = []
        tmp_data = {}
        tmp_data["line"] = 'D'
        send_data.append(tmp_data)
        recv_data = self.rst_tcp_client.send(json.dumps(send_data))
        result_data = json.loads(recv_data.decode())
        return result_data[0]

    def send(self, msg):
        """
        データを送信します。
        """

        # 戻り値配列
        rtn_r = []
        rtn_int = []

        datas = json.loads(msg)

        for data in datas:

            if data['act'] == 'r':
                # 読み込み

                address = data['add']
                len = int(data['len'])
                read_data = self.pic_reg_read(address, len)
                rtn_r.append(read_data)

            elif data['act'] == 'w':
                # 書き込み

                address = data['add']
                vals = data['v']
                self.pic_reg_write(address, vals)

            elif data['act'] == 'rst':
                # リセット

                self.pic_reg_reset()

            elif data['act'] == 'int':
                # INT

                read_data = self.pic_reg_int()
                rtn_int.append(read_data)

        rtn = {}
        rtn['r'] = rtn_r
        rtn['int'] = rtn_int
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
        tp31 = Tp31(slot, host)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            recv_data = tp31.send(data)
            tpUtils.nodeOut(json.dumps(recv_data))
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
            tpUtils.nodeOut("")
