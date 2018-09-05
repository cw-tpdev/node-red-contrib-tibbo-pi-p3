
from lib.tcpClient import TcpClient
import tpUtils
import sys
from constant import *
from tp16_out import Tp16_out


class Tp17_out(Tp16_out):
    """
    #17 Three PWMs with power outputs
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """
        super().__init__(slot, host)

    def start(self):
        """
        開始処理
        """
        super().start()

    def send(self, msg):
        """
        データを送信します。
        """
        super().send(msg)


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
        tp17_out = Tp17_out(slot, host)
        tp17_out.start()
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            tp17_out.send(data)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
