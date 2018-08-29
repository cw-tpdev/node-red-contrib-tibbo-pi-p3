import sys
from tp00_in import Tp00_in
import tpUtils
from constant import *
import json


class Tp38_in:
    """
    #38 Pushbutton
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """
        self.slot = slot
        self.comm = GPIO
        self.host = host

        # tp00_in
        self.tp00_in = Tp00_in(self.slot, self.comm, self.host)
        self.tp00_in.start(self.recv_event)

    def start(self, callback_recv):
        """
        開始処理
        """
        self.callback_recv = callback_recv
        # 受信待ち
        self.tp00_in.wait_for_recv()

    def recv_event(self, recv_data):
        """
        データ受信イベント
        """
        try:

            # jsonで受け取る
            result = json.loads(recv_data.decode())

            # on/offをコールバック(on/offは反転)
            if result['v'] == 0:
                val = 1
            else:
                val = 0
            self.handler(self.callback_recv, val)

        except Exception as e:
            tpUtils.stderr(str(e.args))

    def handler(self, func, *args):
        """
        ハンドラー
        """
        return func(*args)


def recv_event(flag):
    """
    データ受信イベント
    """
    try:
        tpUtils.nodeOut(flag)
    except Exception as e:
        tpUtils.stderr(str(e.args))


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
        tp38_in = Tp38_in(slot, host)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    try:
        # 受信待ち
        tp38_in.start(recv_event)
    except KeyboardInterrupt:
        sys.exit(0)
