
from lib.tcpClient import TcpClient
import tpUtils
import sys
import json


class Tp22:
    """
    #22 RTD Temperature Meter
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """
        self.slot = slot
        self.comm = 'TP22'
        self.host = host

    def start(self):
        """
        開始処理
        """
        self.tcp_client = TcpClient()
        self.tcp_client.connect_by_conf(self.host, self.slot, self.comm)

        # 初期化処理
        self.tcp_client.send(json.dumps({"act": "init"}))

    def get_data(self):
        """
        データを取得します。
        """
        # Lock
        self.tcp_client.lock(self.slot)
        try:
            _result = self.tcp_client.send(json.dumps({"act": "t"}))
            result_data = tpUtils.to_float(_result.decode())
            return result_data
        finally:
            # unLock
            self.tcp_client.unlock(self.slot)


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
        tp22 = Tp22(slot, host)
        tp22.start()
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            recv_data = tp22.get_data()
            tpUtils.nodeOut(recv_data)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
            tpUtils.nodeOut("")
