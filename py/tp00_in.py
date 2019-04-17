
from lib.tcpClient import TcpClient
import tpUtils
import sys
from constant import *
import json


class Tp00_in:
    """
    #00 direct I/O lines
    """

    def __init__(self, slot, comm, host=None, target_line=['A', 'B', 'C', 'D']):
        """
        コンストラクタ
        """

        self.slot = slot
        self.comm = comm
        self.host = host
        # GPIOのみ有効(対象となるライン)
        self.target_line = target_line

    def start(self, callback_recv):
        """
        開始処理
        """

        self.callback_recv = callback_recv

        self.tcp_client = TcpClient(self.__callback_recv)
        self.tcp_client.connect_by_conf_recv(self.host, self.slot, self.comm)

    def wait_for_recv(self):
        """
        データ受信待ち
        """
        self.tcp_client.recv()

    def __callback_recv(self, recv_data):
        """
        データ受信イベント
        """

        if self.comm == GPIO:
            # GPIOの場合、監視対象のラインかチェック
            result_data = json.loads(recv_data.decode())
            if result_data['line'] in self.target_line:
                # 含むときだけコールバックを呼ぶ
                self.handler(self.callback_recv, recv_data)
        else:
            self.handler(self.callback_recv, recv_data)

    def handler(self, func, *args):
        """
        ハンドラー
        """
        return func(*args)


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
        target_line = []
        if (len(argvs) > 3):
            host = argvs[3]
        # 監視対象のライン(ABCDのような文字列で来る)
        # 同じスロットに対して、別なインスタンスで監視対象のラインを変えたい場合に指定する。
        if (len(argvs) > 4):
            # 例：['A', 'B', 'C', 'D']
            target_line = json.loads(argvs[4])
        tp00_in = Tp00_in(slot, comm, host, target_line)
        tp00_in.start(recv_event)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    try:
        # 受信待ち
        tp00_in.wait_for_recv()
    except KeyboardInterrupt:
        sys.exit(0)
