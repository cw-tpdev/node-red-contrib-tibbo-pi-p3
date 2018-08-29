import socket
import select
import sys
import tpUtils
import threading
import time


class TcpServer:
    """
    TCP Server
    """

    def __init__(self, callback_recv, info):
        """
        コンストラクタ

        callback_recv: 受信時のコールバック関数
        info: 受信時に渡す設定情報など
        """

        # バッファサイズ
        self.bufsize = 1024
        # 送信区切り文字
        self.buf_split = b"-TP-EOT-"

        # 受信時のイベント
        self.callback_recv = callback_recv
        self.info = info

        # ソケットリスト
        self.lst_clientsock = []

    def __client_handler(self, clientsock):
        """
        受信処理スレッド
        """

        while True:

            try:
                # 受信
                rcvmsg = clientsock.recv(self.bufsize)
                #tpUtils.stdout('Received -> %s' % (rcvmsg))
            except Exception:
                # コネクション切断等のエラー時はコネクションの再接続を行う。
                break

            # 切断時
            if rcvmsg == b'':
                # コネクション切断時は再接続を行う。
                break

            if self.callback_recv != None:

                # コールバック
                send_data = self.handler(
                    self.callback_recv, self.info, rcvmsg)

                try:
                    # メッセージを返します
                    if (send_data is None or send_data == ''):
                        # Noneという文字列を返却
                        clientsock.send('None'.encode())
                    elif type(send_data) == str:
                        # 文字
                        clientsock.send(send_data.encode())
                    else:
                        # bytes
                        clientsock.send(send_data)
                except Exception:
                    # コネクション切断等のエラー時はコネクションの再接続を行う。
                    break

        # クローズ
        clientsock.close()
        # コネクション切断時は再接続を行う。
        tpUtils.stdout("Socket erroor reconnect %s %d" %
                       (self.host, self.port))

    def recv(self, host, port):
        """
        受信イベント
        """

        self.host = host
        self.port = port

        rty_cnt = 0
        while True:

            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            while True:
                try:
                    self.sock.bind((host, port))
                    break
                except:
                    rty_cnt = rty_cnt + 1
                    # リトライ
                    if rty_cnt >= 10:
                        raise
                    try:
                        time.sleep(1)
                    except KeyboardInterrupt:
                        sys.exit(0)

            self.sock.listen(100)

            tpUtils.stdout("Server listening on %s %d" % (host, (port)))

            # 接続待機
            clientsock, _ = self.sock.accept()

            # 配列に保持する
            self.lst_clientsock.append(clientsock)

            # 受信イベントスレッド
            client_thread = threading.Thread(target=self.__client_handler,
                                             args=(clientsock,))
            client_thread.daemon = True
            client_thread.start()

    def send(self, send_data):
        """
        送信処理
        """

        for clientsock in self.lst_clientsock:

            try:
                # メッセージを返します
                if type(send_data) == str:
                    clientsock.send(send_data.encode() + self.buf_split)
                else:
                    clientsock.send(send_data + self.buf_split)
            except:
                pass

    def handler(self, func, *args):
        """
        ハンドラー
        """
        return func(*args)
