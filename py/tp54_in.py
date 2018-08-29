
from lib.tcpClient import TcpClient
import tpUtils
import sys
from constant import *


class Tp54_in:
    """
    #54 Four dry contact inputs
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """

        self.slot = slot
        self.comm = GPIO
        self.host = host

    def start(self, callback_recv):
        """
        開始処理
        """
        self.tcp_client = TcpClient(callback_recv)
        self.tcp_client.connect_by_conf_recv(self.host, self.slot, self.comm)

    def wait_for_recv(self):
        """
        データ受信待ち
        """
        self.tcp_client.recv()


def recv_event(recv_data):
    """
    データ受信イベント
    """
    try:
        tpUtils.nodeOut(recv_data.decode('utf-8'))
    except Exception as e:
        tpUtils.stderr(str(e.args))


if __name__ == '__main__':

    argvs = sys.argv
    if (len(argvs) <= 1):
        tpUtils.stderr('Need argv! [1]: slot ')
        sys.exit(0)

    try:
        slot = argvs[1]
        host = None
        if (len(argvs) > 2):
            host = argvs[2]
        tp54_in = Tp54_in(slot, host)
        tp54_in.start(recv_event)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    try:
        # 受信待ち
        tp54_in.wait_for_recv()
    except KeyboardInterrupt:
        sys.exit(0)
