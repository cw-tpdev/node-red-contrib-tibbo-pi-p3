
import sys
from tp00 import Tp00
import json
from constant import *
import tpUtils
from lib.tcpClient import TcpClient
from tpConfig import TpConfig


class Tp57_out:
    """
    # 57 FPGA Tibbit
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """
        self.slot = slot
        self.comm = 'TP57'
        self.host = host

        self.tcp_client = TcpClient()
        self.tcp_client.connect_by_conf(self.host, self.slot, self.comm)

    def send(self, msg):
        """
        データを送信します。
        """

        self.tcp_client.send(msg)


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
        tp57_out = Tp57_out(slot, host)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            tp57_out.send(data)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
