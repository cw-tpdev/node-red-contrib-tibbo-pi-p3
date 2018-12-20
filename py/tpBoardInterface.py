#!/usr/bin/python3
import os, sys
import _thread as thread
import time
#from tpP1Interface import TpP1Interface
#from tpP2Interface import TpP2Interface
from tpP3Interface import TpP3Interface
from constant import *
import json
import tpUtils
import re

# 定数宣言 ---------------------------------------------------------------
LINE_SETTING_NONE     = 0
LINE_SETTING_A_IN     = 1
LINE_SETTING_D_IN     = 2
LINE_SETTING_D_OUT_OD = 3 # オープンドレイン
LINE_SETTING_D_OUT    = 4 # TTL

# クラス宣言 -------------------------------------------------------------
class TpBoardInterface:
    """ Tibbo-Pi基板とのインターフェース層です。
    """

    def __init__(self, settings, callback_send):
        """ コンストラクタ
            settings      : 上位側のconfig情報
            callback_send : GPIO入力、およびSerial読み込み割り込み発生時のcallback関数
        """
        # データ初期化
        self.__serial_recv_buf = [[] for i in range(5)] # serail 5slotぶんのバッファslot 1,3,5,7,9 の順
        self.__serial_info = [{'recv_kind':''} for i in range(5)] # serail 5slotぶんの情報
        """ {'recv_kind':以下}
	    'NONE'/'CHAR'/'LENG'/'TI
	    で、それぞれ必要なら、
	    {'char':1文字}
	    {'leng':長さ}
	    {'time':ms}
        """

        # P1/P2/P3 切り替え
        self.__board_kind = 'P3'
        if self.__board_kind == 'P1':
            self.__board = TpP1Interface()
        elif self.__board_kind == 'P2':
            self.__board = TpP2Interface()
        else: # P3
            self.__board = TpP3Interface()
        self.board = self.__board 
        
        # 排他制御用定義
        self.i2c_lock = thread.allocate_lock()
        self.spi_lock = thread.allocate_lock()
        if self.__board_kind == 'P2' or self.__board_kind == 'P3':
            self.__board.spi_lock_init(self.spi_lock)

        # I2C健全性チェック
        self.__board.i2c_check_before_init()

        # FWバージョン確認
        self.__board.check_pic_fw()
        self.__board.read_pic_fw_ver(True)
        tpUtils.stdout('Board FW ver = ' + str(self.get_pic_fw_ver()))

        # ボード初期化
        self.__board.board_init()
        
        # 設定
        self.__tp_button = False
        self.settings = settings
        self.__settings_check()
        
        # イベント発生用のコールバック関数をセット
        self.callback_send = callback_send

        # PICスロット初期化
        self.__board.pic_slot_init()

    def serial_write(self, slot, vals):
        """ Serial書き込み
            slot : 'S01' ~ 'S10'
            vals : 書き込みデータ
            戻り : なし
        """
        # slot選択
        slot_num = tpUtils.slot_str_to_int(slot)

        # Serial書き込み
        self.__board.serial_write(slot_num, vals)

        return

    def analog_read(self, slot, line):
        """ GPIO アナログ値読み出し
            slot : 'S01' ~ 'S10'
            line : 'A' ~ 'D'
            戻り : analog値
        """
        slot_num = tpUtils.slot_str_to_int(slot)
        line_num = tpUtils.line_str_to_int(line)
        dat = 0

        if self.__board_kind == 'P1':
            # P1には機能なし
            return
        elif self.__board_kind == 'P2':
            dat = self.__board.analog_read(slot_num, line_num)
        else: # P3
            dat = self.__board.analog_read(slot_num, line_num)

        return dat

    def gpio_in_out_init(self, slot, line, kind):
        """ GPIO実行時で設定
            slot : 1 ~ 10
            line : 'A' ~ 'D'
            kind : 0 ~ 4(NONE/ANALOG/IN/OUT_OD/OUT)
            戻り : なし
        """
        #print('gpio_in_out_init', slot, line, kind)
        slot_num = tpUtils.slot_str_to_int(slot)
        line_num = tpUtils.line_str_to_int(line)
        self.__board.gpio_in_out_init(slot_num, line_num, kind)
        return

    def gpio_read(self, slot, line):
        """ GPIO読み出し
            slot : 'S01' ~ 'S10'
            line : 'A' ~ 'D'
            戻り : 0 or 1 (Low or High)
        """
        slot_num = tpUtils.slot_str_to_int(slot)
        line_num = tpUtils.line_str_to_int(line)
        dat = 0

        if self.__board_kind == 'P1':
            self.i2c_lock.acquire(1)
            dat = self.__board.gpio_read(slot_num, line_num)
            self.i2c_lock.release()
        elif self.__board_kind == 'P2':
            #self.spi_lock.acquire(1) # P2はtpP2Interface内部で排他制御
            dat = self.__board.gpio_read(slot_num, line_num)
            #self.spi_lock.release()
        else: # P3
            dat = self.__board.gpio_read(slot_num, line_num)

        return dat

    def gpio_write(self, slot, line, val):
        """ GPIO書き込み
            slot : 'S01' ~ 'S10'
            line : 'A' ~ 'D'
            val  : '0' or '1' (Low or High)
            戻り : なし
        """
        slot_num = tpUtils.slot_str_to_int(slot)
        line_num = tpUtils.line_str_to_int(line)

        if self.__board_kind == 'P1':
            self.i2c_lock.acquire(1)
            self.__board.gpio_write(slot_num, line_num, int(val))
            self.i2c_lock.release()
        elif self.__board_kind == 'P2':
            #self.spi_lock.acquire(1) # P2はtpP2Interface内部で排他制御
            self.__board.gpio_write(slot_num, line_num, int(val))
            #self.spi_lock.release()
        else: # P3
            self.__board.gpio_write(slot_num, line_num, int(val))
        return

    def spi_access(self, slot, address, vals):
        """ SPI書き込み・読み出し
            slot    : 'S01' ~ 'S10', 'S00'はPICだが、隠し機能
            address : レジスタアドレス 
            vals    : 書き込みデータ, 読み込み時はdummy
            戻り    : 読み込みデータ
        """
        # slot選択
        slot_num = tpUtils.slot_str_to_int(slot)

        # P1は以外はtpPxInterface内部で排他制御
        if self.__board_kind == 'P1': self.spi_lock.acquire(1)

        # SPI情報取得
        mode = 0
        speed = 0
        endian = 0
        for elem in self.settings:
            if elem['slot'] != slot: continue
            setting = elem['settings']
            mode = int(setting['mode']) 
            speed = int(setting['speed'])
            endian = int(setting['endian'])
            break

        # SPIアクセス
        data = self.__board.spi_access(slot_num, mode, speed, endian, 0, address, vals)

        # P1は以外はtpPxInterface内部で排他制御
        if self.__board_kind == 'P1': self.spi_lock.release()

        return data

    def tp22_temp(self, slot):
        """ Tibbit#22, RTD読み出し
            slot : 'S01' ~ 'S10'
            戻り : C戻り値、温度生データ
        """
        slot_num = tpUtils.slot_str_to_int(slot)
        self.i2c_lock.acquire(1)
        try:
            self.__board.i2c_select(slot_num)
            c_ret, data = self.__board.tp22_temp()
        except:
            raise
        finally:
            self.__board.i2c_select() # slot選択解除
            self.i2c_lock.release()
        return c_ret, data

    def i2c_read_tp22(self, slot, num):
        """ Tibbit#22, I2C読み出し
            slot : 'S01' ~ 'S10'
            num  : 読み込みbyte数
            戻り : i2cデータ
        """
        slot_num = tpUtils.slot_str_to_int(slot)
        self.i2c_lock.acquire(1)
        try:
            self.__board.i2c_select(slot_num)
            data = self.__board.i2c_read_tp22(num)
        except:
            raise
        finally:
            self.__board.i2c_select() # slot選択解除
            self.i2c_lock.release()
        return data

    def i2c_write_tp22(self, slot, val):
        """ Tibbit#22, I2C書き込み
            slot : 'S01' ~ 'S10'
            val  : 書き込みデータ、1byteのみ
            戻り : なし
        """
        slot_num = tpUtils.slot_str_to_int(slot)
        self.i2c_lock.acquire(1)
        try:
            self.__board.i2c_select(slot_num)
            self.__board.i2c_write_tp22(val)
        except:
            raise
        finally:
            self.__board.i2c_select() # slot選択解除
            self.i2c_lock.release()
        return

    def tpFPGA_write(self, slot, file_path):
        """ FPGA Tibbit(#26,57), FPGAリセット＆書き込み
            slot      : 'S01' ~ 'S10'
            file_path : binイメージのファイル名フルパス
            戻り : なし
        """
        slot_num = tpUtils.slot_str_to_int(slot)
        self.__board.tpFPGA_write(slot_num, file_path)
        return

    def tp26_start_record(self, slot):
        """ #26 記録開始
            slot : 'S01' ~ 'S10'
            戻り : なし
        """
        slot_num = tpUtils.slot_str_to_int(slot)
        self.__board.tp26_start_record(slot_num)
        return

    def tp26_get_record(self, slot):
        """ #26 記録読み込み
            slot : 'S01' ~ 'S10'
            戻り : byte配列
        """
        slot_num = tpUtils.slot_str_to_int(slot)
        return self.__board.tp26_get_record(slot_num)

    def tp26_put_play(self, slot, vals):
        """ #26 記録書き込み
            slot : 'S01' ~ 'S10'
            vals : 記録したバイナリ配列
            戻り : なし
        """
        slot_num = tpUtils.slot_str_to_int(slot)
        self.__board.tp26_put_play(slot_num, vals)
        return

    def tp26_start_play(self, slot):
        """ #26 再生開始
            slot : 'S01' ~ 'S10'
            戻り : なし
        """
        slot_num = tpUtils.slot_str_to_int(slot)
        self.__board.tp26_start_play(slot_num)
        return

    def i2c_read(self, slot, address, num):
        """ I2C読み出し(cmdなし)
            slot    : 'S01' ~ 'S10'
            address : I2Cアドレス
            num     : 読み込みbyte数
            戻り    : i2cデータ
        """
        slot_num = tpUtils.slot_str_to_int(slot)

        self.i2c_lock.acquire(1)
        try:
            self.__board.i2c_select(slot_num)
            data = self.__board.i2c_read(address, -1, num)
        except:
            raise
        finally:
            self.__board.i2c_select() # slot選択解除
            self.i2c_lock.release()
        return data

    def i2c_read_with_cmd(self, slot, address, cmd, num):
        """ I2C読み出し
            slot    : 'S01' ~ 'S10'
            address : I2Cアドレス
            cmd     : 読み込み時コマンド（1byte）
            num     : 読み込みbyte数
            戻り    : i2cデータ
        """
        slot_num = tpUtils.slot_str_to_int(slot)

        self.i2c_lock.acquire(1)
        try:
            self.__board.i2c_select(slot_num)
            data = self.__board.i2c_read(address, cmd, num)
        except:
            raise
        finally:
            self.__board.i2c_select() # slot選択解除
            self.i2c_lock.release()
        return data

    def i2c_write(self, slot, address, vals):
        """ I2C書き込み(cmdなし)
            slot    : 'S01' ~ 'S10'
            address : I2Cアドレス
            vals    : 書き込みデータ、1 or 2 byte
            戻り    : なし
        """
        slot_num = tpUtils.slot_str_to_int(slot)
        if len(vals) != 1 and len(vals) != 2:
            raise ValueError('I2C write data number error! : ' + str(len(vals)))

        self.i2c_lock.acquire(1)
        try:
            self.__board.i2c_select(slot_num)
            if len(vals) == 1:
                self.__board.i2c_write_1byte(address, vals[0])
            else: # 2byte
                self.__board.i2c_write_2byte(address, vals[0], vals[1])
        except:
            raise
        finally:
            self.__board.i2c_select() # slot選択解除
            self.i2c_lock.release()
        return

    def i2c_write_with_cmd(self, slot, address, cmd, vals):
        """ I2Cブロック書き込み、コマンド付き
            slot    : 'S01' ~ 'S10'
            address : I2Cアドレス
            cmd     : コマンド
            vals    : 書き込みデータ、リスト
            戻り    : なし
        """
        slot_num = tpUtils.slot_str_to_int(slot)
        self.i2c_lock.acquire(1)
        try:
            self.__board.i2c_select(slot_num)
            self.__board.i2c_write_block_data(address, cmd, vals)
        except:
            raise
        finally:
            self.__board.i2c_select() # slot選択解除
            self.i2c_lock.release()
        return

    def rp_buzzer(self, time_msec, pattern):
        """ ボードブザー鳴動
            time_msec : 鳴らす時間
            pattern   : パターン
            戻り      : なし
        """
        time_msec_int = int(time_msec) if type(time_msec) is str else time_msec
        pattern_int = int(pattern) if type(pattern) is str else pattern
        self.__buzzer_set(time_msec_int, pattern_int)
        return

    def rp_led(self, num, val):
        """ ボードLED制御
            num : LED番号
            val : 1/0, 1=On
            戻り: なし
        """
        num_int = int(num) if type(num) is str else num
        val_int = int(val) if type(val) is str else val
        if num_int >= 1 and num_int <= 4:
            self.__board.rp_led(num_int, val_int)
        else:
            raise ValueError('Board LED number error! 1~4 : ' + str(num_int))
        return

    def get_pic_fw_ver(self):
        """ PICのFWのバージョンを返す
            戻り : FWのバージョン（数値）
        """
        return self.__board.get_pic_fw_ver()

    # 内部メソッド ---

    def __tp52_init(self, setting):
        """ tibbit #52設定
            setting : self.settingsの要素
            戻り    : なし
        """
        slot_num = tpUtils.slot_str_to_int(setting['slot'])
        self.__board.tp52_init(slot_num)

    def __tp22_init(self, setting):
        """ tibbit #22設定
            setting : self.settingsの要素
            戻り    : なし
        """
        slot_num = tpUtils.slot_str_to_int(setting['slot'])
        self.__board.tp22_init(slot_num)

    def __spi_init(self, setting):
        """ tibbit SPI設定
            setting : self.settingsの要素
            戻り    : なし
        """
        slot_num = tpUtils.slot_str_to_int(setting['slot'])
        # 通信情報設定
        kbaud = setting['settings']['speed']
        kbaud_num = int(kbaud)
        self.__board.spi_init(slot_num, kbaud_num)

    def __i2c_init(self, setting):
        """ tibbit I2C設定
            setting : self.settingsの要素
            戻り    : なし
        """
        slot_num = tpUtils.slot_str_to_int(setting['slot'])
        # 通信情報設定
        kbaud = setting['settings']['baudRateK']
        #print(slot_num, kbaud)
        kbaud_num = int(kbaud)
        self.__board.i2c_init(slot_num, kbaud_num)
        return

    def __serial_init(self, setting):
        """ tibbit Seral設定
            setting : self.settingsの要素
            戻り    : なし
        """
        slot_num = tpUtils.slot_str_to_int(setting['slot'])
        if slot_num % 2 == 0: # 奇数slotのみ対応
            raise ValueError('Serial slot error! : ' + str(slot_num))
        try:
            # 通信情報設定
            baud = setting['settings']['baudRate']
            flow = setting['settings']['hardwareFlow']
            parity = setting['settings']['parity']
            sep_kind = setting['settings']['splitInput']
            sep_char = setting['settings']['onTheCharactor']
            sep_time = setting['settings']['afterATimeoutOf']
            sep_leng = setting['settings']['intoFixedLengthOf']
        except Exception:
            # 設定エラー
            raise tpUtils.TpCheckError('Please check the serial setting.')

        #print(slot_num, baud, flow, parity, sep_char, sep_time, sep_leng)
        baud_num = int(baud)
        flow_num = 1 if flow == 'on' else 0
        parity_num = 0 if parity == 'none' else 1 if parity == 'odd' else 2
        self.__board.serial_init(
                self.__serial_event_callback, 
                slot_num, 
                baud_num, 
                flow_num, 
                parity_num)

        # 受信用情報確保
        pos = int((slot_num - 1) / 2)
        if sep_kind == '1':
            self.__serial_info[pos]['recv_kind'] = 'CHAR'
            self.__serial_info[pos]['char'] = sep_char
        elif sep_kind == '2':
            self.__serial_info[pos]['recv_kind'] = 'TIME'
            self.__serial_info[pos]['time'] = int(sep_time)
            self.__serial_info[pos]['lock'] = thread.allocate_lock()
            thread.start_new_thread(self.__serial_recv_time_thread, (slot_num, int(sep_time)))
        elif sep_kind == '3':
            self.__serial_info[pos]['recv_kind'] = 'LENG'
            self.__serial_info[pos]['leng'] = int(sep_leng)
        else:
            self.__serial_info[pos]['recv_kind'] = 'NONE'
        #print(self.__serial_info)
        return

    #def serial_event_callback_test(self, slot, val):
    #    self.__serial_event_callback(slot, val)
    def __serial_event_callback(self, slot, val):
        #print(tpUtils.slot_int_to_str(slot), send_data)

        # いったん、バッファへ受信データ格納
        pos = int((slot - 1) / 2)
        kind = self.__serial_info[pos]['recv_kind']
        try:
            if kind == 'TIME' : # 時間区切り
                self.__serial_info[pos]['lock'].acquire(1)
            self.__serial_recv_buf[pos].extend(val)
        except:
            raise
        finally:
            if kind == 'TIME' : # 時間区切り
                self.__serial_info[pos]['lock'].release()

        # 受信方法による振り分け
        if kind == 'CHAR' : # 文字区切り
            char = self.__serial_info[pos]['char']
            self.__serial_recv_char(slot, char)
        elif kind == 'TIME' : # 時間区切り
            pass # 別スレッドで対応
        elif kind == 'LENG' : # 固定長区切り
            leng = self.__serial_info[pos]['leng']
            self.__serial_recv_leng(slot, leng)
        else: # 区切りなし
            send_data = self.__serial_recv_buf[pos][:] # 実copy
            #print(tpUtils.slot_int_to_str(slot), send_data, self.__serial_recv_buf)
            self.__serial_recv_buf[pos].clear()
            self.callback_send(tpUtils.slot_int_to_str(slot), Serial, json.dumps(send_data))

    def __serial_recv_char(self, slot, char):
        """Serial受信文字区切り
        """
        #print('__serial_recv_char', slot, char, len(char))
        pos = int((slot - 1) / 2)
        if ord(char) in self.__serial_recv_buf[pos]:
            buf_pos = self.__serial_recv_buf[pos].index(ord(char))
            send_data = self.__serial_recv_buf[pos][:buf_pos + 1] # 区切り文字含め、実copy
            #print(tpUtils.slot_int_to_str(slot), send_data, self.__serial_recv_buf)
            del self.__serial_recv_buf[pos][:buf_pos + 1]
            self.callback_send(tpUtils.slot_int_to_str(slot), Serial, json.dumps(send_data))

    def __serial_recv_leng(self, slot, leng):
        """Serial受信固定長区切り
        """
        pos = int((slot - 1) / 2)
        while len(self.__serial_recv_buf[pos]):
            if len(self.__serial_recv_buf[pos]) <= leng:
                break
            else:
                send_data = self.__serial_recv_buf[pos][:leng] # 実copy
                del self.__serial_recv_buf[pos][:leng]
            #print(tpUtils.slot_int_to_str(slot), send_data, self.__serial_recv_buf)
            self.callback_send(tpUtils.slot_int_to_str(slot), Serial, json.dumps(send_data))

    def __serial_recv_time_thread(self, slot, time_ms):
        """Serial受信時間区切り
        """
        pos = int((slot - 1) / 2)
        while True:
            time.sleep(time_ms / 1000)
            if len(self.__serial_recv_buf[pos]):
                send_data = self.__serial_recv_buf[pos][:] # 実copy
                self.__serial_recv_buf[pos].clear()
                #print(tpUtils.slot_int_to_str(slot), send_data, self.__serial_recv_buf)
                self.callback_send(tpUtils.slot_int_to_str(slot), Serial, json.dumps(send_data))

    def __gpio_init(self, setting):
        """ tibbit GPIO設定、入力変化時のみ抜出
            setting : self.settingsの要素
            戻り    : なし
        """
        slot_num = tpUtils.slot_str_to_int(setting['slot'])
        for pin in setting['pin']:
            #print(pin)
            if pin['status'] == 'IN' and 'edge' in pin:
                if pin['edge'] == 'on':
                    line_num = tpUtils.line_str_to_int(pin['name'])
                    self.__board.gpio_event_init(self.__gpio_event_callback, slot_num, line_num)
            if pin['status'] == 'IN':
                line_num = tpUtils.line_str_to_int(pin['name'])
                self.__board.gpio_init(slot_num, line_num, LINE_SETTING_D_IN)
            elif pin['status'] == 'OUT_OD':
                line_num = tpUtils.line_str_to_int(pin['name'])
                self.__board.gpio_init(slot_num, line_num, LINE_SETTING_D_OUT_OD)
            elif pin['status'] == 'OUT':
                line_num = tpUtils.line_str_to_int(pin['name'])
                self.__board.gpio_init(slot_num, line_num, LINE_SETTING_D_OUT)
            elif pin['status'] == 'IN_Analog':
                line_num = tpUtils.line_str_to_int(pin['name'])
                self.__board.gpio_init(slot_num, line_num, LINE_SETTING_A_IN)
        return

    def gpio_event_init(self, slot, line):
         self.__board.gpio_event_init(self.__gpio_event_callback, slot, line)
    def __gpio_event_callback(self, slot, line, on):
        send_data = {'line': tpUtils.line_int_to_str(line), 'v': on}
        #print(tpUtils.slot_int_to_str(slot), send_data)
        self.callback_send(tpUtils.slot_int_to_str(slot), GPIO, json.dumps(send_data))
       
    #def rp_button_init(self):
    #    self.__rp_button_init()
    def __rp_button_init(self):
        """ 基板ボタン使用時、callback等初期化
            戻り    : なし
        """
        self.__board.rp_button_init(self.__rp_button_callback)
        return

    def __rp_button_callback(self, kind, on):
        if kind == 'RST':
            send_data = {'btn': 1, 'v': on}
        else: # MD
            send_data = {'btn': 2, 'v': on}
        #print(send_data)
        self.callback_send('S00', TP_BUTTON, json.dumps(send_data))
        return
       
    def __settings_check(self):
        for setting in self.settings:
            if 'comm' not in setting: continue
            #print(setting['comm'])
            if setting['comm'] == TP_BUTTON:
                # 基板ボタン用設定
                self.__rp_button_init()
            elif setting['comm'] == TP_BUZZER:
                # BUZZERパターン動作用thread設定
                self.__buzzer_init()
            elif setting['comm'] == GPIO:
                # tibbit GPIO用設定
                self.__gpio_init(setting)
            elif setting['comm'] == Serial:
                # tibbit Serial用設定
                self.__serial_init(setting)
            elif setting['comm'] == I2C:
                # tibbit I2C用設定
                self.__i2c_init(setting)
            elif setting['comm'] == SPI:
                # tibbit SPI用設定
                self.__spi_init(setting)
            elif setting['comm'] == 'TP22':
                # tibbit #22用設定
                self.__tp22_init(setting)
            elif setting['comm'] == 'TP52':
                # tibbit #52用設定
                self.__tp52_init(setting)
        return

    def __buzzer_init(self):
        self.__buzzer_table = [ # 鳴動パターン用テーブル
                [0, 0],
                [0, 1],
                [1, 1],
                [0.5, 0.5],
                [0.2, 0.2],
                [0.1, 0.1],
                [0.1, 0.9]]
        self.__buzzer_stop_time = 0
        self.__buzzer_run_flg = False
        self.__buzzer_on_flg = False
        thread.start_new_thread(self.__buzzer_thread, ())
        return

    def __buzzer_set(self, time_msec, pattern):
        self.__buzzer_time_on = 0
        self.__buzzer_time_off = 0
        if pattern == 0: # 強制停止
            self.__board.rp_buzzer(0)
            self.__buzzer_run_flg = False
        elif pattern == 1: # 連続On
            self.__board.rp_buzzer(1)
            self.__buzzer_run_flg = False
        elif pattern <= 6: 
            self.__buzzer_time_on = self.__buzzer_table[pattern][0]
            self.__buzzer_time_off = self.__buzzer_table[pattern][1]
            self.__buzzer_run_flg = True
            self.__buzzer_on_flg = True
        else: # エラー
            self.__board.rp_buzzer(0)
            self.__buzzer_run_flg = False
            raise ValueError('Buzzer pattern error! 0~6 : ' + str(pattern))

        if time_msec == 0:
            self.__buzzer_stop_time = 0
        else:
            self.__buzzer_stop_time = time.time() + time_msec / 1000
        return

    def __buzzer_thread(self):
        while(True):
            time.sleep(0.01)
            #print(self.__buzzer_run_flg, self.__buzzer_on_flg)

            # 時間確認
            if self.__buzzer_stop_time == 0:
                pass
            else:
                if time.time() >= self.__buzzer_stop_time:
                    self.__board.rp_buzzer(0)
                    self.__buzzer_stop_time = 0
                    self.__buzzer_run_flg = False

            # On/Off動作
            if self.__buzzer_run_flg == False:
                pass
            else:
                if self.__buzzer_on_flg:
                    #print('ON')
                    self.__board.rp_buzzer(1)
                    time.sleep(self.__buzzer_time_on)
                    self.__buzzer_on_flg = False
                else:
                    #print('OFF')
                    self.__board.rp_buzzer(0)
                    time.sleep(self.__buzzer_time_off)
                    self.__buzzer_on_flg = True

