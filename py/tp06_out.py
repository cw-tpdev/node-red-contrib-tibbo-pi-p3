
from lib.tcpClient import TcpClient
import tpUtils
import sys
from constant import *


class Tp06_out:
    """
    #06 Two high-power relays
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """
        self.slot = slot
        self.comm = GPIO
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
        tp06_out = Tp06_out(slot, host)
        tp06_out.start()
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            tp06_out.send(data)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
