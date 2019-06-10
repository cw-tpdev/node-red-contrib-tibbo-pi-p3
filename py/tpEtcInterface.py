#!/usr/bin/python3
import os, sys
import time
from tpBoardInterface import TpBoardInterface
import tpUtils
import math

class TpEtcInterface:
    """
    特殊なTibbitや外部インターフェースの設定を行います。
    """

    def __init__(self, board_inter):
        """ コンストラクタ
            board_inter : tpBoardInterfaceのインスタンス
        """
        # 設定
        # #22
        self.__inter = board_inter
        self.__tp22_wait_max_ms = 100
        self.__tp22_retry_num = 100
        self.__RTD_A = 3.9080e-3
        self.__RTD_B = -5.870e-7

        # #52
        self.__tp52_err_comp = [[0, 0, 0, 0] for i in range(10)]
 
    def tp22_init(self, slot):
        """ Tibbit #22 初期化
            slot : 'S01' ~ 'S10'
            戻り : なし
        """
        slot_num = tpUtils.slot_str_to_int(slot)
        # Reset
        self.__inter.gpio_write(slot, 'C', 0)
        time.sleep(0.1)
        self.__inter.gpio_write(slot, 'C', 1)
        time.sleep(0.1)
        return

    def tp22_get_temp(self, slot, pt_kind):
        """ Tibbit #22 温度測定用
            slot    : 'S01' ~ 'S10'
            pt_kind : 'PT100', 'PT200', 'PT500', 'PT1000'
            戻り    : 温度
        """
        #print('tp22_get_temp', slot, pt_kind)
        # reset
        #self.__inter.gpio_write(slot, 'C', '0')
        #self.__inter.gpio_write(slot, 'C', '1')

        # 温度読み込み
        for i in range(self.__tp22_retry_num): 
            for j in range(self.__tp22_retry_num): 
                c_ret, rtd = self.__inter.tp22_temp(slot)
                #print('tp22_get_temp', c_ret, rtd)
                if rtd % 2 == 1: # c_retエラー時は、rtd=-999999で戻るので、このチェックでOK
                    time.sleep(0.2)
                    continue
                else: 
                    break
            else:
                raise ValueError('Tibbit #22 RTD retry error! ' + str(c_ret) + ', ' + str(rtd))
            temp = self.__tp22_temp(rtd, pt_kind)
            if temp < -240: 
                time.sleep(0.1)
                continue
            else: 
                break
        else:
            raise ValueError('Tibbit #22 -240 retry error! ' + str(temp))
        return round(temp, 2)

    def tp22_get_ver(self, slot):
        """ Tibbit #22 バージョン取得
            slot : 'S01' ~ 'S10'
            戻り : バージョン情報
        """
        #print('tp22_get_ver', slot)
        self.__inter.i2c_write_tp22(slot, 0x03)
        ret = self.__inter.i2c_read_tp22(slot, 16)
        ver = ''
        for i in ret: ver += chr(i)
        #print(ver)
        return ver

    def tpFPGA_write(self, slot, file_path):
        """ FPGA Tibbit(#26,57), FPGAリセット＆書き込み
            slot      : 'S01' ~ 'S10'
            file_path : binイメージのファイル名フルパス
            戻り      : なし
        """
        self.__inter.tpFPGA_write(slot, file_path)
        return

    def tp26_start_record(self, slot):
        """ #26 記録開始
            slot      : 'S01' ~ 'S10'
            戻り      : なし
        """
        self.__inter.tp26_start_record(slot)
        return

    def tp26_get_record(self, slot):
        """ #26 記録読み込み
            slot      : 'S01' ~ 'S10'
            戻り      : byte配列
        """
        return self.__inter.tp26_get_record(slot)

    def tp26_put_play(self, slot, vals):
        """ #26 記録書き込み
            slot : 'S01' ~ 'S10'
            vals : 記録したバイナリ配列
            戻り : なし
        """
        self.__inter.tp26_put_play(slot, vals)
        return

    def tp26_start_play(self, slot):
        """ #26 再生開始
            slot : 'S01' ~ 'S10'
            戻り : なし
        """
        self.__inter.tp26_start_play(slot)
        return

    def tp52_init(self, slot):
        """ #52 初期化＆補正値確保
            slot : 'S01', 'S03', 'S07', 'S09'
            戻り : なし
        """
        slot_num = tpUtils.slot_str_to_int(slot)
        if slot_num != 1 and slot_num != 3 and slot_num != 7 and slot_num != 9:
            raise ValueError('tp52_init error! : slot = ' + slot)
        # Reset
        self.__inter.gpio_write(slot, 'C', 0)
        time.sleep(0.1)
        self.__inter.gpio_write(slot, 'C', 1)
        time.sleep(0.1)

        # 初期化
        # I2Cはconfigで150kbpsに設定すること
        self.__inter.i2c_write(slot, 0x10, [0x03])
        for i in range(4):
            self.__inter.i2c_write_with_cmd(slot, 0x10, 0x02, [i, 0x1C])
            self.__tp52_int_wait(slot)
        #   param read(補正係数)
        self.__inter.i2c_write(slot, 0x10, [0x06])
        self.__tp52_int_wait(slot)
        time.sleep(0.1) # 150Kbpsにしてさらにwait必要
        v = self.__inter.i2c_read_with_cmd(slot, 0x10, 0, 16)
        #print(slot, list(map(hex, v)))
        self.__tp52_err_comp[slot_num - 1][0] = self.__tp52_error_compensation(v[0],  v[1],  v[2],  v[3])
        self.__tp52_err_comp[slot_num - 1][1] = self.__tp52_error_compensation(v[4],  v[5],  v[6],  v[7])
        self.__tp52_err_comp[slot_num - 1][2] = self.__tp52_error_compensation(v[8],  v[9],  v[10], v[11])
        self.__tp52_err_comp[slot_num - 1][3] = self.__tp52_error_compensation(v[12], v[13], v[14], v[15])
        #print(slot, self.__tp52_err_comp[slot_num - 1])
        self.__tp52_int_wait(slot)
        return

    def tp52_get_volt(self, slot, ch):
        """ #52 初期化＆補正値確保
            slot : 'S01', 'S03', 'S07', 'S09'
            ch   : 'CH1'~'CH4'
            戻り : 測定値16bitデータ
        """
        slot_num = tpUtils.slot_str_to_int(slot)
        if slot_num != 1 and slot_num != 3 and slot_num != 7 and slot_num != 9:
            raise ValueError('tp52_get_volt error! : slot = ' + slot)
        ch_num = int(ch[2])
        if ch_num < 1 or ch_num > 4:
            raise ValueError('tp52_get_volt error! : ch = ' + ch)

        flg = 0
        count = 0
        while True:
            while True:
                time.sleep(0.1)
                self.__inter.i2c_write_with_cmd(slot, 0x10, 0x01, [ch_num - 1])
                self.__tp52_int_wait(slot)
                v = self.__inter.i2c_read_with_cmd(slot, 0x10, 0, 3)
                if v[2] & 0x80 == 0: break
                count += 1
                if count > 20:
                    self.tp52_init(slot)
                    count = 0
                    flg = 0
            if flg == 0:
                self.__inter.i2c_write_with_cmd(slot, 0x10, 0x02, [ch_num - 1, 0x9C])
                self.__tp52_int_wait(slot)
                flg = 1
            else:
                tmp = v[0] * 256 + v[1]
                break
        return tmp
        """ 生値からのvolt計算方法は以下
        if tmp <= 0x7FFF:
            sign = 1
        else:
            sign = -1
            tmp =  0xFFFF - tmp + 1

        volt = self.__tp52_err_comp[ch_num - 1] * tmp / 1000000 + tmp * 0.00030517578125
        if sign < 0: volt = -volt

        return volt
        """
        
    def tp52_get_correct(self, slot, ch):
        """ #52 補正値を返す
            slot : 'S01', 'S03', 'S07', 'S09'
            ch   : 'CH1'~'CH4'
            戻り : 補正値
        """
        slot_num = tpUtils.slot_str_to_int(slot)
        if slot_num != 1 and slot_num != 3 and slot_num != 7 and slot_num != 9:
            raise ValueError('tp52_get_correct error! : slot = ' + slot)
        ch_num = int(ch[2])
        if ch_num < 1 or ch_num > 4:
            raise ValueError('tp52_get_correct error! : ch = ' + ch)
        return self.__tp52_err_comp[slot_num - 1][ch_num - 1]

   # 内部メソッド ---

    def __tp22_check(self, slot):
        begin_time = time.time()
        while True:
            ret = self.__inter.gpio_read(slot, 'D')
            if ret == 1: break # Highになるまでwait
            cur_time = time.time()
            if (cur_time - begin_time) * 1000 > self.__tp22_wait_max_ms:
                raise ValueError('Tibbit #22 wait error!')

    def __tp22_temp(self, rtd, pt_kind):
        rtd /= 2;

        if pt_kind == 'PT100':
            normal_0_resist = 100.0
        elif pt_kind == 'PT200':
            normal_0_resist = 200.0
        elif pt_kind == 'PT500':
            normal_0_resist = 500.0
        elif pt_kind == 'PT1000':
            normal_0_resist = 1000.0
        else:
            raise ValueError('Tibbit #22 PT kind error!')

        rtd_rref = 4000.0
        a2 = 2.0 * self.__RTD_B
        b_sq = self.__RTD_A * self.__RTD_A

        rtd_resist = normal_0_resist
        resist = rtd * rtd_rref / 32768.0

        c = 1.0 - (resist / rtd_resist)
        d = b_sq - 2.0 * a2 * c
        if d < 0: return -999 # 平方根取れない場合

        data = math.sqrt(d)
        data = (-self.__RTD_A + data) / a2;

        return data

    def __tp52_int_wait(self, slot):
        while True:
            v = self.__inter.gpio_read(slot, 'D')
            if v == 1: break

    def __tp52_error_compensation(self, v0, v1, v2, v3):
        r = v1 * 0x10000 + v2 * 0x100 + v3
        ret = r / 1000000
        ret += v0 * 0x1000000
        if v0 & 0x80: ret = -ret
        return ret

