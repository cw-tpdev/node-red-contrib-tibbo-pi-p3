
from lib.tcpClient import TcpClient
import tpUtils
import sys
from constant import *
import json
from tpConfig import TpConfig


class Tp02:
    """
    # 02 RS232/422/485 port
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """
        self.slot = slot
        self.comm = Serial
        self.host = host

        # LINE C
        self.io_tcp_client = None

        # LINE G/H
        slot_num = tpUtils.slot_str_to_int(self.slot)
        slot_num = slot_num + 1
        slot_gpio = tpUtils.slot_int_to_str(slot_num)
        self.gpio_tcp_client = TcpClient()
        self.gpio_tcp_client.connect_by_conf(self.host, slot_gpio, GPIO)

    def __setModeVal(self, ch_a, ch_b):
        """
        モードをセット
        """

        send_data = []
        tmp_data = {}
        tmp_data["line"] = 'A'
        tmp_data["v"] = ch_a
        send_data.append(tmp_data)
        tmp_data = {}
        tmp_data["line"] = 'B'
        tmp_data["v"] = ch_b
        send_data.append(tmp_data)
        self.gpio_tcp_client.send(json.dumps(send_data))

    def start(self):
        """
        開始処理
        """

        # confからmodeを取得する
        if (self.host is None or self.host == ''):
            self.host = 'localhost'
        tp_config = TpConfig(self.host, self.slot, self.comm)
        setting = tp_config.get_setting()

        mode = setting['settings']['mode']

        if mode == 'RS232':
            self.__setModeVal(1, 0)
        elif mode == 'RS422':
            self.__setModeVal(1, 1)
        elif mode == 'RS485':
            self.__setModeVal(0, 1)
            # LINE C
            self.io_tcp_client = TcpClient()
            self.io_tcp_client.connect_by_conf(self.host, self.slot, GPIO)
        else:
            raise ValueError('Tibbit #02 Line error!')

        self.tcp_client = TcpClient()
        self.tcp_client.connect_by_conf(self.host, self.slot, self.comm)

    def send(self, msg):
        """
        データを送信します。
        """
        recv_data = self.tcp_client.send(msg)
        return recv_data

    def setDtr(self, val):
        """
        DTRにHIGH/LOWを設定
        """

        send_data = []
        tmp_data = {}
        tmp_data["line"] = 'C'
        tmp_data["v"] = val
        send_data.append(tmp_data)
        self.gpio_tcp_client.send(json.dumps(send_data))

    def getDsr(self):
        """
        DSRのHIGH/LOWを取得
        """

        send_data = []
        tmp_data = {}
        tmp_data["line"] = 'D'
        send_data.append(tmp_data)
        recv_data = self.gpio_tcp_client.send(json.dumps(send_data))
        result_data = json.loads(recv_data.decode())
        return result_data[0]

    def set_io(self, high_low):
        """
        送受信を切り替えます
        """

        if self.io_tcp_client is not None:

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
        tp02 = Tp02(slot, host)
        tp02.start()
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            obf_data = json.loads(data)

            obf_data = json.loads(data)

            recv_data = ""
            if 'act' in obf_data:
                # DTR or DSR
                if obf_data['act'] == "dtr":
                    tp02.setDtr(obf_data['v'])

                elif obf_data['act'] == "dsr":
                    recv_data = tp02.getDsr()

                elif obf_data['act'] == "io":
                    tp02.set_io(obf_data['v'])

            else:
                # シリアル
                tp02.send(bytearray(obf_data['data']))

            tpUtils.nodeOut(recv_data)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
