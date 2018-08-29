
from lib.tcpClient import TcpClient
import tpUtils
import sys
from constant import *


class TpcBuzzer:
    """
    TP Buzzer
    """

    def __init__(self, host=None):
        """
        コンストラクタ
        """
        self.slot = "S00"
        self.comm = TP_BUZZER
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
    try:
        host = None
        if (len(argvs) > 1):
            host = argvs[1]
        tpc_buzzer = TpcBuzzer(host)
        tpc_buzzer.start()
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            tpc_buzzer.send(data)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
