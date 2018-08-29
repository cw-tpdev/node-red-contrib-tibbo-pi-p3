
from lib.tcpClient import TcpClient
import tpUtils
import sys
from constant import *
import json


class Tp00:
    """
    #00 direct I/O lines
    """

    def __init__(self, slot, comm, host=None):
        """
        コンストラクタ
        """
        self.slot = slot
        self.comm = comm
        self.host = host

    def start(self):
        """
        開始処理
        """
        self.tcp_client = TcpClient()
        self.tcp_client.connect_by_conf(self.host, self.slot, self.comm)

    def send(self, msg):
        """
        データを送信します。
        """
        recv_data = self.tcp_client.send(msg)
        return recv_data

    def lock(self, slot, name=""):
        """
        排他ロック
        """
        self.tcp_client.lock(slot, name)

    def unlock(self, slot, name=""):
        """
        排他ロック解除
        """
        self.tcp_client.unlock(slot, name)


if __name__ == '__main__':

    argvs = sys.argv
    if (len(argvs) <= 2):
        tpUtils.stderr('Need argv! [1]: slot [2]: communication')
        sys.exit(0)

    try:
        slot = argvs[1]
        comm = argvs[2]
        host = None
        if (len(argvs) > 3):
            host = argvs[3]
        tp00 = Tp00(slot, comm, host)
        tp00.start()
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            if (comm != Serial):
                recv_data = tp00.send(data)
            else:
                obf_data = json.loads(data)
                recv_data = tp00.send(bytearray(obf_data['data']))

            tpUtils.nodeOut(recv_data.decode('utf-8'))
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
            tpUtils.nodeOut("")
