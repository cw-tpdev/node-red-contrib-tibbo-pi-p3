
from lib.tcpClient import TcpClient
import tpUtils
import sys
from constant import *


class TpcButton:
    """
    TP Button
    """

    def __init__(self, host=None):
        """
        コンストラクタ
        """

        self.slot = "S00"
        self.comm = TP_BUTTON
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
    try:
        host = None
        if (len(argvs) > 1):
            host = argvs[1]
        tpc_button = TpcButton(host)
        tpc_button.start(recv_event)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    try:
        # 受信待ち
        tpc_button.wait_for_recv()
    except KeyboardInterrupt:
        sys.exit(0)
