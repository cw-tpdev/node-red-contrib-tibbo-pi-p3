
from lib.tcpClient import TcpClient
import tpUtils
import sys
from constant import *
import json


class Tp01_out:
    """
    #01 Four-line RS232 port
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """
        self.slot = slot
        self.comm = Serial
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
        tp01_out = Tp01_out(slot, host)
        tp01_out.start()
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            # {"type":"Buffer","data":[110,117]}
            data = input()
            obf_data = json.loads(data)
            tp01_out.send(bytearray(obf_data['data']))
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
