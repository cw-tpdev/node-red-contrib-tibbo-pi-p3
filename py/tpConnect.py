from lib.tcpServer import TcpServer
import tpUtils
import time
import sys
import json
import os
from tpControl import TpControl
from tpConfig import TpConfig
import traceback
import threading


class TpConnect:
    """
    Tibbo-Pi制御.pyとの仲介を行います。
    """

    def __init__(self, settings, connect_flg):
        """
        コンストラクタ
        """

        # TCPサーバー保持用
        self.tcp_server_list = {}

        # 排他ロック確認用
        self.__lockList = []

        # 外部からの接続可否
        self.connect_flg = connect_flg

        # 設定の保持
        self.tp_config = TpConfig()

        # 制御用インスタンス
        self.tp_control = TpControl(
            self.tp_config.get_settings(), self.__send_data)

    def start(self):
        """
        設定をもとに、サーバーを複数起動します。
        """

        # 複数起動
        settings = self.tp_config.get_settings()
        for setting in settings:

            # hostがlocalhostのノードのみ起動する(別IPはここでは起動しない)
            if setting['host'] != 'localhost':
                continue

            # 受信用
            if 'port' in setting:
                client_thread = threading.Thread(target=self.__server_thread_event_recv,
                                                 args=(setting,))
                client_thread.daemon = True
                client_thread.start()

            # イベントドリブン用
            if 'portEvent' in setting:
                client_thread = threading.Thread(target=self.__server_thread_event_send,
                                                 args=(setting,))
                client_thread.daemon = True
                client_thread.start()

    def __server_thread_event_recv(self, setting):
        """
        サーバーを起動します。（リクエスト・リプライ）
        """

        try:

            # TCPサーバー(設定情報を渡す)
            tcp_srv = TcpServer(self.__recv_data, setting)

            # 保持(ポートごと)
            self.tcp_server_list[setting['port']] = tcp_srv

            # 受信待ち
            bind_host = 'localhost'
            if self.connect_flg:
                # 外部も許可
                bind_host = ''
            tcp_srv.recv(bind_host, setting['port'])

        except Exception as e:
            # 失敗
            tpUtils.stderr(traceback.format_exc())

    def __server_thread_event_send(self, setting):
        """
        サーバーを起動します。（リプライ）
        """

        try:

            # TCPサーバー(設定情報を渡す)
            tcp_srv = TcpServer(None, setting)

            # 保持(ポートごと)
            self.tcp_server_list[setting['portEvent']] = tcp_srv

            # 待機
            bind_host = 'localhost'
            if self.connect_flg:
                # 外部も許可
                bind_host = ''
            tcp_srv.recv(bind_host, setting['portEvent'])

        except Exception as e:
            # 失敗
            tpUtils.stderr(traceback.format_exc())

    def __lock(self, rcv_msg):
        """
        クライアントの排他を行う
        """

        try:
            chkLock = json.loads(rcv_msg.decode())
            if 'lock' in chkLock:
                # ロック
                lockCnt = 0
                while True:
                    if not chkLock['lock'] in self.__lockList:
                        break
                    if lockCnt > 40:
                        # 無限に待たず2秒程度で終わらせる
                        break
                    time.sleep(0.05)
                    lockCnt = lockCnt + 1

                self.__lockList.append(chkLock['lock'])
                return True

            elif 'unlock' in chkLock:
                # ロック解除
                try:
                    self.__lockList.remove(chkLock['unlock'])
                except ValueError:
                    pass
                return True

            else:
                pass
        except:
            pass

        return False

    def __recv_data(self, info, rcv_msg):
        """
        TCPのデータが受信された場合、処理を行いデータをSendする（リクエスト・リプライ専用）
        """
        try:
            # 排他ロック確認
            if self.__lock(rcv_msg):
                return

            return self.tp_control.control(info, rcv_msg)

        except tpUtils.TpCheckError as e:
            # トレースは出さず、メッセージのみ
            tpUtils.stderr(str(e.args))
            return "-- FAIL ---"
        except Exception as e:
            # 失敗
            tpUtils.stderr(traceback.format_exc())
            return "-- FAIL ---"

    def __send_data(self, slot, comm, send_msg):
        """
        制御からイベントが発生した場合、TCPにてクライアントにデータを送信します。
        """
        try:

            # スロットと通信方法から送信するportを特定(localhostのみ)
            setting = self.tp_config.get_setting('localhost', slot, comm)
            if setting == None or 'portEvent' not in setting:
                return

            port = setting['portEvent']

            if (port != None and port in self.tcp_server_list):

                # 取得したポートにデータを送信する
                tcp_srv = self.tcp_server_list[port]
                tcp_srv.send(send_msg)

        except tpUtils.TpCheckError as e:
            # トレースは出さず、メッセージのみ
            tpUtils.stderr(str(e.args))
            return "-- FAIL ---"
        except Exception as e:
            # 失敗
            tpUtils.stderr(traceback.format_exc())


if __name__ == '__main__':

    argvs = sys.argv
    setting_file = None
    if (len(argvs) > 1):
        setting_file = argvs[1]

    connect_flg = False
    if (len(argvs) > 2 and argvs[2] == 'true'):
        connect_flg = argvs[2]

    try:

        # インスタンス生成
        tp_connect = TpConnect(setting_file, connect_flg)

    except tpUtils.TpCheckError as e:
        # トレースは出さず、メッセージのみ
        tpUtils.stderr(str(e.args))
        tpUtils.stderr('Tibbo-Pi failed to start up.')
        sys.exit(0)

    # サーバ起動
    tp_connect.start()

    # 接続完了
    tpUtils.stdout('Successfully connected!')

    # 待ち処理
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
