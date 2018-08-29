
from lib.tcpClient import TcpClient
import tpUtils
import sys
from constant import *
import json
from tpConfig import TpConfig
import time
import _thread as thread


class Tp02_in:
    """
    #02 RS232/422/485 port
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """

        self.slot = slot
        self.comm = Serial
        self.host = host

    def __setModeVal(self, ch_a, ch_b):
        """
        モードをセット
        """

        slot_num = tpUtils.slot_str_to_int(self.slot)
        slot_num = slot_num + 1
        slot_gpio = tpUtils.slot_int_to_str(slot_num)
        temp_tcp_client = TcpClient()
        temp_tcp_client.connect_by_conf(self.host, slot_gpio, GPIO)

        send_data = []
        tmp_data = {}
        tmp_data["line"] = 'A'
        tmp_data["v"] = ch_a
        send_data.append(tmp_data)
        tmp_data = {}
        tmp_data["line"] = 'B'
        tmp_data["v"] = ch_b
        send_data.append(tmp_data)
        temp_tcp_client.send(json.dumps(send_data))

    def start(self, callback_recv, callback_recv_dsr):
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
        else:
            raise ValueError('Tibbit #02 Line error!')

        self.tcp_client = TcpClient(callback_recv)
        self.tcp_client.connect_by_conf_recv(self.host, self.slot, self.comm)

        # DSR
        slot_num = tpUtils.slot_str_to_int(self.slot)
        slot_num = slot_num + 1
        slot_gpio = tpUtils.slot_int_to_str(slot_num)
        self.gpio_tcp_client = TcpClient(callback_recv_dsr)
        self.gpio_tcp_client.connect_by_conf_recv(self.host, slot_gpio, GPIO)

    def wait_for_recv(self):
        """
        データ受信待ち
        """

        thread.start_new_thread(self.tcp_client.recv, ())
        thread.start_new_thread(self.gpio_tcp_client.recv, ())

        # 待ち処理
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def recv_event(recv_data):
    """
    データ受信イベント
    """
    try:
        tpUtils.nodeOut(recv_data.decode('utf-8'))
    except Exception as e:
        tpUtils.stderr(str(e.args))


def recv_event_dsr(recv_data):
    """
    データ受信イベント(DSR)
    """
    try:

        result_data = json.loads(recv_data.decode())
        tpUtils.nodeOut(result_data['v'])

    except Exception as e:
        tpUtils.stderr(str(e.args))


if __name__ == '__main__':

    argvs = sys.argv
    if (len(argvs) <= 1):
        tpUtils.stderr('Need argv! [1]: slot ')
        sys.exit(0)

    try:
        slot = argvs[1]
        host = None
        if (len(argvs) > 2):
            host = argvs[2]
        tp02_in = Tp02_in(slot, host)
        tp02_in.start(recv_event, recv_event_dsr)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    try:
        # 受信待ち
        tp02_in.wait_for_recv()
    except KeyboardInterrupt:
        sys.exit(0)
