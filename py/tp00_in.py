
from lib.tcpClient import TcpClient
import tpUtils
import sys


class Tp00_in:
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
    if (len(argvs) <= 2):
        tpUtils.stderr('Need argv! [1]: slot [2]: communication')
        sys.exit(0)

    try:
        slot = argvs[1]
        comm = argvs[2]
        host = None
        if (len(argvs) > 3):
            host = argvs[3]
        tp00_in = Tp00_in(slot, comm, host)
        tp00_in.start(recv_event)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    try:
        # 受信待ち
        tp00_in.wait_for_recv()
    except KeyboardInterrupt:
        sys.exit(0)

