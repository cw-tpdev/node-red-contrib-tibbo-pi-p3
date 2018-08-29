import sys
import tpUtils
from constant import *
import json
from lib.tcpClient import TcpClient
import os


class Tp26:
    """
    #26 IR code processor
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """

        self.slot = slot
        self.comm = 'TP26'
        self.host = host

        self.tcp_client = TcpClient()
        self.tcp_client.connect_by_conf(self.host, self.slot, self.comm)

        # FPGA内容書き込み
        file = os.path.dirname(os.path.abspath(__file__)) + \
            '/bin/IR_Remote_bitmap.bin'

        if os.path.exists(file) == False:
            raise FileNotFoundError("Not Found: " + file)
        self.tcp_client.send(json.dumps({"act": "fw", "file_path": file}))

    def send(self, msg):
        """
        データを送信します。
        """

        _result = self.tcp_client.send(msg)
        return _result.decode('utf-8')


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
        tp26 = Tp26(slot, host)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            recv_data = tp26.send(data)
            tpUtils.nodeOut(recv_data)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
            tpUtils.nodeOut("")
