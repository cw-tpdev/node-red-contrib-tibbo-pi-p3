
import socket
import sys
import time
from tpConfig import TpConfig
import tpUtils
import json


class TcpClient:
    """
    TCP Client
    """

    def __init__(self, callback_recv=None):
        """
        コンストラクタ
        """

        # バッファサイズ
        self.bufsize = 1024
        # 受信区切り文字
        self.buf_split = b"-TP-EOT-"

        # 受信時のイベント
        self.callback_recv = callback_recv

    def connect_by_conf(self, host, slot, comm):
        """
        設定から読み込み(送受信の場合)
        """
        if (host is None or host == ''):
            host = 'localhost'

        tp_config = TpConfig(host, slot, comm)
        setting = tp_config.get_setting()
        self.connect(setting['host'], setting['port'])

    def connect_by_conf_recv(self, host, slot, comm):
        """
        設定から読み込み(受信のみの場合)
        """
        if (host is None or host == ''):
            host = 'localhost'

        tp_config = TpConfig(host, slot, comm)
        setting = tp_config.get_setting()
        self.connect(setting['host'], setting['portEvent'])

    def connect(self, host, port):
        """
        接続
        """

        rty_cnt = 0
        while True:
            try:

                # 接続
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((host, port))

                # 接続完了
                tpUtils.stdout(
                    '[TP TCP Client] Successfully connected! host:' + host + ' port:' + str(port))
                # 接続したhost、portを保存
                self.host = host
                self.port = port

                break

            except ConnectionRefusedError:

                # 接続中
                tpUtils.stdout('[TP TCP Client] Try connecting')

                rty_cnt = rty_cnt + 1
                # リトライ
                # if rty_cnt >= 10:
                #    raise
                # 1秒WAIT
                try:
                    time.sleep(1)
                except KeyboardInterrupt:
                    sys.exit(0)

    def send(self, send_data):
        """
        送信
        """

        if hasattr(self, 'sock') == False or self.sock is None:
            return

        # 送受信が成功するまで繰り返す。
        while True:
            try:
                # メッセージを返します
                if type(send_data) == str:
                    self.sock.send(send_data.encode())
                else:
                    self.sock.send(send_data)

                response = self.sock.recv(self.bufsize)
                if response == b'':
                    # コネクション切断時は再接続を行う。
                    self.reconnect(self.host, self.port)
                    continue
                return response
            except Exception:
                # エラー発生時はコネクションを再接続する。
                self.reconnect(self.host, self.port)

    def reconnect(self, host, port):
        # ソケットをクローズして、コネクションの再接続を行う。
        self.sock.close()
        tpUtils.stdout("Socket erroor reconnect %s %d" % (host, port))
        self.connect(host, port)
        return

    def recv(self):
        """
        受信
        """

        if hasattr(self, 'sock') == False or self.sock is None:
            return

        # 受信データを貯める変数
        recv_data = b''

        while True:

            # イベントドリブンのようにsendを連続してくる場合、データが結合されるので対応
            try:
                rcvmsg = self.sock.recv(self.bufsize)
            except Exception:
                # エラー発生時はコネクションを再接続する。
                self.reconnect(self.host, self.port)
                continue

            # 切断時
            if rcvmsg == b'':
                # コネクション切断時は再接続を行う。
                self.reconnect(self.host, self.port)
                continue

            # 受信データ
            recv_data = recv_data + rcvmsg

            # 区切りをチェック
            find_sp = recv_data.rfind(self.buf_split)
            if find_sp != -1:

                # 分割して処理
                datas = recv_data.split(self.buf_split)

                # データが最後まで取得できているかチェック
                # 終わっていない場合は次のループで取得してもらう
                if recv_data.endswith(self.buf_split) == False:
                    datas = datas[:-1]

                for data in datas:

                    if data != b"" and self.callback_recv != None:
                        # コールバック
                        self.handler(self.callback_recv, data)

                # 読み込んだ分は消す
                recv_data = recv_data[find_sp+len(self.buf_split):]

        # クローズ
        self.sock.close()

    def lock(self, slot, name=""):
        """
        排他ロック
        """
        self.send(json.dumps({"lock": slot + "_" + name}))

    def unlock(self, slot, name=""):
        """
        排他ロック解除
        """
        self.send(json.dumps({"unlock": slot + "_" + name}))

    def handler(self, func, *args):
        """
        ハンドラー
        """
        return func(*args)
