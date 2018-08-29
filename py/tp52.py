
from lib.tcpClient import TcpClient
import tpUtils
import sys
from constant import *
import json
import time


class Tp52:
    """
    #52 Four-channel isolated +/-10V ADC
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """

        self.slot = slot
        self.comm = 'TP52'
        self.host = host

    def start(self):
        """
        開始処理
        """
        self.tcp_client = TcpClient()
        self.tcp_client.connect_by_conf(self.host, self.slot, self.comm)

        # 初期化処理
        self.tcp_client.send(json.dumps({"act": "init"}))

    def get_data(self, msg):
        """
        値を取得します。
        """

        _result = self.tcp_client.send(msg)
        result_data = json.loads(_result.decode())

        return result_data


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
        tp52 = Tp52(slot, host)
        tp52.start()
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            recv_data = tp52.get_data(data)
            tpUtils.nodeOut(json.dumps(recv_data))
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
            tpUtils.nodeOut("")
