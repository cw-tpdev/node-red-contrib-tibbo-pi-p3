
from lib.tcpClient import TcpClient
import tpUtils
import sys
from constant import *
import json
from tpConfig import TpConfig


class Tp05_out:
    """
    # 05 RS485 port
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

        # IN/OUT
        self.io_tcp_client = TcpClient()
        self.io_tcp_client.connect_by_conf(self.host, self.slot, GPIO)

    def send(self, msg):
        """
        データを送信します。
        """
        recv_data = self.tcp_client.send(msg)
        return recv_data

    def set_io(self, high_low):
        """
        送受信を切り替えます
        """

        # the line shall be LOW for data input and HIGH for output.
        send_data = []
        tmp_data = {}
        tmp_data["line"] = 'C'
        tmp_data["v"] = high_low
        send_data.append(tmp_data)
        self.io_tcp_client.send(json.dumps(send_data))


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
        tp05_out = Tp05_out(slot, host)
        tp05_out.start()
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            obf_data = json.loads(data)

            if 'act' in obf_data:
                # 送受信切替
                tp05_out.set_io(obf_data['v'])

            else:
                # シリアル
                tp05_out.send(bytearray(obf_data['data']))

        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
