#!/usr/bin/python3
"""P3用プログラム
   インターフェース部クラス
"""
gTpEnv = True # 環境チェック, TrueでTibbo-Piとみなす
import os, sys
import _thread as thread
import time
try:
    import RPi.GPIO as GPIO
    import subprocess
except:
    gTpEnv = False
import tpUtils

# 定数宣言 ---------------------------------------------------------------
SLOT_SETTING_NONE = 0x00
SLOT_SETTING_SERI = 0x01
SLOT_SETTING_I2C  = 0x02
SLOT_SETTING_SPI  = 0x03
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
            subprocess.call(['/bin/sh', self.__path + '/c/ch.sh', self.__path + '/c/spi_access'])
            subprocess.call(['/bin/sh', self.__path + '/c/ch.sh', self.__path + '/c/i2c_read_tp22'])
            subprocess.call(['/bin/sh', self.__path + '/c/ch.sh', self.__path + '/c/i2c_write_tp22'])
            subprocess.call(['/bin/sh', self.__path + '/c/ch.sh', self.__path + '/c/tp22_temp'])
            subprocess.call(['/bin/sh', self.__path + '/c/ch.sh', self.__path + '/c/end_tp22.sh'])
            subprocess.call(['/bin/sh', self.__path + '/c/ch.sh', self.__path + '/c/i2c_read'])
            subprocess.call(['/bin/sh', self.__path + '/c/ch.sh', self.__path + '/c/i2c_write'])
            subprocess.call(['/bin/sh', self.__path + '/c/ch.sh', self.__path + '/c/fpga_lattice'])

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
            self.__tp22_addr = '0x0D'
            self.__tp22_kbaud = 15

            # i2c設定
            self.__i2c_kbaud_list = [100] * 11 # 0 = slot未選択時, default 100Kbps
            self.__i2c_kbaud = 0 # アクセス時書き換え用

            # P3用設定
            self.p3_flg = 2 # 0:P2, 1:line_setのみP3, 2:全部P3
            self.__spi_init_write_buf = [0] * 0x29 # アドレス0x01～0x28使用
            self.__spi_write_buf = [[0] * 0x2E] * 2 # アドレス0x29～0x2D 2面使用
            self.__spi_write_buf_side = 0 # 0 or 1,  アクセス中なら、この値の逆サイド利用
            self.__spi_write_buf_flg = [0] * 0x2E # アドレス0x29～0x2D 使用, 1でwriteあり
            self.__spi_write_start_addr = 0x29 
            self.__spi_write_end_addr = 0x2D 
            self.__spi_write_buf_lock = thread.allocate_lock()
            self.__spi_read_buf = [[0] * 0x65] * 2 # アドレス0x29～0x64 2面使用
            self.__spi_read_buf_side = 0 # 0 or 1,  アクセス中なら、この値の逆サイド利用
            self.__spi_read_buf_start = 0 # bufferへの取得開始時刻
            self.__spi_read_start_addr = 0x29 
            self.__spi_read_end_addr = 0x64 # slot数で処理時間がかわるのを防ぐため、毎回最大スロットを読み込む
            self.__spi_read_buf_lock = thread.allocate_lock()
        else: # 非Tibbo-Pi環境（以下全メソッドで同様, dummy値を返すこともあり）
            pass

    def pic_slot_init(self):
        """ PICスロット初期設定
            戻り : なし
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

    def board_init(self):
        """ 基板初期化
        """
        if gTpEnv:
            GPIO.setwarnings(False)
            self.__rp_gpio_init()
            self.i2c_select(0)
            # PIC初期化
            self.__pic_spi_access(PIC_WRITE_ADDR, [PIC_RST_CMD])
            time.sleep(1) # P3 PIC起動時LED点滅待ち

    def spi_lock_init(self, lock):
        """ SPI Lock初期化
            lock : SPIアクセス時thread lock
        """
        self.__spi_lock = lock

    def spi_init(self, slot, kbaud):
        """ SPI初期化
            slot  : 1 ~ 10
            kbaud : 通信速度
            戻り  : なし
        """
        #print('spi_init', slot, kbaud)
        self.__slot_set_p3(slot, SLOT_SETTING_SPI)

    def i2c_init(self, slot, kbaud):
        """ I2C初期化
            slot  : 1 ~ 10
            kbaud : 通信速度
            戻り  : なし
        """
        #print('i2c_init', slot, kbaud)
        self.__i2c_kbaud_list[slot] = kbaud
        self.__slot_set_p3(slot, SLOT_SETTING_I2C)

    def serial_init(self, callback, slot, baud, flow, parity):
        """ Serial初期化
        """
        #print('serial_init', callback, slot, baud, flow, parity)
        if slot % 2 == 0: return # 奇数slotのみ対応
        if gTpEnv:
            # PIC設定
            addr = (slot - 1) + 0x01 
            data = self.__serial_data(baud, flow, parity)
            if self.p3_flg > 0:
                self.__slot_set_p3(slot, SLOT_SETTING_SERI)
                self.__spi_init_write_buf[addr] = data
            else:
                self.__slot_set(slot, SLOT_SETTING_SERI)
                self.__pic_spi_access(PIC_WRITE_ADDR + addr, [data])
            # 受信時callback設定
            if self.serial_event_callback is None:
                self.serial_event_callback = callback
                # 取りこぼしが発生するのでevent登録ではなくloopで処理する
                thread.start_new_thread(self.__check_serial_thread, ())

    def serial_write(self, slot, vals):
        """ Serial書き込み
        """
        #print('serial_write', slot, vals)
        vals = [b for b in vals]
        
        if slot % 2 == 0: return # 奇数slotのみ対応
        pos = int((slot - 1) / 2)
        if gTpEnv:
            num_addr = pos + 0x6F
            dat_addr = pos + 0x79 + PIC_WRITE_ADDR
            while len(vals):
                dmy = [0]
                buff_num = 250 - self.__pic_spi_access(num_addr, dmy)[0]
                if buff_num >= len(vals):
                    self.__pic_spi_access(dat_addr, vals)
                    vals.clear()
                elif buff_num <= 0: # バッファあふれならwait
                    time.sleep(0.01)
                else:
                    self.__pic_spi_access(dat_addr, vals[:buff_num])
                    del vals[:buff_num]

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
            c_cmd = self.__path +\
                '/c/spi_access ' +\
                str(mode) + ' ' +\
                str(speed) + ' ' +\
                str(endian) + ' ' +\
                '0x' + format(int(address), '02x') + ' ' +\
                str(wait_ms) + ' ' +\
                str(slot) + ' ' +\
                str(len(data))
            for elem in data: c_cmd += ' 0x' + format(elem, '02x')
            #print(c_cmd)
            self.__spi_lock.acquire(1)
            self.__subp_lock.acquire(1)
            try:
                c_ret = subprocess.Popen(c_cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True)
                c_return = c_ret.wait()
                ret_bin = c_ret.stdout.readlines()
            except:
                raise
            finally:
                self.__subp_lock.release()
                self.__spi_lock.release()
            #print(c_return, ret_bin)
            c_return -= 256 if c_return > 127 else c_return
            if c_return != 0:
                raise ValueError('SPI access error! : c_return = ' + str(c_return))
            ret_str = str(ret_bin[0])[2:-1]
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

    def analog_read(self, slot, line):
        """ GPIO読み出し
            slot : 1 ~ 10
            line : 1 ~ 4
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
            kind : 2 ~ 4(IN/OUT_OD/OUT)
            戻り : なし
        """
        #print('gpio_init', slot, line, kind)
        #self.__slot_set_p3(slot, SLOT_SETTING_NONE) # I2C/SPI/SerialでもGPIO使用することあるので、この設定をしてはいけない
        self.__line_set_p3(slot, line, kind)

    def gpio_in_out_init(self, slot, line, kind):
        """ GPIO実行時で設定
            slot : 1 ~ 10
            line : 1 ~ 4
            kind : 2 ~ 4(IN/OUT_OD/OUT)
            戻り : なし
        """
        #print('gpio_in_out_init', slot, line, kind)
        self.__slot_set(slot, SLOT_SETTING_NONE)
        self.__line_set(slot, line, kind)

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
            old = self.__pic_spi_access(addr, dmy, no_use_buf_flg)[0]
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

    def rp_button_init(self, callback):
        """ 基板ボタン用設定
        """
        self.rb_button_callback = callback
        GPIO.add_event_detect(24, GPIO.BOTH, callback = self.__rp_button_callback, bouncetime = 10) # MD
        GPIO.add_event_detect(23, GPIO.BOTH, callback = self.__rp_button_callback, bouncetime = 10) # RST

    def rp_buzzer(self, on):
        """ ラズパイブザーOn/Off
        """
        #print('rp_buzzer', on)
        GPIO.output(15, on)

    def rp_led(self, num, on):
        """ ラズパイLED On/Off
        """
        #print('rp_led', num, on)
        on = 1 if on == 0 else 0
        GPIO.output(self.__rp_led_table[num - 1], on)

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

    def tp22_temp(self, slot):
        """ Tibbit#22, RTD読み出し
            slot    : 1 ~ 10
            戻り    : C戻り値、16bit (0x1234 など)
        """
        if gTpEnv:
            c_cmd = self.__path +\
                '/c/tp22_temp ' +\
                str(slot) + ' ' +\
                str(self.__tp22_kbaud) 
            #print(c_cmd)

            self.__subp_lock.acquire(1)
            try:
                c_ret = subprocess.Popen(c_cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True)

                c_return = c_ret.wait()
                ret_bin = c_ret.stdout.readlines()
            except:
                raise
            finally:
                self.__subp_lock.release()
            #print(c_return, ret_bin)
            c_return -= 256 if c_return > 127 else c_return
            self.__i2c_end_tp22()
            if c_return != 0:
                #raise ValueError('tp22_temp error! : c_return = ' + str(c_return))
                return c_return, -999999
            ret_str = str(ret_bin[0])[2:-1]
            ret = int(ret_str[2:], 16)
            #print(ret)
            return c_return, ret
        else:
            pass

    def i2c_read_tp22(self, slot, num):
        """ Tibbit#22, I2C読み出し
            slot    : 1 ~ 10
            num     : 読み込みbyte数
        """
        #print('i2c_read_tp22', slot, num)
        if gTpEnv:
            c_cmd = os.path.dirname(os.path.abspath(__file__)) +\
                '/c/i2c_read_tp22 ' +\
                str(slot) + ' ' +\
                str(self.__tp22_kbaud) + ' ' +\
                self.__tp22_addr + ' ' +\
                str(num)
            #print(c_cmd)

            self.__subp_lock.acquire(1)
            try:
                c_ret = subprocess.Popen(c_cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True)

                c_return = c_ret.wait()
                ret_bin = c_ret.stdout.readlines()
            except:
                raise
            finally:
                self.__subp_lock.release()
            #print(c_return, ret_bin)
            c_return -= 256 if c_return > 127 else c_return
            self.__i2c_end_tp22()
            if c_return != 0:
                raise ValueError('i2c_read_tp22 error! : c_return = ' + str(c_return))
            ret_str = str(ret_bin[0])[2:-1]
            ret_str_sep = ret_str.split(',')
            ret = []
            for elem in ret_str_sep:
                ret.append(int(elem[2:], 16)) 
            #print(ret)
            return ret
        else:
            pass

    def i2c_write_tp22(self, slot, data, addr = 0):
        """ Tibbit#22, I2C書き込み
            slot    : 1 ~ 10
            data    : 1byteのみ、書き込みデータ
            addr    : 指定されていたらSPIアドレス、0x80以上のはず
            戻り : なし
        """
        #print('i2c_write_tp22', slot, data, addr)
        if gTpEnv:
            c_cmd = os.path.dirname(os.path.abspath(__file__)) +\
                '/c/i2c_write_tp22 ' +\
                str(slot) + ' ' +\
                str(self.__tp22_kbaud) + ' ' +\
                self.__tp22_addr + ' ' +\
                '0x' + format(int(data), '02x') 
            if addr != 0: c_cmd += ' 0x' + format(int(addr), '02x')
            #print(c_cmd)

            self.__subp_lock.acquire(1)
            try:
                c_ret = subprocess.Popen(c_cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True)

                c_return = c_ret.wait()
                ret_bin = c_ret.stdout.readlines()
            except:
                raise
            finally:
                self.__subp_lock.release()
            #print(c_return, ret_bin)
            c_return -= 256 if c_return > 127 else c_return
            self.__i2c_end_tp22()
            if c_return != 0:
                raise ValueError('i2c_write_tp22 error! : c_return = ' + str(c_return))
        else:
            pass
        return

    def tpFPGA_write(self, slot, file_path):
        """ FPGA Tibbit(#26,57), FPGAリセット＆書き込み
            slot      : 1 ~ 10
            file_path : binイメージのファイル名フルパス
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
            c_cmd = os.path.dirname(os.path.abspath(__file__)) +\
                '/c/fpga_lattice ' +\
                str(slot) + ' ' +\
                '0 ' +\
                file_path
            #print(c_cmd)
            c_return = self.__fpga_lattice_call(c_cmd)
            if c_return != 0:
                raise ValueError('tpFPGA_write error! : c_return = ' + str(c_return))
        else:
            pass

    def tp26_start_record(self, slot):
        """ #26 記録開始
            slot      : 1 ~ 10
        """
        #print('tp26_start_record', slot)
        if gTpEnv:
            c_cmd = os.path.dirname(os.path.abspath(__file__)) +\
                '/c/fpga_lattice ' +\
                str(slot) + ' ' +\
                '1 '
            #print(c_cmd)
            c_return = self.__fpga_lattice_call(c_cmd)
            if c_return != 0:
                raise ValueError('tp26_start_record error! : c_return = ' + str(c_return))
        else:
            pass

    def tp26_get_record(self, slot):
        """ #26 記録読み込み
            slot      : 1 ~ 10
            結果は/dev/shm/tp26_record.bin に出力される
            その内容をbyte配列としてreturn
        """
        #print('tp26_get_record', slot)
        if gTpEnv:
            c_cmd = os.path.dirname(os.path.abspath(__file__)) +\
                '/c/fpga_lattice ' +\
                str(slot) + ' ' +\
                '2 '
            #print(c_cmd)
            c_return = self.__fpga_lattice_call(c_cmd)
            if c_return != 0:
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
        """
        #print('tp26_put_play', slot, vals)
        if gTpEnv:
            # 記録バイナリは/dev/shm/tp26_play.bin に保存する
            with open('/dev/shm/tp26_play.bin', 'wb') as f:
                f.write(vals)

            c_cmd = os.path.dirname(os.path.abspath(__file__)) +\
                '/c/fpga_lattice ' +\
                str(slot) + ' ' +\
                '3 /dev/shm/tp26_play.bin'
            #print(c_cmd)
            c_return = self.__fpga_lattice_call(c_cmd)
            if c_return != 0:
                raise ValueError('tp26_put_play error! : c_return = ' + str(c_return))
        else:
            pass

    def tp26_start_play(self, slot):
        """ #26 再生開始
            slot      : 1 ~ 10
        """
        #print('tp26_start_play', slot)
        if gTpEnv:
            c_cmd = os.path.dirname(os.path.abspath(__file__)) +\
                '/c/fpga_lattice ' +\
                str(slot) + ' ' +\
                '4 '
            #print(c_cmd)
            c_return = self.__fpga_lattice_call(c_cmd)
            if c_return != 0:
                raise ValueError('tp26_start_play error! : c_return = ' + str(c_return))
        else:
            pass

    def i2c_read(self, address, cmd, num):
        """ I2C読み出し
            address : I2Cアドレス
            cmd     : 読み込み時コマンド（1byte）, -1 ならcmdなし
            num     : 読み込みbyte数
            戻り    : i2cデータ
        """
        if gTpEnv:
            #start = time.time()
            c_cmd = os.path.dirname(os.path.abspath(__file__)) +\
                '/c/i2c_read ' +\
                str(self.__i2c_kbaud) +\
                ' 0x' + format(int(address), '02x') +\
                ' ' + str(num)
            if cmd >= 0:
                c_cmd += ' 0x' + format(int(cmd), '02x') 
            #print(c_cmd)

            self.__subp_lock.acquire(1)
            try:
                c_ret = subprocess.Popen(c_cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True)

                c_return = c_ret.wait()
                ret_bin = c_ret.stdout.readlines()
            except:
                raise
            finally:
                self.__subp_lock.release()
            #print(c_return, ret_bin)
            c_return -= 256 if c_return > 127 else c_return
            if c_return != 0:
                raise ValueError('i2c_read error! : c_return = ' + str(c_return))
            ret_str = str(ret_bin[0])[2:-1]
            ret_str_sep = ret_str.split(',')
            ret = []
            for elem in ret_str_sep:
                ret.append(int(elem[2:], 16)) 
            #dt = time.time() - start
            #print('i2c_read:', dt * 1000, 'ms')
            #print(ret)
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
        """ I2C 2byte書き込み
            address : I2Cアドレス
            cmd     : コマンド
            vals    : データリスト
            戻り : なし
        """
        if gTpEnv:
            #start = time.time()
            c_cmd = os.path.dirname(os.path.abspath(__file__)) +\
                '/c/i2c_write ' +\
                str(self.__i2c_kbaud) +\
                ' 0x' + format(int(address), '02x') +\
                ' ' + str(1 + len(vals)) +\
                ' 0x' + format(int(cmd), '02x') 
            for elem in vals: c_cmd += ' 0x' + format(int(elem), '02x')
            #print(c_cmd)

            self.__subp_lock.acquire(1)
            try:
                c_ret = subprocess.Popen(c_cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True)

                c_return = c_ret.wait()
                ret_bin = c_ret.stdout.readlines()
            except:
                raise
            finally:
                self.__subp_lock.release()
            #print(c_return, ret_bin)
            c_return -= 256 if c_return > 127 else c_return
            if c_return != 0:
                raise ValueError('i2c_write error! : c_return = ' + str(c_return))
            #dt = time.time() - start
            #print('i2c_write:', dt * 1000, 'ms')
        else:
            pass
        return

    def i2c_select(self, slot=0):
        """ I2C用slot選択
            slot : 0(未選択), 1~10
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

    def dbg_pic_reg_print(self, addr, num):
        """ Debug用PICレジスタ表示
            addr : 0x00～0x7F
            num  : byte数
        """
        dat = [0] * num
        ret = self.__pic_spi_access(addr, dat)
        #print('dbg_pic_reg_print', ret)
        for i, v in enumerate(ret): print(hex(i + addr), hex(v))

    # 内部メソッド ---

    def __i2c_end_tp22(self):
        while True:
            try:
                self.i2c_select(0)
                break
            except:
                #print('__i2c_end_tp22 except!')
                self.__subp_lock.acquire(1)
                try:
                    subprocess.call(self.__path + '/c/end_tp22.sh', shell=True)
                except:
                    raise
                finally:
                    self.__subp_lock.release()

    #def serial_event_callback_test(self, pin):
    #    self.__serial_event_callback(pin)
    def __serial_event_callback(self, pin):
        #print('__serial_event_callback pin =', pin)
        pos = self.__serial_int_table.index(pin)
        slot = pos * 2 + 1
        if gTpEnv:
            num_addr = pos + 0x6A
            dat_addr = pos + 0x74
            while True:
                dmy = [0]
                buff_num = self.__pic_spi_access(num_addr, dmy)[0]
                if buff_num == 0: break
                dmy = [0] * buff_num
                data = self.__pic_spi_access(dat_addr, dmy)
                #print(slot, buff_num, data)
                self.serial_event_callback(slot, data)

    # 内部メソッド ---

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
        ret += flow << 2

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

    def __gpio_edge_check(self, dat, up, slot, line):
        """ pinのエッジを調べる
            dat  : PICの0x33～0x3Cのエッジ情報10byte
            up   : 立ち上がりエッジを調べる場合True、下がりならFalse
            slot : 1～10
            line : 1～4
        """
        #print('__gpio_edge_check', dat, up, slot, line)
        bit = 1 << (4 - line)
        if slot % 2 == 1: # 奇数slotは上位4bit
            bit <<= 4
        indx = int((slot - 1) / 2)
        if up == False: indx += 5
        ret = 0 if dat[indx] & bit == 0 else 1
        #print('__gpio_edge_check', slot, line, up, indx, dat[indx], ret)
        return ret

    def __gpio_event_callback(self, vals):
        """ GPIO入力に変化があった場合
            戻り : なし
        """
        #print('__gpio_event_callback', pin)
        # 全エッジ情報読み出し
        dat = [0] * 10
        #print('__gpio_event_callback after_read_get', pin)
        #ret = self.__pic_spi_access(0x33, dat)
        ret = vals
        for elem in self.__gpio_in_edge_table:
            # 立ち上がりエッジ確認
            if self.__gpio_edge_check(ret, True, elem[0], elem[1]) == 1:
                #print('Rise callback : slot =', elem[0], 'line =', elem[1])
                self.gpio_event_callback(elem[0], elem[1], 1)
            # 立ち下がりエッジ確認
            if self.__gpio_edge_check(ret, False, elem[0], elem[1]) == 1:
                #print('Fall callback : slot =', elem[0], 'line =', elem[1])
                self.gpio_event_callback(elem[0], elem[1], 0)
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
        while True:

            # 読み込み
            #print(self.__spi_write_buf_flg[0x29:0x2E])
            if any(self.__spi_write_buf_flg[0x29:0x2E]): 
                self.__spi_write_buf_put()
                self.__spi_read_buf_get()
                # write flg クリア
                self.__spi_write_buf_flg[self.__spi_write_start_addr:self.__spi_write_end_addr + 1] = [0] * (self.__spi_write_end_addr - self.__spi_write_start_addr + 1)
            else:
                self.__spi_read_buf_get()

            # GPIO Inチェック
            if self.gpio_event_callback is not None:
                cur_in = self.__spi_read_buf_read(0x2E, old_in)
                check_flg, in_edge = self.__gpio_in_edge_check(old_in, cur_in)
                if check_flg:
                    self.__gpio_event_callback(in_edge)
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
        self.__spi_write_buf_lock.acquire(1)
        self.__pic_spi_access(self.__spi_write_start_addr + PIC_WRITE_ADDR, self.__spi_write_buf[self.__spi_write_buf_side][self.__spi_write_start_addr:self.__spi_write_end_addr + 1], True)
        self.__spi_write_buf_side = 0 if self.__spi_write_buf_side == 1 else 1
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
        self.__spi_write_buf_flg[addr] = 1 # 書き込みフラグ
        lock_check = self.__spi_write_buf_lock.locked()
        if lock_check == True:
            # lock中なら、反対側のbufferを利用する。waitが入るので、すぐにbufferは書き換わらない
            side = 0 if self.__spi_write_buf_side == 1 else 1
            self.__spi_write_buf[side][addr:addr+len(vals)] = vals[0:len(vals)]
        else:
            # lockしていないなら、bufferアクセス中にputされないようにlockする
            self.__spi_write_buf_lock.acquire(1)
            side = 0 if self.__spi_write_buf_side == 1 else 1
            self.__spi_write_buf[side][addr:addr+len(vals)] = vals[0:len(vals)]
            self.__spi_write_buf_lock.release()
        return vals

    def __spi_read_buf_read(self, addr, vals):
        """ バッファの内容を返す
            addr : レジスタアドレス
            vals : 書き込みデータ（リスト）
            戻り : バッファ委からの読み込み値
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

    def __fpga_lattice_call(self, c_cmd):
        """ c/fpga_lattice 呼び出し
        """
        self.__subp_lock.acquire(1)
        try:
            c_ret = subprocess.Popen(c_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True)
            c_return = c_ret.wait()
        except:
            raise
        finally:
            self.__subp_lock.release()
        #print(c_return)
        c_return -= 256 if c_return > 127 else c_return
        return c_return 

# main部 -----------------------------------------------------------------

def pic_reg_read(inter, slot, address, num):
    addr1 = address >> 8
    addr2 = address & 0x00FF
    #print(slot, num, address, addr1, addr2)
    inter.i2c_select(slot)
    inter.i2c_write_block_data(0x03, 0xFE, [addr1, addr2])
    inter.i2c_select(0)
    time.sleep(0.01)
    inter.i2c_select(slot)
    ret = inter.i2c_read(0x03, 0, num)
    return ret

def pic_reg_write(inter, slot, address, vals):
    addr1 = address >> 8
    addr2 = address & 0x00FF
    dat = [addr1, addr2]
    dat.extend(vals)
    #print(slot, vals, address, addr1, addr2, dat)
    inter.i2c_select(slot)
    inter.i2c_write_block_data(0x03, 0xFE, dat)
    inter.i2c_select(0)

def tbt52_error_compensation(v0, v1, v2, v3):
    r = v1 * 0x10000 + v2 * 0x100 + v3
    ret = r / 1000000
    ret += v0 * 0x1000000
    if v0 & 0x80: ret = -ret
    return ret   

def tbt52_int_wait(slot):
    while True:
        v = inter.gpio_read(slot, 4)
        if v == 1: break

if __name__ == '__main__':
    argv = sys.argv
    inter = TpP3Interface()
    lock = thread.allocate_lock()
    inter.spi_lock_init(lock)
    inter.board_init()

    #inter.i2c_select(0)
    #sys.exit();

    while False:
        #inter.dbg_pic_reg_print(0x00, 0x3D)
        inter.dbg_pic_reg_print(0x00, 2)
        print('')
        time.sleep(1.0)

    # ---

    # #13(ADC with #12)  
    if False:
        slot = 8

        inter.i2c_select(8)
        while True:
            for i in range(4):
                ch = 0x88 + 0x10 * i
                # ch set
                inter.i2c_write_1byte(0x08, ch)
                time.sleep(0.1)
                # pre load
                inter.i2c_read(0x08, ch, 2)
                time.sleep(0.1)
                # load
                """
                vh = inter.i2c_read(0x08, ch, 1)
                vl = inter.i2c_read(0x08, ch, 1)
                dw = vh[0] * 16 + vl[0] / 16
                mv = (dw*488281-1000000000)/100000
                print(slot, i + 1, vh, vl, mv/1000)
                """
                val = inter.i2c_read(0x08, ch, 2)
                dw = val[0] * 16 + val[1] / 16
                mv = (dw*488281-1000000000)/100000
                print(slot, i + 1, hex(ch), val, mv/1000)
                time.sleep(0.1)
            print('')
            time.sleep(0.5)


    # #26 Reset & Write
    if False:
        inter.tpFPGA_write(4, './IR_Remote_bitmap.bin');

    # #26 start record etc...
    if False:
    #if True:
        #inter.tp26_start_record(4);
        #inter.tp26_get_record(4);
        inter.tp26_start_play(4);
    # #26 put play
    #if True:
    if False:
        with open('tp26_record.bin', 'rb') as f:
            vals = f.read()
        inter.tp26_put_play(4, vals);

        #inter.tp26_start_record(4);

    # #26 Reset
    if False:
        slot = 4
        inter.gpio_write(slot, 1, 1)
        inter.gpio_write(slot, 2, 0)
        inter.gpio_write(slot, 2, 1)
        time.sleep(0.01)
        inter.gpio_write(slot, 1, 0)
        inter.gpio_write(slot, 2, 0)
        inter.gpio_write(slot, 2, 1)
        time.sleep(0.01)
        inter.gpio_write(slot, 1, 1)

    # #52 Init & Read
    if False:
        slot = 3
        line = 3

        # Reset
        inter.gpio_write(slot, 3, 0)
        time.sleep(0.5)
        inter.gpio_write(slot, 3, 1)
        time.sleep(0.5)

        inter.i2c_select(slot)

        # 初期化
        inter.i2c_write_1byte(0x10, 0x03)
        #v = inter.i2c_read(0x10, 0, 15)
        #print(v, ' '.join(list(map(chr, v))))
        for i in range(4):
            #print('ch', i + 1, 'setting')
            inter.i2c_write_block_data(0x10, 0x02, [i, 0x1C])
            tbt52_int_wait(slot)
        #   param read(補正係数)
        inter.i2c_write_1byte(0x10, 0x06)
        tbt52_int_wait(slot)
        time.sleep(0.1) # 150Kbpsにしてさらにwait必要
        v = inter.i2c_read(0x10, 0, 16)
        print(list(map(hex, v)))
        err_comp = [0] * 4
        err_comp[0] = tbt52_error_compensation(v[0],  v[1],  v[2],  v[3])
        err_comp[1] = tbt52_error_compensation(v[4],  v[5],  v[6],  v[7])
        err_comp[2] = tbt52_error_compensation(v[8],  v[9],  v[10], v[11])
        err_comp[3] = tbt52_error_compensation(v[12], v[13], v[14], v[15])
        print(err_comp)
        tbt52_int_wait(slot)

        inter.i2c_select(0)
        
        # 電圧取得 
        while True:
            time.sleep(0.5) 
            inter.i2c_select(slot)
            flg = 0
            while True:
                while True:
                    time.sleep(0.1) 
                    inter.i2c_write_block_data(0x10, 0x01, [line])
                    tbt52_int_wait(slot)
                    v = inter.i2c_read(0x10, 0, 3)
                    print(list(map(hex, v)))
                    if v[2] & 0x80 == 0: break
                if flg == 0:
                    inter.i2c_write_block_data(0x10, 0x02, [line, 0x9C])
                    tbt52_int_wait(slot)
                    flg = 1
                else:
                    tmp = v[0] * 256 + v[1]
                    break

            if tmp <= 0x7FFF:
                sign = 1
            else:
                sign = -1
                tmp =  0xFFFF - tmp + 1

            volt = err_comp[line] * tmp / 1000000 + tmp * 0.00030517578125
            if sign < 0: volt = -volt

            print(volt, '[V]')
            inter.i2c_select(0)


    # #52 Ver Read
    if False:
        slot = 3
        # Reset
        inter.gpio_write(slot, 3, 0)
        time.sleep(0.5)
        inter.gpio_write(slot, 3, 1)
        time.sleep(0.5)

        inter.i2c_select(slot)
        inter.i2c_write_1byte(0x10, 0x03)
        v = inter.i2c_read(0x10, 0, 15)
        print(v, ' '.join(list(map(chr, v))))

    # #26(FPGA IR) Reset 
    if False:
        slot = 4
        # S04設定
        inter.spi_access(0, 3, 250, 1, 0, 0x94, [0x03, 0x00, 0x00]) # SPI設定
        """
        out = [0] * 1024
        inter.spi_access(4, 2, 500, 1, 0, 0x00, out)
        sys.exit();
        time.sleep(0.1)

        c_cmd = './c/spi4lattice 2 250 1 0x00 0 4 ./IR_Remote_bitmap.bin'
        c_ret = subprocess.Popen(c_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True)
        c_return = c_ret.wait()
        c_return -= 256 if c_return > 127 else c_return
        ret_bin = c_ret.stdout.readlines()
        print(c_return, ret_bin)
        """


    # #26(FPGA IR) Reset & SPI , 遅過ぎてボツ
    if False:
        slot = 4
        # S04設定
        inter.spi_access(0, 3, 250, 1, 0, 0x94, [0x00, 0x44, 0x42]) # GPIO設定 LineA,B,C = Out, D = In
        ret = inter.spi_access(0, 3, 250, 1, 0, 0x2A, [0])
        ret[0] &= 0xF0
        ret[0] |= 0x0F
        inter.spi_access(0, 3, 250, 1, 0, 0xAA, ret) # All High
        time.sleep(0.01)
        # CS = High の状態で、Clk = Low, High = FPGA Reset Assert
        ret[0] &= 0xFB # S4/LineB(SCLK) = Low
        inter.spi_access(0, 3, 250, 1, 0, 0xAA, ret)
        ret[0] |= 0x04 # S4/LineB(SCLK) = High
        inter.spi_access(0, 3, 250, 1, 0, 0xAA, ret)

        time.sleep(0.001) # 200nsのかわり
        
        # CS = Low の状態で、Clk = Low, High = FPGA Reset Deassert
        ret[0] &= 0xF7 # S4/LineA(CS) = Low
        inter.spi_access(0, 3, 250, 1, 0, 0xAA, ret)
        ret[0] &= 0xFB # S4/LineB(SCLK) = Low
        inter.spi_access(0, 3, 250, 1, 0, 0xAA, ret)
        ret[0] |= 0x04 # S4/LineB(SCLK) = High
        inter.spi_access(0, 3, 250, 1, 0, 0xAA, ret)

        # CS = Lowの状態でClk = Low
        ret[0] &= 0xFB # S4/LineB(SCLK) = Low
        inter.spi_access(0, 3, 250, 1, 0, 0xAA, ret)

        # S04設定
        #inter.spi_access(0, 3, 250, 1, 0, 0x94, [0x03, 0x00, 0x00]) # SPI設定
        """
        # CS = High
        ret[0] |= 0x08 # S4/LineA(CS) = High
        inter.spi_access(0, 3, 250, 1, 0, 0xAA, ret)
        """
        while True:
            ret[0] &= 0xFB # S4/LineB(SCLK) = Low
            inter.spi_access(0, 3, 250, 1, 0, 0xAA, ret)
            ret[0] |= 0x04 # S4/LineB(SCLK) = High
            inter.spi_access(0, 3, 250, 1, 0, 0xAA, ret)


    # #26(FPGA IR)
    if False:
        slot = 4
        # S04設定
        inter.spi_access(0, 3, 250, 1, 0, 0x94, [0x03, 0x00, 0x00]) # SPI設定
        time.sleep(0.5)

        ret = inter.spi_access(slot, 2, 100, 1, 0, 0x02, [8])
        print(ret)
        ret = inter.spi_access(slot, 2, 100, 1, 0, 0x00, [8])
        print(ret)
        ret = inter.spi_access(slot, 2, 100, 1, 0, 0x00, [8])
        print(ret)
        ret = inter.spi_access(slot, 2, 100, 1, 0, 0x00, [8])
        print(ret)

    # I2C Test
    # #16,17 Block Read
    if False:
        slot = 7
        # Reset
        inter.gpio_write(slot, 3, 0)
        time.sleep(0.5)
        inter.gpio_write(slot, 3, 1)
        time.sleep(0.5)

        while True:
            inter.i2c_select(slot)
            inter.i2c_write_block_data(0x03, 0xFE, [0, 0x99])
            inter.i2c_select(0)
            inter.i2c_select(slot)
            v = inter.i2c_read(0x03, 0, 1)
            print(hex(v[0]))
            inter.i2c_select(0)
            time.sleep(1)

    # #16,17 Block Write/Read
    if False:
        slot = 7
        # Reset
        inter.gpio_write(slot, 3, 0)
        time.sleep(0.5)
        inter.gpio_write(slot, 3, 1)
        time.sleep(0.5)

        inter.i2c_select(slot)
        inter.i2c_write_block_data(0x03, 0xFE, [0, 0x20])
        #inter.i2c_write_block_data(0x03, 0xFE, [0, 0x20, 1,2,3,4])
        inter.i2c_select(0)

        while True:
            inter.i2c_select(slot)
            inter.i2c_write_block_data(0x03, 0xFE, [0, 0x20])
            inter.i2c_select(0)
            inter.i2c_select(slot)
            print(inter.i2c_read(0x03, 0, 4))

    # #16,17,31 PWM-LineA
    if False: #mkxxx20180824
        slot = 2
        inter.board_init()
        # line設定
        inter.i2c_init(slot, 100)
        inter.gpio_init(slot, 3, LINE_SETTING_D_OUT_OD)
        inter.gpio_init(slot, 4, LINE_SETTING_D_IN)
        inter.pic_slot_init()

        # Reset
        inter.gpio_write(slot, 3, 0)
        time.sleep(0.01)
        inter.gpio_write(slot, 3, 1)
        time.sleep(0.01)

        # init
        pic_reg_write(inter, slot, 0x011D, [0x20, 0x00]) # APFCON0,1
        pic_reg_write(inter, slot, 0x029E, [0x24]) # CCPTMRS0
        lat = pic_reg_read(inter, slot, 0x010C, 3) # LATA,B,C
        lat[0] |= 0x03 # LATA
        lat[2] |= 0x03 # LATC 
        pic_reg_write(inter, slot, 0x010C, lat)
        tris = pic_reg_read(inter, slot, 0x008C, 3) # TRISA,B,C
        tris[0] |= 0x03 # TRISA
        tris[2] |= 0x03 # TRISC
        pic_reg_write(inter, slot, 0x008C, tris)

        # config 
        tris = pic_reg_read(inter, slot, 0x008C, 3) # TRISA,B,C
        ansel = pic_reg_read(inter, slot, 0x018C, 3) # ANSELA,B,C
        tris[0] |= 0x10 # RA4 入力へ
        tris[2] &= 0xDF # RC5 出力へ
        ansel[0] &= 0xEF # RA4 デジタル
        ansel[2] &= 0xDF # RC5 デジタル
        pic_reg_write(inter, slot, 0x008C, tris)
        pic_reg_write(inter, slot, 0x018C, ansel)

        # PWM設定
        pic_reg_write(inter, slot, 0x001B, [255]) # PR2
        pic_reg_write(inter, slot, 0x001C, [0x04]) # T2CON
        pic_reg_write(inter, slot, 0x0291, [0x40]) # CCPR1L
        pic_reg_write(inter, slot, 0x0293, [0x0C]) # CCP1CON

    # #16,17,31 PWM-LineB
    if False: #mkxxx20180824
        slot = 4
        inter.board_init()
        # line設定
        inter.i2c_init(slot, 150)
        inter.gpio_init(slot, 3, LINE_SETTING_D_OUT_OD)
        inter.gpio_init(slot, 4, LINE_SETTING_D_IN)
        inter.pic_slot_init()

        # Reset
        inter.gpio_write(slot, 3, 0)
        time.sleep(0.01)
        inter.gpio_write(slot, 3, 1)
        time.sleep(0.01)

        # init
        pic_reg_write(inter, slot, 0x011D, [0x20, 0x00]) # APFCON0,1
        pic_reg_write(inter, slot, 0x029E, [0x24]) # CCPTMRS0
        lat = pic_reg_read(inter, slot, 0x010C, 3) # LATA,B,C
        lat[0] |= 0x03 # LATA
        lat[2] |= 0x03 # LATC 
        pic_reg_write(inter, slot, 0x010C, lat)
        tris = pic_reg_read(inter, slot, 0x008C, 3) # TRISA,B,C
        tris[0] |= 0x03 # TRISA
        tris[2] |= 0x03 # TRISC
        pic_reg_write(inter, slot, 0x008C, tris)

        # config 
        tris = pic_reg_read(inter, slot, 0x008C, 3) # TRISA,B,C
        ansel = pic_reg_read(inter, slot, 0x018C, 3) # ANSELA,B,C
        tris[2] |= 0x10 # RC4入力へ
        tris[2] &= 0xF7 # RC3 出力へ
        ansel[2] &= 0xE7 # RC3,4 デジタル
        pic_reg_write(inter, slot, 0x008C, tris)
        pic_reg_write(inter, slot, 0x018C, ansel)

        # PWM設定
        pic_reg_write(inter, slot, 0x0416, [255]) # PR4
        pic_reg_write(inter, slot, 0x0417, [0x04]) # T4CON
        pic_reg_write(inter, slot, 0x0298, [0x40]) # CCPR2L
        pic_reg_write(inter, slot, 0x029A, [0x0C]) # CCP2CON

    # #16,17,31 PWM-LineC
    if False: #mkxxx20180824
        slot = 4
        inter.board_init()
        # line設定
        inter.i2c_init(slot, 100)
        inter.gpio_init(slot, 3, LINE_SETTING_D_OUT_OD)
        inter.gpio_init(slot, 4, LINE_SETTING_D_IN)
        inter.pic_slot_init()

        # Reset
        inter.gpio_write(slot, 3, 0)
        time.sleep(0.01)
        inter.gpio_write(slot, 3, 1)
        time.sleep(0.01)

        # init
        pic_reg_write(inter, slot, 0x011D, [0x20, 0x00]) # APFCON0,1
        pic_reg_write(inter, slot, 0x029E, [0x24]) # CCPTMRS0
        lat = pic_reg_read(inter, slot, 0x010C, 3) # LATA,B,C
        lat[0] |= 0x03 # LATA
        lat[2] |= 0x03 # LATC 
        tris = pic_reg_read(inter, slot, 0x008C, 3) # TRISA,B,C
        tris[0] |= 0x03 # TRISA
        tris[2] |= 0x03 # TRISC
        pic_reg_write(inter, slot, 0x008C, tris)

        # config 
        tris = pic_reg_read(inter, slot, 0x008C, 3) # TRISA,B,C
        ansel = pic_reg_read(inter, slot, 0x018C, 3) # ANSELA,B,C
        tris[0] &= 0xFB # RA2 出力へ
        ansel[0] &= 0xFB # RA2 デジタル
        pic_reg_write(inter, slot, 0x008C, tris)
        pic_reg_write(inter, slot, 0x018C, ansel)

        # PWM設定
        #pic_reg_write(inter, slot, 0x041D, [255]) # PR6
        #pic_reg_write(inter, slot, 0x041E, [0x04]) # T6CON
        #pic_reg_write(inter, slot, 0x0311, [0x40]) # CCPR3L
        #pic_reg_write(inter, slot, 0x0313, [0x0C]) # CCP3CON

        # PWM計算                
        #period = 0.125 # [us] 0.1(0.125)～2048
        period = 10 # [us] 0.1(0.125)～2048
        if period < 32.0:
            txcon = 0
            txcon_val = 1
            prx = round(period / 0.125)
        elif period < 128.0:
            txcon = 1
            txcon_val = 4
            prx = round(period / 0.5)
        elif period < 512.0:
            txcon = 2
            txcon_val = 16
            prx = round(period / 2.0)
        elif period <= 2048.0:
            txcon = 3
            txcon_val = 64
            prx = round(period / 8.0)
        else:
            print('period err', period)
        prx = prx - 1 if prx != 0 else 0 
        print('period =', period, txcon, txcon_val, prx)

        #pulse_width = 0.03125 # [us] 0～0.3125～period
        pulse_width = 5 # [us] 0～0.3125～period
        ccp10bit = round(pulse_width * 32 / txcon_val)
        ccpcon54 = (ccp10bit & 0x0003) << 4
        ccprxl = ccp10bit >> 2
        print('pulse_width =', pulse_width, txcon_val, ccp10bit, ccpcon54, ccprxl)

        # パラメータ表示
        print('1周期長さ=', period, '[us]')
        print('周波数=', 1./ period * 1000000, '[Hz]')

        print('パルス幅 =', pulse_width, '[us]')
        print('duty比 =', pulse_width / period * 100, '[%]')

        # PWM設定
        pic_reg_write(inter, slot, 0x041D, [prx]) # PR6
        pic_reg_write(inter, slot, 0x041E, [0x04 | txcon]) # T6CON
        pic_reg_write(inter, slot, 0x0311, [ccprxl]) # CCPR3L
        pic_reg_write(inter, slot, 0x0313, [0x0C | ccpcon54]) # CCP3CON

    # #31 GPIO-Out
    if False: 
        slot = 4
        line = 1
        inter.board_init()
        # line設定
        inter.i2c_init(slot, 100)
        inter.gpio_init(slot, 3, LINE_SETTING_D_OUT_OD)
        inter.gpio_init(slot, 4, LINE_SETTING_D_IN)
        inter.pic_slot_init()

        # Reset
        inter.gpio_write(slot, 3, 0)
        time.sleep(0.01)
        inter.gpio_write(slot, 3, 1)
        time.sleep(0.01)

        # init
        pic_reg_write(inter, slot, 0x011D, [0x20, 0x00]) # APFCON0,1
        pic_reg_write(inter, slot, 0x029E, [0x24]) # CCPTMRS0
        lat = pic_reg_read(inter, slot, 0x010C, 3) # LATA,B,C
        lat[0] |= 0x03 # LATA
        lat[2] |= 0x03 # LATC 
        pic_reg_write(inter, slot, 0x010C, lat)
        tris = pic_reg_read(inter, slot, 0x008C, 3) # TRISA,B,C
        tris[0] |= 0x03 # TRISA
        tris[2] |= 0x03 # TRISC
        pic_reg_write(inter, slot, 0x008C, tris)

        # config 
        lat = pic_reg_read(inter, slot, 0x010C, 3) # LATA,B,C
        tris = pic_reg_read(inter, slot, 0x008C, 3) # TRISA,B,C
        ansel = pic_reg_read(inter, slot, 0x018C, 3) # ANSELA,B,C
        if line == 1: # IO1
            lat[0] |= 0x10 # RA4
            lat[2] |= 0x20 # RC5
            tris[0] |= 0x10 # RA4 入力へ
            tris[2] &= 0xDF # RC5 出力へ
            ansel[0] |= 0x10 # RA4 アナログ
            ansel[2] &= 0xDF # RC5 デジタル
        elif line == 2: # IO2
            lat[2] |= 0x18 # RC3,4 
            tris[2] |= 0x10 # RC4入力へ
            tris[2] &= 0xF7 # RC3 出力へ
            ansel[2] |= 0x10 # RC4 アナログ
            ansel[2] &= 0xF7 # RC3 デジタル
        elif line == 3: # IO3
            lat[0] |= 0x04 # RA2
            tris[0] &= 0xFB # RA2 出力へ
            ansel[0] &= 0xFB # RA2 デジタル
        else: # IO4
            lat[2] |= 0x04 # RC2
            tris[2] &= 0xFB # RC2 出力へ
            ansel[2] &= 0xFB # RC2 デジタル
        pic_reg_write(inter, slot, 0x010C, lat)
        pic_reg_write(inter, slot, 0x008C, tris)
        pic_reg_write(inter, slot, 0x018C, ansel)

        flg = 1
        while True:
            flg = 0 if flg == 1 else 1
            port = pic_reg_read(inter, slot, 0x000C, 3) # PORTA,B,C
            if line == 1: # RC5
                if flg == 1:
                    port[2] |= 0x20
                else:
                    port[2] &= 0xDF
            elif line == 2: # RC3
                if flg == 1:
                    port[2] |= 0x08
                else:
                    port[2] &= 0xF7
            elif line == 3: # RA2
                if flg == 1:
                    port[0] |= 0x04
                else:
                    port[0] &= 0xFB
            else: # RC2
                if flg == 1:
                    port[2] |= 0x04
                else:
                    port[2] &= 0xFB

            time.sleep(0.01)
            pic_reg_write(inter, slot, 0x000C, port)

    # #31 GPIO-In
    if False:
        slot = 9
        line = 3

        # Reset
        inter.gpio_write(slot, 3, 0)
        time.sleep(0.01)
        inter.gpio_write(slot, 3, 1)
        time.sleep(0.01)

        # init
        pic_reg_write(inter, slot, 0x011D, [0x20, 0x00]) # APFCON0,1
        pic_reg_write(inter, slot, 0x029E, [0x24]) # CCPTMRS0
        lat = pic_reg_read(inter, slot, 0x010C, 3) # LATA,B,C
        lat[0] |= 0x03 # LATA
        lat[2] |= 0x03 # LATC 
        pic_reg_write(inter, slot, 0x010C, lat)
        tris = pic_reg_read(inter, slot, 0x008C, 3) # TRISA,B,C
        tris[0] |= 0x03 # TRISA
        tris[2] |= 0x03 # TRISC
        pic_reg_write(inter, slot, 0x008C, tris)

        # config 
        lat = pic_reg_read(inter, slot, 0x010C, 3) # LATA,B,C
        tris = pic_reg_read(inter, slot, 0x008C, 3) # TRISA,B,C
        ansel = pic_reg_read(inter, slot, 0x018C, 3) # ANSELA,B,C
        if line == 1: # IO1
            lat[0] |= 0x10 # RA4
            lat[2] |= 0x20 # RC5
            tris[0] |= 0x10 # RA4 入力へ
            tris[2] |= 0x20 # RC5 入力へ
            ansel[0] |= 0x10 # RA4 アナログ
            ansel[2] &= 0xDF # RC5 デジタル
        elif line == 2: # IO2
            lat[2] |= 0x18 # RC3,4 
            tris[2] |= 0x10 # RC4 入力へ
            tris[2] |= 0x08 # RC3 入力へ
            ansel[2] |= 0x10 # RC4 アナログ
            ansel[2] &= 0xF7 # RC3 デジタル
        elif line == 3: # IO3
            lat[0] |= 0x04 # RA2
            tris[0] |= 0x04 # RA2 入力へ
            ansel[0] &= 0xFB # RA2 デジタル
        else: # IO4
            lat[2] |= 0x04 # RC2
            tris[2] |= 0x04 # RC2 入力へ
            ansel[2] &= 0xFB # RC2 デジタル
        pic_reg_write(inter, slot, 0x010C, lat)
        pic_reg_write(inter, slot, 0x008C, tris)
        pic_reg_write(inter, slot, 0x018C, ansel)

        while True:
            port = pic_reg_read(inter, slot, 0x000C, 3) # PORTA,B,C
            if line == 1: # RC5
                val = 1 if port[2] & 0x20 else 0
            elif line == 2: # RC3
                val = 1 if port[2] & 0x08 else 0
            elif line == 3: # RA2
                val = 1 if port[0] & 0x04 else 0
            else: # RC2
                val = 1 if port[2] & 0x04 else 0

            print(val)
            time.sleep(0.5)

    # #31 ADC
    if False:
        slot = 9
        line = 1

        # Reset
        inter.gpio_write(slot, 3, 0)
        time.sleep(0.01)
        inter.gpio_write(slot, 3, 1)
        time.sleep(0.01)

        # init
        pic_reg_write(inter, slot, 0x011D, [0x20, 0x00]) # APFCON0,1
        pic_reg_write(inter, slot, 0x029E, [0x24]) # CCPTMRS0
        lat = pic_reg_read(inter, slot, 0x010C, 3) # LATA,B,C
        lat[0] |= 0x03 # LATA
        lat[2] |= 0x03 # LATC 
        pic_reg_write(inter, slot, 0x010C, lat)
        tris = pic_reg_read(inter, slot, 0x008C, 3) # TRISA,B,C
        tris[0] |= 0x03 # TRISA
        tris[2] |= 0x03 # TRISC
        pic_reg_write(inter, slot, 0x008C, tris)

        # config 
        lat = pic_reg_read(inter, slot, 0x010C, 3) # LATA,B,C
        tris = pic_reg_read(inter, slot, 0x008C, 3) # TRISA,B,C
        ansel = pic_reg_read(inter, slot, 0x018C, 3) # ANSELA,B,C
        if line == 1: # IO1
            lat[0] |= 0x10 # RA4
            lat[2] |= 0x20 # RC5
            tris[0] |= 0x10 # RA4 入力へ
            tris[2] |= 0x20 # RC5 入力へ
            ansel[0] |= 0x10 # RA4 アナログ
            ansel[2] &= 0xDF # RC5 デジタル
        elif line == 2: # IO2
            lat[2] |= 0x18 # RC3,4 
            tris[2] |= 0x10 # RC4 入力へ
            tris[2] |= 0x08 # RC3 入力へ
            ansel[2] &= 0xEF # RC4 デジタル
            ansel[2] |= 0x08 # RC3 アナログ
        elif line == 3: # IO3
            lat[0] |= 0x04 # RA2
            tris[0] |= 0x04 # RA2 入力へ
            ansel[0] |= 0x04 # RA2 アナログ
        else: # IO4
            lat[2] |= 0x04 # RC2
            tris[2] |= 0x04 # RC2 入力へ
            ansel[2] |= 0x04 # RC2 アナログ
        pic_reg_write(inter, slot, 0x010C, lat)
        pic_reg_write(inter, slot, 0x008C, tris)
        pic_reg_write(inter, slot, 0x018C, ansel)

        # ADC config 
        vref = 5 # 電圧設定
        adcon = pic_reg_read(inter, slot, 0x009E, 1) # ADCON1
        fvrcon = pic_reg_read(inter, slot, 0x0117, 1) # FVRCON
        if vref == 5:
            adcon[0] &= 0xFC # bit0,1 clear
            fvrcon[0] &= 0xFC # bit0,1 clear
        elif vref == 4.096:
            adcon[0] |= 0x03 # bit0,1 set
            fvrcon[0] |= 0x83 # bit0,1 = 11, bit7 set
        elif vref == 2.048:
            adcon[0] |= 0x03 # bit0,1 set
            fvrcon[0] &= 0xFC # bit0,1 = clear
            fvrcon[0] |= 0x82 # bit0,1 = 10, bit7 set
        else: # 1.024V
            adcon[0] |= 0x03 # bit0,1 set
            fvrcon[0] &= 0xFC # bit0,1 = clear
            fvrcon[0] |= 0x81 # bit0,1 = 01, bit7 set
        adcon[0] |= 0x80 # 右詰め
        adcon[0] |= 0x60 # Frc # サンプル時間設定 0x40:1us, 0x60:2us, 0x70:1-6us=Frc
        pic_reg_write(inter, slot, 0x009E, adcon) # ADCON1
        pic_reg_write(inter, slot, 0x0117, fvrcon) # FVRCON

        while True:
            if line == 1: # RA4=AN3
                val = 0x0C | 0x03
            elif line == 2: # RC3=AN7
                val = 0x1C | 0x03
            elif line == 3: # RA2=AN2
                val = 0x08 | 0x03
            else: # RC2=AN6
                val = 0x18 | 0x03
            pic_reg_write(inter, slot, 0x009D, [val]) # ADCON0, ADC開始
            while True:
                adc_chk = pic_reg_read(inter, slot, 0x009D, 1) # ADCON0
                if adc_chk[0] & 0x02 == 0: break

            adc_val = pic_reg_read(inter, slot, 0x009B, 2) # ADRESL/H
            calc_val = (adc_val[1] * 256 + adc_val[0]) * vref / 1024

            print(hex(adc_val[1]), hex(adc_val[0]), calc_val)
            time.sleep(0.5)

    # #31 UART
    if False: 
        slot = 9

        # Reset
        inter.gpio_write(slot, 3, 0)
        time.sleep(0.01)
        inter.gpio_write(slot, 3, 1)
        time.sleep(0.01)

        # init
        pic_reg_write(inter, slot, 0x011D, [0x20, 0x00]) # APFCON0,1
        pic_reg_write(inter, slot, 0x029E, [0x24]) # CCPTMRS0
        lat = pic_reg_read(inter, slot, 0x010C, 3) # LATA,B,C
        lat[0] |= 0x03 # LATA
        lat[2] |= 0x03 # LATC 
        pic_reg_write(inter, slot, 0x010C, lat)
        tris = pic_reg_read(inter, slot, 0x008C, 3) # TRISA,B,C
        tris[0] |= 0x03 # TRISA
        tris[2] |= 0x03 # TRISC
        pic_reg_write(inter, slot, 0x008C, tris)

        # config 
        lat = pic_reg_read(inter, slot, 0x010C, 3) # LATA,B,C
        tris = pic_reg_read(inter, slot, 0x008C, 3) # TRISA,B,C
        ansel = pic_reg_read(inter, slot, 0x018C, 3) # ANSELA,B,C

        lat[0] |= 0x10 # RA4
        lat[2] |= 0x20 # RC5 = RX
        tris[0] |= 0x10 # RA4 入力へ
        tris[2] |= 0x20 # RC5 入力へ
        ansel[0] &= 0xEF # RA4 デジタル
        #ansel[2] &= 0xDF # RC5 デジタル
        lat[2] |= 0x18 # RC3,4 
        tris[2] &= 0xE7 # RC3,4 出力へ
        ansel[2] &= 0xE7 # RC3,4 デジタル

        pic_reg_write(inter, slot, 0x010C, lat)
        pic_reg_write(inter, slot, 0x008C, tris)
        pic_reg_write(inter, slot, 0x018C, ansel)

        # UART config 
        #   RX割り込みEnable
        pie1 = pic_reg_read(inter, slot, 0x0091, 1) # PIE1
        pie1[0] |= 0x20
        pic_reg_write(inter, slot, 0x0091, pie1) 
        #   事前設定
        sta = pic_reg_read(inter, slot, 0x019D, 2) # RCSTA,TXSTA
        sta[0] &= 0x7F # SPEN = 0
        sta[1] &= 0xDF # SREN = 0
        pic_reg_write(inter, slot, 0x019D, sta) 
        uartflg = pic_reg_read(inter, slot, 0x007E, 1) # UARTFLAG(FW)
        uartflg[0] &= 0xBF # bit6 = 0
        uartflg[0] |= 0x80 # bit7 = 1
        pic_reg_write(inter, slot, 0x007E, uartflg) 
        #   baudrate設定
        txsta = pic_reg_read(inter, slot, 0x019E, 1) # TXSTA
        txsta[0] |= 0x04 # BRGH = 1
        pic_reg_write(inter, slot, 0x019E, txsta) 
        baudcon = pic_reg_read(inter, slot, 0x019F, 1) # BAUDCON
        baudcon[0] |= 0x08 # BRG16 = 1
        pic_reg_write(inter, slot, 0x019F, baudcon) 
        baud = 9600 
        if baud == 300:    
            spbrg = 26666
        elif baud == 600: 
            spbrg = 13332
        elif baud == 1200: 
            spbrg = 6666
        elif baud == 2400: 
            spbrg = 3332 
        elif baud == 4800: 
            spbrg = 1666
        elif baud == 9600: 
            spbrg = 832
        elif baud == 19200: 
            spbrg = 416
        elif baud == 38400: 
            spbrg = 208 
        elif baud == 57600: 
            spbrg = 138
        else: # 115.2k 
            spbrg = 68
        spbrgl = spbrg % 256
        spbrgh = spbrg >> 8
        pic_reg_write(inter, slot, 0x019B, [spbrgl, spbrgh]) # SPBRGL/H
        #   parity設定
        parity = 0 # 0:none, 1:odd, 2:even
        sta = pic_reg_read(inter, slot, 0x019D, 2) # RCSTA,TXSTA
        uartflg = pic_reg_read(inter, slot, 0x007E, 1) # UARTFLAG(FW)
        if parity == 0:
            sta[0] &= 0xBF # RX9 = 0
            sta[1] &= 0xBF # TX9 = 0
            uartflg[0] &= 0x8F # bit4-6 = 000
        elif parity == 1: # odd
            sta[0] |= 0x41 # RX9 = 1, RX9D = 1
            sta[1] |= 0x41 # TX9 = 1, TX9D = 1
            uartflg[0] &= 0x8F # bit6-4 = 000
            uartflg[0] |= 0x50 # bit6-4 = 101
        else: # even
            sta[0] |= 0x40 # RX9 = 1
            sta[1] |= 0x40 # TX9 = 1
            sta[0] &= 0xFE # RX9D = 0
            sta[1] &= 0xFE # TX9D = 0
            uartflg[0] &= 0x8F # bit6-4 = 000
            uartflg[0] |= 0x40 # bit6-4 = 100
        pic_reg_write(inter, slot, 0x019D, sta) 
        pic_reg_write(inter, slot, 0x007E, uartflg) 
        #   受信開始設定
        #   送信開始設定
        sta = pic_reg_read(inter, slot, 0x019D, 2) # RCSTA,TXSTA
        sta[0] |= 0x90 # SREN = 1, CREN = 1
        sta[1] |= 0x20 # TXEN = 1
        pic_reg_write(inter, slot, 0x019D, sta) 
        #uartflg = pic_reg_read(inter, slot, 0x007E, 1) # UARTFLAG(FW)
        #uartflg[0] |= 0x40 # bit6 = 1
        #pic_reg_write(inter, slot, 0x007E, uartflg) 
        #   割り込みpin設定
        trisa = pic_reg_read(inter, slot, 0x008C, 1) # TRISA
        trisa[0] &= 0xDF # RA5 出力へ
        pic_reg_write(inter, slot, 0x008C, trisa)


        while True:
            # 送信
            pic_reg_write(inter, slot, 0x0120, [0x30, 0x31, 0x32, 0x33]) # TX_BUFF(FW), '0123'
            pic_reg_write(inter, slot, 0x0077, [4]) # TX_BYTE(FW), 
            # 受信割り込み確認後受信
            #   割り込み確認省略
            while True: # 受信byte数2度読み
                num1 = pic_reg_read(inter, slot, 0x0076, 1) # RX_BYTE(FW)
                num2 = pic_reg_read(inter, slot, 0x0076, 1) # RX_BYTE(FW)
                if num1[0] == num2[0]: break
            if num1[0] > 0:
                pic_reg_write(inter, slot, 0x0076, [0]) # RX_BYTE(FW), 
                val = pic_reg_read(inter, slot, 0x00A0, num1[0]) # RX_BUFF(FW)
                print(num1, val)

            time.sleep(0.5)

    # #29Block Test(Temp)
    while False: 
        begin_time = time.time()
        inter.i2c_select(5)
        ret = inter.i2c_read(0x18, 0x05, 2)
        val = (ret[0] & 0x0F) * 16 + ret[1] / 16
        print(ret, val)
        inter.i2c_select()
        end_time = time.time()
        print('                   ', (end_time - begin_time)*1000, 'ms')
        #time.sleep(0.1)

    # #22Block Test(Temp)
    while False: 
        begin_time = time.time()
        ret = inter.tp22_temp(2)
        print(ret)
        end_time = time.time()
        print('                   ', (end_time - begin_time)*1000, 'ms')

    # #22Block Test(Version)
    if False: 
        inter.i2c_write_tp22(6, 0x03)
        ret = inter.i2c_read_tp22(6, 16)
        print(ret)

    # #22Block Test
    if False:
        #subprocess.call(['sudo', '/home/pi/P2/src/20180518b/py/c/a.out'])
        while True:
            inter.i2c_select(6)
            inter.i2c_write_1byte(0x0D, 0x03)
            ret = inter.i2c_read(0x0D, 0x80, 16)
            ver = ''
            for char in ret: 
                ver += chr(char)
            print(ret, ver)
            #time.sleep(0.1)


    # Block Line Test（LED点灯させる）
    while False:
        inter.dbg_pic_reg_print(0x00, 0x3D)
        for slot in range(1, 11):
            for line in range(1, 5):
                inter.gpio_write(slot, line, 0)
        for slot in range(1, 11):
            for line in range(1, 5):
                inter.gpio_write(slot, line, 1)

    # Led Test
    while False:
        for led in range(1, 5):
            inter.rp_led(led, 1)
            time.sleep(0.5)
            inter.rp_led(led, 0)
    # Button & Buzzer Test
    while False:
        md = GPIO.input(24)
        rst = GPIO.input(23)
        print('MD =', md, 'RST =', rst)
        if md == 0 or rst == 0:
            inter.rp_buzzer(1)
        else:
            inter.rp_buzzer(0)
        time.sleep(0.1)

    # GPIO Out(Raw)
    if False: 
        inter.dbg_pic_reg_print(0x00, 0x3D)
        # S06設定
        ret = inter.spi_access(3, 500, 1, 0, 0x9A, [0x00, 0x40])
        # S06出力
        while True:
            ret = inter.spi_access(3, 500, 1, 0, 0xAB, [0x00])
            time.sleep(1)
            ret = inter.spi_access(3, 500, 1, 0, 0xAB, [0x08])
            time.sleep(1)

    # GPIO IN Test
    if True: #mkxxx20180827
        inter.spi_init(1, 250)
        start_slot = 1
        end_slot = 10
        inter.board_init()
        # 全slot全line 設定
        for i in range(start_slot, end_slot + 1): 
            for j in range(1,5): 
                inter.gpio_init(i, j, LINE_SETTING_D_IN)
        inter.pic_slot_init()
        inter.dbg_pic_reg_print(0x00, 0x29)
       
    # GPIO Out Test
    if False: #mkxxx20180824
        start_slot = 1
        end_slot = 10
        inter.board_init()
        # 全slot全line 設定
        for i in range(start_slot, end_slot + 1): 
            for j in range(1,5): 
                inter.gpio_init(i, j, LINE_SETTING_D_OUT_OD)
        inter.pic_slot_init()
        #inter.dbg_pic_reg_print(0x00, 0x29)
       
        time.sleep(1)
        inter.gpio_write(4, 2, 0)
        while True:
            time.sleep(0.01)

    # GPIO Out
    if False: #mkxxx20180823
        start_slot = 1
        end_slot = 10
        inter.board_init()
        # 全slot全line 設定
        for i in range(start_slot, end_slot + 1): 
            for j in range(1,5): 
                inter.gpio_init(i, j, LINE_SETTING_D_OUT_OD)
        inter.pic_slot_init()
        #inter.dbg_pic_reg_print(0x00, 0x29)
        
        while True:
            for i in range(start_slot, end_slot + 1):
                for j in range(1,5):
                    inter.gpio_write(i, j, 1)
                    time.sleep(0.01)
            for i in range(start_slot, end_slot + 1):
                for j in range(1,5):
                    inter.gpio_write(i, j, 0)
                    time.sleep(0.01)

    # GPIO Out/In
    if False:
        flg = 0
        for i in range(10):
            inter.gpio_write(1, 1, 0)
            time.sleep(0.1)
        while True:
            out_slot = 5
            in_slot  = 4
            for i in range(1,5):
                inter.gpio_write(out_slot, i, flg)
                v = inter.gpio_read(in_slot, i)
                print(in_slot, i, v)
                time.sleep(0.5)
            print('')
            flg = 0 if flg == 1 else 1

    # Analog read
    if False:
        while True:
            slot = 1
            for i in range(1,5):
                v = inter.analog_read(slot, i)
                print(slot, i, v)
                time.sleep(0.1)
            time.sleep(0.5)
            print('')

    # SPI (slot 1～10)
    while False:
        slot = 7
        ret = inter.spi_access(slot, 3, 500, 1, 1, 0x00, [0, 0, 0, 0, 0, 0])
        print(ret)
        time.sleep(0.5)

    if False:
        dat = [0] * 30
        ret = inter.spi_access(3, 50, 1, 1, 0x8B, dat)
        print(ret)

    if False:
        #inter.spi_select(0)
        #ret = inter.spi_access(3, 50, 1, 1, 0xA6, [0, 0x22, 0x22])
        #print(ret)
        #inter.spi_select()
        #time.sleep(0.01)

        for addr in range(0x0B, 0x29, 3):
            inter.spi_select(0)
            ret = inter.spi_access(3, 50, 1, 1, addr, [0, 0, 0])
            print(ret)
            inter.spi_select()
            time.sleep(0.01)

    if False:
        dat = [0] * 30
        ret = inter.spi_access(3, 500, 1, 0, 0x0B, dat)
        print(ret)

    if False:
        inter.gpio_event_init('', 1, 1)
        inter.gpio_event_init('', 10, 4)
        #inter.gpio_event_callback_test(13)

    if False:
        inter.serial_event_callback_test(20)

    while False:
        inter.rp_led(1, 1)
        inter.rp_led(2, 0)
        inter.rp_led(3, 1)
        inter.rp_led(4, 0)
        time.sleep(1)
        inter.rp_led(1, 0)
        inter.rp_led(2, 1)
        inter.rp_led(3, 0)
        inter.rp_led(4, 1)
        time.sleep(1)
