#!/usr/bin/python3
"""P3用プログラム
   インターフェース部クラス
"""
gTpEnv = True # 環境チェック, TrueでTibbo-Piとみなす
import os, sys
import _thread as thread
import time
import ctypes
try:
    import RPi.GPIO as GPIO
except:
    gTpEnv = False
import tpUtils
import subprocess

# 定数宣言 ---------------------------------------------------------------
SLOT_SETTING_NONE = 0x00
SLOT_SETTING_SERI = 0x01
SLOT_SETTING_SERI_FLOW = 0x02
SLOT_SETTING_I2C  = 0x03
SLOT_SETTING_SPI  = 0x04
LINE_SETTING_NONE     = 0
LINE_SETTING_A_IN     = 1
LINE_SETTING_D_IN     = 2
LINE_SETTING_D_OUT_OD = 3 # オープンドレイン
LINE_SETTING_D_OUT    = 4 # TTL

SPI_WAIT = 0.01 # SPIアクセス後のwait秒
CHECK_WAIT = 0.01 # GPIO edge, Serial イベントの定期チェックwait秒 
PIC_RST_CMD = 0xA0
PIC_WRITE_ADDR = 0x80

PIC_READ_THREAD_WAIT = 0.1 # PICのレジスタread thread wait秒 

PIC_NODE_RED_DIR = os.path.dirname(os.path.abspath(__file__)) + '/../'
PIC_FW_VER_DIR = PIC_NODE_RED_DIR + 'py/fw/'
PIC_FW_FILE = 'P3.*.hex'
PIC_FW_FLG_FILE = PIC_NODE_RED_DIR + 'tp_file/tibbo_pi_pic_fw_'
PIC_PICBERRY = 'picberry/picberry'
PIC_FW_UPDATE_SH = 'board_fw_update.sh'
PIC_INIT_LED_WIAT = 1

SPI_RETRY_NUM = 10
I2C_RETRY_NUM = 10

# クラス宣言 -------------------------------------------------------------
class TpP3Interface():
    global gTpEnv

    def __init__(self):
        """ コンストラクタ
        """
        if gTpEnv: # Tibbo-Pi環境（以下全メソッドで同様）
            # 排他処理用設定
            self.__gpio_lock = thread.allocate_lock()
            self.__line_lock = thread.allocate_lock()
            self.__subp_lock = thread.allocate_lock()

            # ハードウェア設定
            GPIO.setmode(GPIO.BCM)
            self.__path = os.path.dirname(os.path.abspath(__file__))
            subprocess.call(['/bin/sh', self.__path + '/ch.sh', PIC_FW_VER_DIR + PIC_PICBERRY])
            subprocess.call(['/bin/sh', self.__path + '/ch.sh', PIC_FW_VER_DIR + PIC_FW_UPDATE_SH])

            # パラメータ定義
            self.__gpio_in_edge_table = []
            self.__spi_cs_table = [25, 8, 5, 7]	
            self.__serial_int_table = [19, 16, 26, 20, 21]	
            self.__ex_gpio_int_table = [13]	
            self.__rp_led_table = [17, 18, 27, 22]	
            self.__kind_table = [[0, 0, 0, 0] for i in range(10)]
            self.gpio_event_callback = None
            self.serial_event_callback = None

            # PIC用SPI設定
            self.__pic_spi_mode = 0x03
            self.__pic_spi_khz = 250
            self.__pic_spi_endian = 1
            self.__pic_spi_wait_ms = 0

            # Tibbit#22用設定
            self.__tp22_addr = 0x0D
            self.__tp22_kbaud = 10

            # i2c設定
            self.__i2c_kbaud_list = [100] * 11 # 0 = slot未選択時, default 100Kbps
            self.__i2c_kbaud = 0 # アクセス時書き換え用



            # P3用設定 ---------

            self.pic_fw_ver = 0 # PIC-FWのバージョンを格納, 0は未定

            self.p3_flg = 2 # 0:P2, 1:line_setのみP3, 2:全部P3

            #     PICアクセス
            self.__spi_init_write_buf = [0] * 0x29 # アドレス0x01～0x28使用
            self.__spi_write_buf = [[0] * 0x2E] * 2 # アドレス0x29～0x2D 2面使用
            self.__spi_write_buf_side = 0 # 0 or 1,  アクセス中なら、この値の逆サイド利用
            self.__spi_write_buf_flg = [0] * 0x2E # アドレス0x29～0x2D 使用, 1でwriteあり
            self.__spi_write_buf_flg_lock = thread.allocate_lock()
            self.__spi_write_start_addr = 0x29 
            self.__spi_write_end_addr = 0x2D 
            self.__spi_write_buf_lock = thread.allocate_lock()
            self.__spi_read_buf = [[0] * 0x65] * 2 # アドレス0x29～0x64 2面使用
            self.__spi_read_buf_side = 0 # 0 or 1,  アクセス中なら、この値の逆サイド利用
            self.__spi_read_buf_start = 0 # bufferへの取得開始時刻
            self.__spi_read_start_addr = 0x29 
            self.__spi_read_end_addr = 0x64 # slot数で処理時間がかわるのを防ぐため、毎回最大スロットを読み込む
            self.__spi_read_buf_lock = thread.allocate_lock()

            #     I2Cアクセス
            self.__i2c_buf = ctypes.create_string_buffer(b'\000' * 1024 * 16)
            self.__i2c_write_lib = ctypes.cdll.LoadLibrary(self.__path + '/c/libi2c_write.so')
            self.__i2c_read_lib = ctypes.cdll.LoadLibrary(self.__path + '/c/libi2c_read.so')
            self.__tp22_temp_lib = ctypes.cdll.LoadLibrary(self.__path + '/c/libtp22_temp.so')
            self.__i2c_read_tp22_lib = ctypes.cdll.LoadLibrary(self.__path + '/c/libi2c_read_tp22.so')
            self.__i2c_write_tp22_lib = ctypes.cdll.LoadLibrary(self.__path + '/c/libi2c_write_tp22.so')
            #     SPIアクセス
            self.__spi_buf = ctypes.create_string_buffer(b'\000' * 1024 * 64)
            self.__spi_access_lib = ctypes.cdll.LoadLibrary(self.__path + '/c/libspi_access.so')
            self.__fpga_lattice_lib = ctypes.cdll.LoadLibrary(self.__path + '/c/libfpga_lattice.so')

        else: # 非Tibbo-Pi環境（以下全メソッドで同様, dummy値を返すこともあり）
            pass

    def pic_slot_init(self):
        """ PICスロット初期設定
            戻り: なし
        """
        if gTpEnv and self.p3_flg > 0:
            # GPIO OUT High固定用設定
            out_init = [0xFF] * 5
            self.__pic_spi_access(PIC_WRITE_ADDR + 0x29, out_init, False) # buffer更新
            self.__pic_spi_access(PIC_WRITE_ADDR + 0x29, out_init, True)  # PIC更新
            # PICへ書き込み
            #print(list(map(hex,self.__spi_init_write_buf[0x01:0x29])))
            self.__pic_spi_access(PIC_WRITE_ADDR + 0x01, self.__spi_init_write_buf[0x01:0x29])
            #self.dbg_pic_reg_print(0x00, 0x29)
            # SPI読み込みスレッド開始
            if self.p3_flg == 2:
                thread.start_new_thread(self.__spi_access_thread, ())
            time.sleep(1) # thread安定待ち
        return

    def i2c_check_before_init(self):
        """ I2Cが固まってないか確認する
            board_initの前にチェックすること
        """
        if gTpEnv:
            self.__subp_lock.acquire(1)
            try:
                sub = subprocess.Popen('i2cdetect -y 1',
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True)
                ret = sub.wait()
                ret_bin = sub.stdout.readlines()
                ret_str = str(ret_bin[-1])[2:-3]
            except:
                raise tpUtils.TpCheckError('Fatal Error! initial I2C access error')
            finally:
                self.__subp_lock.release()
            if ret_str.find('70 71 --') == -1:
                raise tpUtils.TpCheckError('Fatal Error! initial I2C access error ' + ret_str)
        return

    def board_init(self):
        """ 基板初期化
            戻り: なし
        """
        if gTpEnv:
            GPIO.setwarnings(False)
            self.__rp_gpio_init()
            self.i2c_select(0)
            # PIC初期化
            self.__pic_spi_access(PIC_WRITE_ADDR, [PIC_RST_CMD])
            time.sleep(PIC_INIT_LED_WIAT) # P3 PIC起動時LED点滅待ち
        return

    def spi_lock_init(self, lock):
        """ SPI Lock初期化
            lock : SPIアクセス時thread lock
            戻り : なし
        """
        self.__spi_lock = lock
        return

    def spi_init(self, slot, kbaud):
        """ SPI初期化
            slot  : 1 ~ 10
            kbaud : 通信速度
            戻り  : なし
        """
        #print('spi_init', slot, kbaud)
        self.__slot_set_p3(slot, SLOT_SETTING_SPI)
        return

    def i2c_init(self, slot, kbaud):
        """ I2C初期化
            slot  : 1 ~ 10
            kbaud : 通信速度
            戻り  : なし
        """
        #print('i2c_init', slot, kbaud)
        self.__i2c_kbaud_list[slot] = kbaud
        self.__slot_set_p3(slot, SLOT_SETTING_I2C)
        return

    def serial_init(self, callback, slot, baud, flow, parity):
        """ Serial初期化
            callback : Serial割り込み発生時のcallback関数
            slot     : 1 ~ 10
            baud     : 通信速度
            flow     : フロー制御0=なし、1=あり
            parity   : パリティ0=なし、1=奇数、2=偶数
            戻り     : なし
        """
        #print('serial_init', callback, slot, baud, flow, parity)
        if slot % 2 == 0: return # 奇数slotのみ対応
        if gTpEnv:
            # PIC設定
            addr = (slot - 1) + 0x01 
            data = self.__serial_data(baud, flow, parity)
            if self.p3_flg > 0:
                if flow == 0:
                    self.__slot_set_p3(slot, SLOT_SETTING_SERI)
                else:
                    self.__slot_set_p3(slot, SLOT_SETTING_SERI_FLOW)
                self.__spi_init_write_buf[addr] = data
            else:
                self.__slot_set(slot, SLOT_SETTING_SERI)
                self.__pic_spi_access(PIC_WRITE_ADDR + addr, [data])
            # 受信時callback設定
            if self.serial_event_callback is None:
                self.serial_event_callback = callback
                # 取りこぼしが発生するのでevent登録ではなくloopで処理する
                thread.start_new_thread(self.__check_serial_thread, ())

    def read_pic_fw_ver(self, fatal_flg):
        """ PICのFWバージョンを読み込む
            fatal_flg : error時、例外を発生するかのフラグ
            戻り      : PICのFWバージョン, read失敗なら-1, 未定なら0
        """
        self.pic_fw_ver = 0 # FW初期化、0なら未定ということ
        if gTpEnv == False: return 0
        count = 0
        while True:
            try:
                ret = self.__pic_spi_access(0x00, [0], True)[0]
            except:
                ret = -1
            finally:
                if ret > 0 and ret < 32: 
                    self.pic_fw_ver = ret
                    break # バージョンは1～31
                count += 1
                if count >= 10:
                    if fatal_flg:
                        raise tpUtils.TpCheckError('Fatal Error! Illegal Board FW version info = ' + str(ret))
                    else:
                        self.pic_fw_ver = -1
                        return self.pic_fw_ver
        #print('count =', count)
        return self.pic_fw_ver

    def get_pic_fw_ver(self):
        """ PICのFWのバージョンを返す
            戻り : FWのバージョン（数値）
        """
        return self.pic_fw_ver

    def check_pic_fw(self):
        """ PICのFWバージョンをチェックし、古ければ更新する
            戻り: なし
        """
        if gTpEnv == False: return

        # fileよりバージョンチェック
        try:
            sub = subprocess.Popen('ls {0}'.format(PIC_FW_VER_DIR + PIC_FW_FILE),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True)
            ret = sub.wait()
            ret_bin = sub.stdout.readlines()
            hex_file_path = str(ret_bin[0])[2:-3]
            hex_file = os.path.split(hex_file_path)[1]
            chk_ver = int(hex_file.split('.')[1])
        except:
            return # 更新該当ファイル取得できない場合は何もしない。

        # フラグファイルチェック
        sub = subprocess.Popen('ls {0}'.format(PIC_FW_FLG_FILE + str(chk_ver)),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True)
        ret = sub.wait()
        ret_bin = sub.stdout.readlines()
        if len(ret_bin) != 0: return # 該当フラグファイルある場合なにもしない

        # FW バージョンチェック
        fw_ver = self.read_pic_fw_ver(False)
        if fw_ver > 0: # FW正常時
            if chk_ver == fw_ver: # 同じバージョンでフラグファイルないならつくる
                sub = subprocess.Popen('touch {0}'.format(PIC_FW_FLG_FILE + str(chk_ver)),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True)
                ret = sub.wait()
                return
        self.__pic_fw_update(chk_ver, hex_file_path)
        return

    def serial_write(self, slot, vals):
        """ Serial書き込み
            slot : 1 ~ 10
            vals : データリスト
            戻り : なし
        """
        #print('serial_write', slot, list(map(hex, vals)))
        vals = [b for b in vals]
        
        if slot % 2 == 0: return # 奇数slotのみ対応
        pos = int((slot - 1) / 2)
        if gTpEnv:
            num_addr = pos + 0x6F
            dat_addr = pos + 0x79 + PIC_WRITE_ADDR
            while len(vals):
                dmy = [0]
                buff_num = 250 - self.__pic_spi_access(num_addr, dmy)[0]
                #print('buff_num =', buff_num, len(vals))
                if buff_num >= len(vals):
                    self.__pic_spi_access(dat_addr, vals)
                    vals.clear()
                elif buff_num <= 0: # バッファあふれならwait
                    time.sleep(0.01)
                else:
                    self.__pic_spi_access(dat_addr, vals[:buff_num])
                    del vals[:buff_num]
        return

    def spi_access(self, slot, mode, speed, endian, wait_ms, address, vals, no_use_buf_flg = False):
        """ SPI書き込み・読み出し
            slot    : 0 ~ 10, 0=PIC
            mode    : SPIモード, 0~3
            speed   : SPI速度, ~500KHz
            endian  : bit endian, 1=big(bit7から), 0=little(bit0から)
            wait_ms : address書き込み後のwait, PICでは1ms以上必要
            address : レジスタアドレス
            vals    : 書き込みデータ（リスト）
            no_use_buf_flg : bufferアクセスせずに直接PICへアクセス
            戻り    : PICからの読み込み値
        """
        #print('spi_access', slot, mode, speed, endian, wait_ms, hex(address), vals, no_use_buf_flg)
        data = vals[:] # 実コピー
        if gTpEnv:
            if self.p3_flg == 2 and no_use_buf_flg == False:
                #print('spi_access', slot, mode, speed, endian, wait_ms, hex(address), vals, no_use_buf_flg)
                if address >= self.__spi_read_start_addr and address <= self.__spi_read_end_addr:
                    #print('spi_access read_buf', slot, mode, speed, endian, wait_ms, hex(address), vals, no_use_buf_flg)
                    return self.__spi_read_buf_read(address, vals)
                elif (address - PIC_WRITE_ADDR) >= self.__spi_write_start_addr and (address - PIC_WRITE_ADDR) <= self.__spi_write_end_addr:
                    #print('spi_access write_buf', slot, mode, speed, endian, wait_ms, hex(address), vals, no_use_buf_flg)
                    return self.__spi_write_buf_write(address - PIC_WRITE_ADDR, vals)

            #print('spi_access', slot, mode, speed, endian, wait_ms, hex(address), list(map(hex, vals)), no_use_buf_flg)

            dat_str = ''
            for elem in data: dat_str += 'x' + format(int(elem), '02x')
            #print(dat_str)
            self.__subp_lock.acquire(1)
            try:
                c_ret = self.__spi_access_lib.spi_access(mode, speed, endian, address, wait_ms, slot, len(data), dat_str.encode('utf-8'), self.__spi_buf)
                ret_str = str(repr(self.__spi_buf.value))[2:-1]
                #print('spi_access', slot, mode, speed, endian, wait_ms, hex(address), list(map(hex, vals)), ret_str)
            except:
                raise
            finally:
                self.__subp_lock.release()
            #print(c_ret)
            if c_ret != 0:
                raise ValueError('SPI access error! : c_ret = ' + str(c_ret))
            ret_str_sep = ret_str.split(',')
            ret = []
            for elem in ret_str_sep:
                ret.append(int(elem[2:], 16)) 
            #print('spi_access', ret)
            return ret
        else:
            return data

    def gpio_event_init(self, callback, slot, line):
        """ ダイレクトGPIO入力event用設定
            callback : GPIO入力割り込み発生時のcallback関数
            slot     : 1 ~ 10
            line     : 1 ~ 4
            戻り     : なし
        """
        if gTpEnv:
            if self.p3_flg > 0:
                self.__line_set_p3(slot, line, LINE_SETTING_D_IN)
            else:
                self.__line_set(slot, line, LINE_SETTING_D_IN)
            # callback 登録
            if self.gpio_event_callback is None:
                self.gpio_event_callback = callback
                #thread.start_new_thread(self.__check_gpio_thread, ())
                # -> __spi_access_thread の内部でチェックするよう変更
            # Slot & Line 登録
            self.__gpio_in_edge_table.append([slot, line])
        return

    def analog_read(self, slot, line):
        """ GPIO読み出し
            slot : 1 ~ 10
            line : 1 ~ 4
            戻り : analog値
        """
        if gTpEnv:
            addr = (slot - 1) * 4 + (line - 1) + 0x3D
            if self.p3_flg == 0:
                self.__line_set(slot, line, LINE_SETTING_A_IN)
            dmy = [0]
            dat = self.__pic_spi_access(addr, dmy)
            #print('analog_read', slot, line, hex(addr), dat)
            return dat[0]
        else:
            return 0

    def gpio_init(self, slot, line, kind):
        """ GPIO初期化
            slot : 1 ~ 10
            line : 1 ~ 4
            kind : 0 ~ 4(NONE/ANALOG/IN/OUT_OD/OUT)
            戻り : なし
        """
        #print('gpio_init', slot, line, kind)
        #self.__slot_set_p3(slot, SLOT_SETTING_NONE) # I2C/SPI/SerialでもGPIO使用することあるので、この設定をしてはいけない
        self.__line_set_p3(slot, line, kind)
        return

    def gpio_in_out_init(self, slot, line, kind):
        """ GPIO実行時で設定
            slot : 1 ~ 10
            line : 1 ~ 4
            kind : 0 ~ 4(NONE/ANALOG/IN/OUT_OD/OUT)
            戻り : なし
        """
        #print('gpio_in_out_init', slot, line, kind)
        self.__slot_set(slot, SLOT_SETTING_NONE)
        self.__line_set(slot, line, kind)
        return

    def gpio_read(self, slot, line):
        """ GPIO読み出し
            slot : 1 ~ 10
            line : 1 ~ 4
            戻り : 0 or 1 (Low or High)
        """
        #print('gpio_read', slot, line)
        return self.__gpio_read(0x2E, slot, line)

    def gpio_write(self, slot, line, val, no_use_buf_flg = False):
        """ GPIO書き込み
            slot : 1 ~ 10
            line : 1 ~ 4
            val  : 0 or 1 (Low or High)
            no_use_buf_flg : bufferアクセスせずに直接PICへアクセス
            戻り : なし
        """
        if self.p3_flg == 0:
            self.__line_set(slot, line, LINE_SETTING_D_OUT)
        addr = int((slot - 1) / 2) + 0x29
        dmy = [0]
        self.__gpio_lock.acquire(1) # 過去データorするため排他開始
        try:
            old = self.__spi_write_buf_read(addr, dmy)[0]
            # MSB:S1A,S1B,S1C,S1D,S2A,S2B,S2C,S2D:LSB のようなならび
            bit = 1 << (4 - line)
            if slot % 2 == 1: # 奇数slotは下位4bit
                bit <<= 4
            dat = old | bit if val == 1 else old & (~(bit))
            addr += PIC_WRITE_ADDR
            self.__pic_spi_access(addr, [dat], no_use_buf_flg)
        except:
            raise
        finally:
            self.__gpio_lock.release() # 排他解放
        return

    def rp_button_init(self, callback):
        """ 基板ボタン用設定
            callback : Serial読み込み割り込み発生時のcallback関数
            戻り     : なし
        """
        self.rb_button_callback = callback
        GPIO.add_event_detect(24, GPIO.BOTH, callback = self.__rp_button_callback, bouncetime = 10) # MD
        GPIO.add_event_detect(23, GPIO.BOTH, callback = self.__rp_button_callback, bouncetime = 10) # RST
        return

    def rp_buzzer(self, on):
        """ ラズパイブザーOn/Off
            on  : 1=On, 0=Off
            戻り: なし
        """
        #print('rp_buzzer', on)
        GPIO.output(15, on)
        return

    def rp_led(self, num, on):
        """ ラズパイLED On/Off
            num : LED番号
            on  : 1=On, 0=Off
            戻り: なし
        """
        #print('rp_led', num, on)
        on = 1 if on == 0 else 0
        GPIO.output(self.__rp_led_table[num - 1], on)
        return

    def tp52_init(self, slot):
        """ tibbit #52初期化
            slot  : 1 ~ 10
            戻り  : なし
        """
        #print('tp52_init', slot)
        self.__slot_set_p3(slot, SLOT_SETTING_I2C)
        self.__line_set_p3(slot, 3, LINE_SETTING_D_OUT_OD)
        self.__line_set_p3(slot, 4, LINE_SETTING_D_IN)

    def tp22_init(self, slot):
        """ tibbit #22初期化
            slot  : 1 ~ 10
            戻り  : なし
        """
        #print('tp22_init', slot)
        self.__slot_set_p3(slot, SLOT_SETTING_I2C)
        self.__line_set_p3(slot, 3, LINE_SETTING_D_OUT_OD)
        self.__line_set_p3(slot, 4, LINE_SETTING_D_IN)
        return

    def tp22_temp(self):
        """ Tibbit#22, RTD読み出し
            戻り    : C戻り値、16bit (0x1234 など)
        """
        if gTpEnv:
            self.__subp_lock.acquire(1)
            try:
                c_ret = self.__tp22_temp_lib.tp22_temp(self.__tp22_kbaud, self.__i2c_buf)
                ret_str = str(repr(self.__i2c_buf.value))[2:-1]
            except:
                raise
            finally:
                self.__subp_lock.release()
            #print(c_ret)
            #self.__i2c_end_tp22()
            if c_ret != 0:
                #raise ValueError('tp22_temp error! : c_ret = ' + str(c_ret))
                return c_ret, -999999
            ret = int(ret_str[2:], 16)
            #print('tp22_temp', ret, ret_str)
            return c_ret, ret
        else:
            return 0, 0

    def i2c_read_tp22(self, num):
        """ Tibbit#22, I2C読み出し
            num : 読み込みbyte数
            戻り: i2cデータ 
        """
        if gTpEnv:
            self.__subp_lock.acquire(1)
            try:
                c_ret = self.__i2c_read_tp22_lib.i2c_read_tp22(self.__tp22_kbaud, self.__tp22_addr, num, self.__i2c_buf)
                ret_str = str(repr(self.__i2c_buf.value))[2:-1]
            except:
                raise
            finally:
                self.__subp_lock.release()
            #print(c_ret)
            #self.__i2c_end_tp22()
            if c_ret != 0:
                raise ValueError('i2c_read_tp22 error! : c_ret = ' + str(c_ret))
            #ret_str = str(ret_bin[0])[2:-1]
            ret_str_sep = ret_str.split(',')
            ret = []
            for elem in ret_str_sep:
                ret.append(int(elem[2:], 16)) 
            #print(ret)
            return ret
        else:
            return []

    def i2c_write_tp22(self, data, addr = 0):
        """ Tibbit#22, I2C書き込み
            data : 1byteのみ、書き込みデータ
            addr : 指定されていたらSPIアドレス、0x80以上のはず
            戻り : なし
        """
        if gTpEnv:
            self.__subp_lock.acquire(1)
            try:
                c_ret = self.__i2c_write_tp22_lib.i2c_write_tp22(self.__tp22_kbaud, self.__tp22_addr, data, addr)
            except:
                raise
            finally:
                self.__subp_lock.release()
            #print(c_ret)
            #self.__i2c_end_tp22()
            if c_ret != 0:
                raise ValueError('i2c_write_tp22 error! : c_ret = ' + str(c_ret))
        else:
            pass
        return

    def tpFPGA_write(self, slot, file_path):
        """ FPGA Tibbit(#26,57), FPGAリセット＆書き込み
            slot      : 1 ~ 10
            file_path : binイメージのファイル名フルパス
            戻り      : なし
        """
        #print('tpFPGA_write', slot, file_path)
        if gTpEnv:
            # FPGA Reset
            self.gpio_write(slot, 1, 1)
            self.gpio_write(slot, 2, 0)
            self.gpio_write(slot, 2, 1)
            time.sleep(0.01)
            self.gpio_write(slot, 1, 0)
            self.gpio_write(slot, 2, 0)
            self.gpio_write(slot, 2, 1)
            time.sleep(0.01)
            self.gpio_write(slot, 1, 1)

            # FPGA書き込み
            c_return = self.__fpga_lattice_call(slot, 0, file_path)
            if c_return != 0:
                raise ValueError('tpFPGA_write error! : c_return = ' + str(c_return))
            self.gpio_write(slot, 1, 1)
        else:
            pass
        return

    def tpFPGA_debug(self, slot):
        """ #26動作デバッグ
            slot : 1 ~ 10
            戻り : なし
        """
        #print('tpFPGA_debug', slot)
        if gTpEnv:
            c_return = self.__fpga_lattice_call(slot, 9, '')
            if c_return != 0:
                raise ValueError('tpFPGA_debug error! : c_return = ' + str(c_return))
        else:
            pass
        return

    def tp26_start_record(self, slot):
        """ #26 記録開始
            slot : 1 ~ 10
            戻り : なし
        """
        #print('tp26_start_record', slot)
        if gTpEnv:
            c_return = self.__fpga_lattice_call(slot, 1, '')
            if c_return != 0:
                raise ValueError('tp26_start_record error! : c_return = ' + str(c_return))
        else:
            pass
        return

    def tp26_get_record(self, slot):
        """ #26 記録読み込み
            slot      : 1 ~ 10
            結果は/dev/shm/tp26_record.bin に出力される
            その内容をbyte配列としてreturn
        """
        #print('tp26_get_record', slot)
        if gTpEnv:
            c_return = self.__fpga_lattice_call(slot, 2, '')
            if c_return == -20:
                raise tpUtils.TpCheckError('#26 No Data.')
            elif c_return == -21:
                raise tpUtils.TpCheckError('#26 Recording failed.')
            elif c_return != 0:
                raise ValueError('tp26_get_record error! : c_return = ' + str(c_return))
            # 記録結果読み込み
            with open('/dev/shm/tp26_record.bin', 'rb') as f:
                vals = f.read()
            return vals
        else:
            return []

    def tp26_put_play(self, slot, vals):
        """ #26 記録書き込み
            slot : 1 ~ 10
            vals : 記録したバイナリ配列
            戻り : なし
        """
        #print('tp26_put_play', slot, vals)
        if gTpEnv:
            # 記録バイナリは/dev/shm/tp26_play.bin に保存する
            with open('/dev/shm/tp26_play.bin', 'wb') as f:
                f.write(vals)

            c_return = self.__fpga_lattice_call(slot, 3, '/dev/shm/tp26_play.bin')
            if c_return != 0:
                raise ValueError('tp26_put_play error! : c_return = ' + str(c_return))
        else:
            pass
        return

    def tp26_start_play(self, slot):
        """ #26 再生開始
            slot : 1 ~ 10
            戻り : なし
        """
        #print('tp26_start_play', slot)
        if gTpEnv:
            c_return = self.__fpga_lattice_call(slot, 4, '')
            if c_return != 0:
                raise ValueError('tp26_start_play error! : c_return = ' + str(c_return))
        else:
            pass
        return

    def i2c_read(self, address, cmd, num):
        """ I2C読み出し
            address : I2Cアドレス
            cmd     : 読み込み時コマンド（1byte）, -1 ならcmdなし
            num     : 読み込みbyte数
            戻り    : i2cデータ
        """
        if gTpEnv:
            retry1 = 0
            retry2 = 0
            while True:
                self.__subp_lock.acquire(1)
                err_flg = False
                try:
                    c_ret = self.__i2c_read_lib.i2c_read(self.__i2c_kbaud, address, num, cmd, self.__i2c_buf)
                    ret_str = str(repr(self.__i2c_buf.value))[2:-1]
                except:
                    err_flg = True
                    retry1 += 1
                    if retry1 > I2C_RETRY_NUM:
                        raise
                    else:
                        pass
                finally:
                    self.__subp_lock.release()
                if err_flg: continue
                #print(c_ret, self.__i2c_buf)
                if c_ret != 0:
                    retry2 += 1
                    if retry2 > I2C_RETRY_NUM:
                        raise ValueError('i2c_read error! : c_ret = ' + str(c_ret))
                else:
                    break
                time.sleep(0.01)
            ret_str_sep = ret_str.split(',')
            ret = []
            for elem in ret_str_sep:
                ret.append(int(elem[2:], 16)) 
            return ret
        else:
            pass

    def i2c_write_1byte(self, address, data):
        """ I2C 1byte書き込み
            address : I2Cアドレス
            data    : データ（1byte）
            戻り : なし
        """
        self.i2c_write_block_data(address, data, [])          
        return

    def i2c_write_2byte(self, address, dat1, dat2):
        """ I2C 2byte書き込み
            address : I2Cアドレス
            dat1    : データ（1byteめ）
            dat2    : データ（2byteめ）
            戻り : なし
        """
        self.i2c_write_block_data(address, dat1, [dat2])          
        return

    def i2c_write_block_data(self, address, cmd, vals):
        """ I2C block書き込み
            address : I2Cアドレス
            cmd     : コマンド
            vals    : データリスト
            戻り : なし
        """
        if gTpEnv:
            dat_str = 'x' + format(int(cmd), '02x')
            for elem in vals: dat_str += 'x' + format(int(elem), '02x')
            #print(dat_str)
            retry1 = 0
            retry2 = 0
            while True:
                self.__subp_lock.acquire(1)
                err_flg = False
                try:
                    c_ret = self.__i2c_write_lib.i2c_write(self.__i2c_kbaud, address, len(vals) + 1, dat_str.encode('utf-8'))
                except:
                    err_flg = True
                    retry1 += 1
                    if retry1 > I2C_RETRY_NUM:
                        raise
                    else:
                        pass
                finally:
                    self.__subp_lock.release()
                if err_flg: continue
                #print(c_ret)
                if c_ret != 0:
                    retry2 += 1
                    if retry2 > I2C_RETRY_NUM:
                        raise ValueError('i2c_write error! : c_ret = ' + str(c_ret))
                else:
                    break
                time.sleep(0.01)
        else:
            pass
        return

    def i2c_select(self, slot=0):
        """ I2C用slot選択
            slot : 0(未選択), 1~10
            戻り : なし
        """
        self.__i2c_kbaud = self.__i2c_kbaud_list[slot]
        if slot >= 1 and slot <= 5:
            self.i2c_write_1byte(0x71, 0)
            self.i2c_write_1byte(0x70, 0x08 | (slot - 0))
        elif slot >= 6 and slot <= 10:
            self.i2c_write_1byte(0x70, 0)
            self.i2c_write_1byte(0x71, 0x08 | (slot - 5))
        else:
            self.i2c_write_1byte(0x70, 0)
            self.i2c_write_1byte(0x71, 0)
        return

    def dbg_pic_reg_print(self, addr, num):
        """ Debug用PICレジスタ表示
            addr : 0x00～0x7F
            num  : byte数
            戻り : なし
        """
        dat = [0] * num
        ret = self.__pic_spi_access(addr, dat)
        #print('dbg_pic_reg_print', ret)
        for i, v in enumerate(ret): print(hex(i + addr), hex(v))
        return


    # 内部メソッド ---

    def __pic_fw_update(self, ver, hex_file_path):
        """ PICのFW update
            ver : FW バージョン番号
            hex_file_path : FWファイルのパス
            戻り: なし
        """
        # フラグファイル消去
        sub = subprocess.Popen('rm {0}'.format(PIC_FW_FLG_FILE + str(ver)),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True)
        ret = sub.wait()

        # FW更新
        tpUtils.stdout('Board FW updating...')
        try:
            cmd = PIC_FW_VER_DIR + PIC_PICBERRY
            sub = subprocess.Popen(['sudo', cmd, '-f', 'pic18f66k40', '-g', 'C:18,D:17,M:14', '-w', hex_file_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False)
            ret = sub.wait()
            ret_bin = sub.stdout.readlines()
            ret_chk = str(ret_bin[-1])[2:-3]
            if ret_chk.find('DONE!') == -1: raise
            time.sleep(PIC_INIT_LED_WIAT) # PIC起動待ち
            self.read_pic_fw_ver(True)
            tpUtils.stdout('Board FW update finished!')
        except:
            raise tpUtils.TpCheckError('Fatal Error ! Board FW update error!')

        # 書き込み後フラグファイル対応
        sub = subprocess.Popen('touch {0}'.format(PIC_FW_FLG_FILE + str(ver)),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True)
        ret = sub.wait()

        return

    def __serial_event_callback(self, pin):
        #print('__serial_event_callback pin =', pin)
        pos = self.__serial_int_table.index(pin)
        slot = pos * 2 + 1
        if gTpEnv:
            num_addr = pos + 0x6A
            dat_addr = pos + 0x74
            if True:
                dmy = [0]
                buff_num = self.__pic_spi_access(num_addr, dmy)[0]
                dmy = [0xFF] * buff_num
                dmy[buff_num - 1] = 0 # 送信データの最後は0x00でマーク
                data = self.__pic_spi_access(dat_addr, dmy)
                #print(slot, buff_num, list(map(hex, data)))
                err_addr = pos + 0x65
                dmy = [0]
                err_dat = self.__pic_spi_access(err_addr, dmy)
                if err_dat[0] & 0x0E != 0:
                    #data.insert(0, err_dat[0] + 0x100)
                    print(slot, 'err_dat =', hex(err_dat[0]))
                self.serial_event_callback(slot, data)

    def __serial_data(self, baud, flow, parity):
        # ボーレート
        if baud == 2400:
            ret = 0
        elif baud == 4800:
            ret = 1
        elif baud == 14400:
            ret = 3
        elif baud == 19200:
            ret = 4
        elif baud == 38400:
            ret = 5
        elif baud == 57600:
            ret = 6
        elif baud == 115200:
            ret = 7
        else: # 9600 or other(default)
            ret = 2
        ret <<= 4

        # フロー制御
        #ret += flow << 2

        # パリティ
        ret += parity        

        return ret

    def __pic_spi_access(self, address, vals, no_use_buf_flg = False):
        """ SPI書き込み・読み出し
            address : レジスタアドレス
            vals    : 書き込みデータ（リスト）
            no_use_buf_flg : bufferアクセスせずに直接PICへアクセス
            戻り    : PICからの読み込み値
        """
        #begin_time = time.time()

        ret = self.spi_access(
                0,
                self.__pic_spi_mode,
                self.__pic_spi_khz,
                self.__pic_spi_endian,
                self.__pic_spi_wait_ms,
                address, vals, no_use_buf_flg)
        #time.sleep(SPI_WAIT)
        #end_time = time.time()
        #dt = end_time - begin_time
        #print('dt_ms =', dt * 1000)
        return ret

    def __rp_gpio_init(self):
        # I2C
        #RPIO.setup(2, RPIO.ALT0)
        #RPIO.setup(3, RPIO.ALT0)
        # SPI
        for pin in self.__spi_cs_table: 
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, 0) # 起動時Low
        # exGPIO
        for pin in self.__ex_gpio_int_table: 
            GPIO.setup(pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)
        # Serial
        for pin in self.__serial_int_table: 
            GPIO.setup(pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)
        # 基板LED
        for pin in self.__rp_led_table: 
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, 1) # 起動時消灯
        # 基板SW
        GPIO.setup(24, GPIO.IN, pull_up_down = GPIO.PUD_UP) # MD
        GPIO.setup(23, GPIO.IN, pull_up_down = GPIO.PUD_UP) # RST
        # 基板BZ
        GPIO.setup(15, GPIO.OUT)

    def __gpio_read(self, addr, slot, line):
        addr = int((slot - 1) / 2) + addr
        if self.p3_flg == 0:
            self.__line_set(slot, line, LINE_SETTING_D_IN)
        dmy = [0]
        dat = self.__pic_spi_access(addr, dmy)[0]
        # MSB:S1A,S1B,S1C,S1D,S2A,S2B,S2C,S2D:LSB のようなならび
        bit = 1 << (4 - line)
        if slot % 2 == 1: # 奇数slotは上位4bit
            bit <<= 4
        ret = 0 if dat & bit == 0 else 1
        #print('gpio_read', slot, line, hex(addr), hex(dat), ret)
        return ret

    def __gpio_edge_check(self, dat, cur_in, up, slot, line):
        """ pinのエッジを調べる
            dat    : PICの0x33～0x3Cのエッジ情報10byte
            cur_in : PICの0x2E～0x32の入力情報5byte
            up     : 立ち上がりエッジを調べる場合True、下がりならFalse
            slot   : 1～10
            line   : 1～4
            戻り   : エッジあり= 1, なし= 0
                     入力現在地
        """
        #print('__gpio_edge_check', dat, up, slot, line)
        bit = 1 << (4 - line)
        if slot % 2 == 1: # 奇数slotは上位4bit
            bit <<= 4
        indx = int((slot - 1) / 2)
        cur_indx = indx
        if up == False: indx += 5
        ret = 0 if dat[indx] & bit == 0 else 1
        curr = 0 if cur_in[cur_indx] & bit == 0 else 1
        #print('__gpio_edge_check', slot, line, up, indx, dat[indx], ret, curr)
        return ret, curr

    def __gpio_event_callback(self, vals, cur_in):
        """ GPIO入力に変化があった場合
            vals   : PICの0x33～0x3Cのエッジ情報10byte
            cur_in : PICの0x2E～0x32の入力情報5byte
            戻り : なし
        """
        #print('__gpio_event_callback', list(map(hex, vals)), list(map(hex, cur_in)))
        # 全エッジ情報読み出し
        dat = [0] * 10
        #print('__gpio_event_callback after_read_get', pin)
        #ret = self.__pic_spi_access(0x33, dat)
        ret = vals
        for elem in self.__gpio_in_edge_table:
            up_edge, curr = self.__gpio_edge_check(ret, cur_in, True, elem[0], elem[1])
            down_edge, curr = self.__gpio_edge_check(ret, cur_in, False, elem[0], elem[1])
            if up_edge == 1 and down_edge == 1:
                if curr == 1:
                    self.gpio_event_callback(elem[0], elem[1], 0)
                    self.gpio_event_callback(elem[0], elem[1], 1)
                else:
                    self.gpio_event_callback(elem[0], elem[1], 1)
                    self.gpio_event_callback(elem[0], elem[1], 0)
            elif up_edge == 1 or down_edge == 1:
                self.gpio_event_callback(elem[0], elem[1], up_edge)

        return

    def __rp_button_callback(self, pin):
        if (pin == 24):
            on = 1 if GPIO.input(24) == 0 else 0
            self.rb_button_callback('MD', on)
        else:
            on = 1 if GPIO.input(23) == 0 else 0
            self.rb_button_callback('RST', on)

    def __slot_set_p3(self, slot, kind):
        """ P3用Slot設定
            slot : 1 ~ 10
            kind : 0 ~ 3(SLOT_SETTING_*)
            戻り : なし
        """
        #print('__slot_set_p3', slot, kind)
        addr = (slot - 1) * 3 + 0x0B
        self.__spi_init_write_buf[addr] = kind
        #print('__slot_set_p3', hex(addr), slot, kind)

    def __slot_set(self, slot, kind):
        """ Slot設定
            slot : 1 ~ 10
            kind : 0 ~ 3(SLOT_SETTING_*)
            戻り : なし
        """
        #print('__slot_set', slot, kind)
        addr = (slot - 1) * 3 + 0x0B
        self.__pic_spi_access(PIC_WRITE_ADDR + addr, [kind])

    def __line_set_p3(self, slot, line, kind):
        """ P3用Linet設定
            slot : 1 ~ 10
            line : 1 ~ 4
            kind : 0 ~ 4(LINE_SETTING_*)
            戻り : なし
        """
        #print('__line_set_p3', slot, line, kind)
        addr = (slot - 1) * 3 + 0x0B
        if line == 1 or line == 2: # A or B
            old = self.__spi_init_write_buf[addr + 1]
            if line == 1: # A 
                val = (old & 0x0F) | (kind << 4)
            else: # B
                val = (old & 0xF0) | (kind)
            self.__spi_init_write_buf[addr + 1] = val
        else: # C or D
            old = self.__spi_init_write_buf[addr + 2]
            if line == 3: # C
                val = (old & 0x0F) | (kind << 4)
            else: # D
                val = (old & 0xF0) | (kind)
            self.__spi_init_write_buf[addr + 2] = val
        #print('__line_set_p3', hex(addr), slot, line, hex(val), kind, hex(old))

    def __line_set(self, slot, line, kind):
        """ Linet設定
            slot : 1 ~ 10
            line : 1 ~ 4
            kind : 0 ~ 4(LINE_SETTING_*)
            戻り : なし
        """
        #print('__line_set', slot, line, kind)
        # 設定済みか確認
        if self.__kind_table[slot - 1][line - 1] == kind: return
        self.__kind_table[slot - 1][line - 1] = kind

        # 設定開始
        # 現在情報読み込み 
        addr = (slot - 1) * 3 + 0x0B
        self.__line_lock.acquire(1) # 過去データorするため排他開始
        try:
            if line == 1 or line == 2: # A or B
                dmy = [0]
                old = self.__pic_spi_access(addr + 1, dmy)
                val = [0]
                if line == 1: # A 
                    val[0] = (old[0] & 0x0F) | (kind << 4)
                else: # B
                    val[0] = (old[0] & 0xF0) | (kind)
            else: # C or D
                dmy = [0, 0]
                old = self.__pic_spi_access(addr + 1, dmy)
                val = [old[0], 0]
                if line == 3: # C
                    val[1] = (old[1] & 0x0F) | (kind << 4)
                else: # D
                    val[1] = (old[1] & 0xF0) | (kind)
            # 現在情報とorして書き込み
            val.insert(0, SLOT_SETTING_NONE)
            #print('__line_set', hex(addr), val, kind, old)
            """
            if len(old) == 2:
                err_str = '__line_set' + ' ' + str(hex(addr)) + ' ' + str(hex(val[0])) + ',' + str(hex(val[1])) + ',' + str(hex(val[2])) + ' ' + str(kind) + ' ' + str(hex(old[0])) + ',' + str(hex(old[1])) + '\r\n'
            else:
                err_str = '__line_set' + ' ' + str(hex(addr)) + ' ' + str(hex(val[0])) + ',' + str(hex(val[1])) + ' ' + str(kind) + ' ' + str(hex(old[0])) + '\r\n'
            tpUtils.stderr(err_str)
            """

            self.__pic_spi_access(PIC_WRITE_ADDR + addr, val)
        except:
            raise
        finally:
            self.__line_lock.release() # 排他解放

    """
    def __check_gpio_thread(self):
        while True:
            pin = self.__ex_gpio_int_table[0]
            if GPIO.input(pin) == 0:
                self.__gpio_event_callback(pin)
            time.sleep(CHECK_WAIT)
    """

    def __check_serial_thread(self):
        """ event登録のかわりにloopで処理
        """
        while True:
            for pin in self.__serial_int_table:
                if GPIO.input(pin) == 0:
                    self.__serial_event_callback(pin)
            time.sleep(CHECK_WAIT)

    def __spi_access_thread(self):
        """ PICのレジスタ情報をバッファに読み書きするthread
        """
        old_in = [0] * 5 # GPIO入力エッジ確認用
        pulse_chk = [0] * 10 # 瞬時パルス確認用
        while True:

            # 読み込み
            #print(self.__spi_write_buf_flg[0x29:0x2E])
            self.__spi_write_buf_flg_lock.acquire(1)
            if any(self.__spi_write_buf_flg[0x29:0x2E]): 
                self.__spi_write_buf_put()
                self.__spi_read_buf_get()
                # write flg クリア
                self.__spi_write_buf_flg[self.__spi_write_start_addr:self.__spi_write_end_addr + 1] = [0] * (self.__spi_write_end_addr - self.__spi_write_start_addr + 1)
            else:
                self.__spi_read_buf_get()
            self.__spi_write_buf_flg_lock.release()

            # GPIO Inチェック
            if self.gpio_event_callback is not None:
                cur_in = self.__spi_read_buf_read(0x2E, old_in)
                check_flg, in_edge = self.__gpio_in_edge_check(old_in, cur_in)
                if check_flg:
                    self.__gpio_event_callback(in_edge, cur_in)
                else: # 瞬時パルス確認
                    pulse_chk = self.__spi_read_buf_read(0x33, pulse_chk)
                    if pulse_chk.count(0) != 10:
                        self.__gpio_event_callback(pulse_chk, cur_in)
                old_in = cur_in[:]

            # wait
            while True: # 途中で__spi_read_buf_get() がthread外から呼ばれても規定秒waitする　
                start = self.__spi_read_buf_start
                end = time.time()
                dt = end - start
                wait = PIC_READ_THREAD_WAIT - dt if PIC_READ_THREAD_WAIT - dt > 0 else 0.001
                #print('dt =', dt, 'wait =', wait)
                time.sleep(wait)
                if start == self.__spi_read_buf_start: break
                # 途中でstartの値かわっていたら、再度waitする
                #print('再度wait', dt, 'wait =', wait)

    def __gpio_in_edge_check(self, old_in, cur_in):
        """ GPIOのIN edgeをチェックする
            old_in : 過去の入力データ
            cur_in : 現在の入力データ
            戻り   : flg 変化ありならTrue
                     edge情報10byte（PICアドレス 0x33~0x3C と同じイメージ）
        """
        #print('__gpio_in_edge_check', list(map(hex, old_in)), list(map(hex, cur_in)))
        up_edge = [0] * 5
        down_edge = [0] * 5
        for i in range(5):
            up_edge[i] = (old_in[i] ^ cur_in[i]) & cur_in[i]
            down_edge[i] = (old_in[i] ^ cur_in[i]) & old_in[i]
        in_edge = up_edge
        in_edge.extend(down_edge)
        check_flg = any(in_edge)
        #print('__gpio_in_edge_check', check_flg, list(map(hex, in_edge)))
        return check_flg, in_edge

    def __spi_write_buf_put(self):
        """ バッファからSPIにwriteする
            戻り : なし
        """
        #print('__spi_write_buf_put', self.__spi_write_buf_side)
        #print('__spi_write_buf_put', self.__spi_write_buf_side, list(map(hex, self.__spi_write_buf[self.__spi_write_buf_side][0x29:0x2E])))
        self.__spi_write_buf_lock.acquire(1)

        retry = 0
        out = self.__spi_write_buf[self.__spi_write_buf_side][self.__spi_write_start_addr:self.__spi_write_end_addr + 1]
        while True:
            self.__pic_spi_access(self.__spi_write_start_addr + PIC_WRITE_ADDR, out, True)
            ret = self.__pic_spi_access(self.__spi_write_start_addr, out, True)
            if out != ret:
                retry += 1
                #print('__spi_write_buf_put NG!!!!', retry, list(map(hex, out)), list(map(hex, ret)))
                if retry > SPI_RETRY_NUM: 
                    #print('__spi_write_buf_put NG!!!!', retry, list(map(hex, out)), list(map(hex, ret)))
                    raise ValueError('__spi_write_buf_put retry error!') 
                    break
                continue
            break

        #self.__spi_write_buf_side = 0 if self.__spi_write_buf_side == 1 else 1 # 0面のみ使用
        self.__spi_write_buf_lock.release()
        #print(self.__spi_write_buf)
        return

    def __spi_read_buf_get(self):
        """ SPIからバッファにreadする
            戻り : なし
        """
        self.__spi_read_buf_lock.acquire(1)
        self.__spi_read_buf_start = time.time()
        ret = self.__pic_spi_access(self.__spi_read_start_addr, self.__spi_read_buf[self.__spi_read_buf_side][self.__spi_read_start_addr:self.__spi_read_end_addr + 1], True)
        self.__spi_read_buf[self.__spi_read_buf_side][self.__spi_read_start_addr:self.__spi_read_end_addr + 1] = ret[:]
        self.__spi_read_buf_side = 0 if self.__spi_read_buf_side == 1 else 1
        self.__spi_read_buf_lock.release()
        #print(self.__spi_read_buf)
        return

    def __spi_write_buf_write(self, addr, vals):
        """ バッファに書き込む
            addr : レジスタアドレス
            vals : 書き込みデータ（リスト）
            戻り : valsそのまま
        """
        self.__spi_write_buf_flg_lock.acquire(1)
        self.__spi_write_buf_flg[addr] = 1 # 書き込みフラグ

        self.__spi_write_buf_lock.acquire(1)
        #side = 0 if self.__spi_write_buf_side == 1 else 1 # 0面のみ使用
        self.__spi_write_buf[self.__spi_write_buf_side][addr:addr+len(vals)] = vals[0:len(vals)]
        self.__spi_write_buf_lock.release()
        #print('__spi_write_buf_write', hex(addr), vals, lock_check, self.__spi_write_buf_side)
        #print('__spi_write_buf_write', self.__spi_write_buf_flg[0x29:0x2E])
        self.__spi_write_buf_flg_lock.release()
        return vals

    def __spi_write_buf_read(self, addr, vals):
        """ writeバッファの内容を返す
            addr : レジスタアドレス
            vals : 書き込みデータ（リスト）
            戻り : バッファからの読み込み値
        """
        self.__spi_write_buf_lock.acquire(1)
        ret = self.__spi_write_buf[self.__spi_write_buf_side][addr:addr+len(vals)]
        self.__spi_write_buf_lock.release()
        #print('__spi_write_buf_write:not locked', side, hex(addr), list(map(hex, ret)))
        return ret

    def __spi_read_buf_read(self, addr, vals):
        """ readバッファの内容を返す
            addr : レジスタアドレス
            vals : 書き込みデータ（リスト）
            戻り : バッファからの読み込み値
        """
        if addr >= self.__spi_write_start_addr and addr <= self.__spi_write_end_addr:
            while True: # 書き込みフラグが立っていたらまつ（bufferにreadでクリアされる）
                if self.__spi_write_buf_flg[addr] == 0: break
                time.sleep(CHECK_WAIT)
        lock_check = self.__spi_read_buf_lock.locked()
        if lock_check == True:
            # lock中なら、反対側のbufferを利用する。waitが入るので、すぐにbufferは書き換わらない
            side = 0 if self.__spi_read_buf_side == 1 else 1
            ret = self.__spi_read_buf[side][addr:addr+len(vals)]
            #print('locked', side, hex(addr), ret)
        else:
            # lockしていないなら、bufferアクセス中にgetされないようにlockする
            self.__spi_read_buf_lock.acquire(1)
            side = 0 if self.__spi_read_buf_side == 1 else 1
            ret = self.__spi_read_buf[side][addr:addr+len(vals)]
            self.__spi_read_buf_lock.release()
            #print('not locked', side, hex(addr), ret)
        return ret

    def __fpga_lattice_call(self, slot, mode, file_path):
        """ c/fpga_lattice 呼び出し
        """
        self.__subp_lock.acquire(1)
        try:
            c_ret = self.__fpga_lattice_lib.fpga_lattice(slot, mode, file_path.encode('utf-8'))
        except:
            raise
        finally:
            self.__subp_lock.release()
        #print(c_ret)
        return c_ret

