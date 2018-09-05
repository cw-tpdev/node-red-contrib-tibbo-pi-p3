import time
import json
from constant import *
from tpBoardInterface import TpBoardInterface
from tpEtcInterface import TpEtcInterface
import tpUtils
import base64


class TpControl:
    """
    Tibbo-Pi制御を行います。
    """

    def __init__(self, settings, callback_send):
        """
        コンストラクタ

        settings：config.json(設定)
        callback_send：イベントドリブン用のコールバック関数
        """

        # 設定
        self.settings = settings

        # イベント発生用のコールバック関数をセット
        self.callback_send = callback_send

        # 基板用インターフェース準備
        self.tp_inter = TpBoardInterface(settings, self.__send_data)
        self.etc_inter = TpEtcInterface(self.tp_inter)

    def control(self, setting, rcv_msg):
        """
        制御を行います。

        setting: この制御に関する設定
        rcv_msg: 制御するための情報
        """
        if setting['comm'] == TP_BUZZER:
            #--------------
            # ブザー
            #--------------

            # Jsonでデータ取得
            data = json.loads(rcv_msg.decode())

            # 鳴らす時間
            btime = data['time']
            # パターン
            pattern = data['ptn']

            # ブザーの制御を行う
            self.tp_inter.rp_buzzer(btime, pattern)

            # 戻り値は無し
            return

        elif setting['comm'] == TP_LED:
            #--------------
            # LED
            #--------------

            # Jsonでデータ取得
            data = json.loads(rcv_msg.decode())

            # LED番号
            no = data['no']
            # 値
            val = data['v']

            # LEDの制御を行う
            self.tp_inter.rp_led(no, val)

            # 戻り値は無し
            return

        # 以下、通信方式により各制御を行う
        elif setting['comm'] == GPIO:
            #--------------
            # GPIO
            #--------------

            # 戻り値配列
            rtn = []

            # Jsonでデータ取得
            datas = json.loads(rcv_msg.decode())

            for data in datas:

                # ライン
                line = data['line']
                # 値
                # None もしくは''の場合は読み込み
                if 'v' in data:
                    val = data['v']
                else:
                    val = None

                status = [stg['status']
                          for stg in setting['pin'] if stg['name'] == line]
                status = status[0]

                if status == 'IN':
                    read_data = self.tp_inter.gpio_read(setting['slot'], line)
                    rtn.append(read_data)

                elif status == 'IN_Analog':
                    read_data = self.tp_inter.analog_read(
                        setting['slot'], line)
                    rtn.append(read_data)

                elif status == 'OUT' or status == 'OUT_OD':
                    self.tp_inter.gpio_write(setting['slot'], line, val)

                elif status == 'IN_OUT':

                    # モードチェンジか
                    if 'mode' in data:
                        change_flg = True
                    else:
                        change_flg = False

                    # IN or OUT
                    if 'io' in data:
                        io = data['io']
                    else:
                        io = None

                    if io == 'IN':
                        self.tp_inter.gpio_in_out_init(
                            setting['slot'], line, 2)

                        if (change_flg == False):
                            read_data = self.tp_inter.gpio_read(
                                setting['slot'], line)
                            rtn.append(read_data)

                    elif io == 'OUT':
                        self.tp_inter.gpio_in_out_init(
                            setting['slot'], line, 4)

                        if (change_flg == False):
                            self.tp_inter.gpio_write(
                                setting['slot'], line, val)

                    elif io == 'OUT_OD':
                        self.tp_inter.gpio_in_out_init(
                            setting['slot'], line, 3)

                        if (change_flg == False):
                            self.tp_inter.gpio_write(
                                setting['slot'], line, val)

            # Jsonで返却
            return json.dumps(rtn)

        elif setting['comm'] == I2C:
            #--------------
            # I2c
            #--------------

            # 戻り値配列
            rtn = []

            # Jsonでデータ取得
            datas = json.loads(rcv_msg.decode())

            for data in datas:
                # 各命令を行う

                # アドレス
                address = data['add']

                if data['act'] == 'r':
                    # 読み込み

                    # len
                    len = int(data['len'])

                    # I2C 読み出し処理を行う
                    if 'cmd' in data:
                        read_data = self.tp_inter.i2c_read_with_cmd(
                            setting['slot'], address, data['cmd'], len)
                    else:
                        read_data = self.tp_inter.i2c_read(
                            setting['slot'], address, len)

                    # 戻り値
                    rtn.append(read_data)

                elif data['act'] == 'w':
                    # 書き込み

                    # value
                    vals = data['v']

                    # I2C 書き込み処理を行う
                    if 'cmd' in data:
                        self.tp_inter.i2c_write_with_cmd(
                            setting['slot'], address, data['cmd'], vals)
                    else:
                        self.tp_inter.i2c_write(
                            setting['slot'], address, vals)

            # Jsonで返却
            return json.dumps(rtn)

        elif setting['comm'] == SPI:
            #--------------
            # SPI
            #--------------

            # 戻り値配列
            rtn = []

            # Jsonでデータ取得
            datas = json.loads(rcv_msg.decode())

            for data in datas:

                # アドレス
                address = data['add']

                # value
                vals = data['v']

                # SPIの処理を行う。SPIの場合は必ず戻り値がある
                rtn_data = self.tp_inter.spi_access(
                    setting['slot'], address, vals)

                # 戻り値
                rtn.append(rtn_data)

            # Jsonで返却
            return json.dumps(rtn)

        elif setting['comm'] == Serial:
            #--------------
            # Serial
            #--------------

            # Serial送信の処理を行う。
            rtn_data = self.tp_inter.serial_write(
                setting['slot'], rcv_msg)

            # 戻り値は無し
            return

        elif setting['comm'] == 'TP22':
            #--------------
            # Tibbit #22
            #--------------

            # Jsonでデータ取得
            data = json.loads(rcv_msg.decode())

            if data['act'] == 'v':

                # バージョン
                return self.etc_inter.tp22_get_ver(setting['slot'])

            elif data['act'] == 'init':

                # 初期化
                self.etc_inter.tp22_init(setting['slot'])

            elif data['act'] == 't':

                # 温度
                return str(self.etc_inter.tp22_get_temp(setting['slot'], setting['settings']['kind']))

        elif setting['comm'] == 'TP26':
            #--------------
            # Tibbit #26
            #--------------

            # Jsonでデータ取得
            data = json.loads(rcv_msg.decode())

            if data['act'] == 'fw':

                # FPGA内容書き込み
                self.etc_inter.tpFPGA_write(setting['slot'], data['file_path'])

            if data['act'] == 'w':

                # 記録開始
                self.etc_inter.tp26_start_record(setting['slot'])

            if data['act'] == 'r':

                # 記録データ取得 encodeする
                _result = self.etc_inter.tp26_get_record(setting['slot'])
                readData = base64.b64encode(_result)
                return readData

            if data['act'] == 'set':

                # 記録データセット decodeする
                bin_file = base64.b64decode(data['data'])
                return self.etc_inter.tp26_put_play(setting['slot'], bin_file)

            if data['act'] == 'play':

                # 記録データ再生
                return self.etc_inter.tp26_start_play(setting['slot'])

            return

        elif setting['comm'] == 'TP52':
            #--------------
            # Tibbit #52
            #--------------

            # Jsonでデータ取得
            datas = json.loads(rcv_msg.decode())

            if (type(datas) != list) and (datas['act'] == 'init'):

                # 初期化
                self.etc_inter.tp52_init(setting['slot'])

                # 補正値の取得
                self.tp52_correct = self.etc_inter.tp52_get_correct(
                    setting['slot'])

            else:

                # 戻り値配列
                rtn = []

                for data in datas:

                    # ch
                    ch = "CH" + str(data['ch'])

                    # 補正値取得
                    cor = None
                    try:
                        idx = data['ch'] - 1
                        cor = self.tp52_correct[idx]
                    except:
                        pass

                    # 電圧取得
                    vol = self.etc_inter.tp52_get_volt(
                        setting['slot'], ch)

                    # 電圧値と補正値を返却
                    rtn_data = [vol, cor]

                    # 戻り値
                    rtn.append(rtn_data)

                # Jsonで返却
                return json.dumps(rtn)

            return

        elif setting['comm'] == 'TP57':
            #--------------
            # Tibbit #57
            #--------------

            # Jsonでデータ取得
            data = json.loads(rcv_msg.decode())

            if data['act'] == 'fw':

                # FPGA内容書き込み
                self.etc_inter.tpFPGA_write(setting['slot'], data['file_path'])

            return

    def __send_data(self, slot, comm, send_msg):
        """
        データを送信します。
        """

        # slot: スロット番号
        # comm: 通信方式
        # send_msg: 送信メッセージ
        self.handler(self.callback_send, slot, comm, send_msg)

    def handler(self, func, *args):
        """
        ハンドラー
        """
        return func(*args)
