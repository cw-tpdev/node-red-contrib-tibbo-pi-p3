
import tpUtils
import sys
from constant import *
import json
from tp31 import Tp31
import time


class Tp16_out(Tp31):
    """
    #16 Three PWMs with open collector outputs
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """
        super().__init__(slot, host)

    def start(self):
        """
        開始処理
        """

        #-----------
        # 共通
        #-----------

        # Lock
        self.tcp_client.lock(self.slot)
        try:

            # リセット
            self.pic_reg_reset()

            time.sleep(0.1)

            # init
            self.pic_reg_write(0x011D, [0x20, 0x00])  # APFCON0,1
            self.pic_reg_write(0x029E, [0x24])  # CCPTMRS0
            lat = self.pic_reg_read(0x010C, 3)  # LATA,B,C
            lat[0] |= 0x03  # LATA
            lat[2] |= 0x03  # LATC
            self.pic_reg_write(0x010C, lat)
            tris = self.pic_reg_read(0x008C, 3)  # TRISA,B,C
            tris[0] |= 0x03  # TRISA
            tris[2] |= 0x03  # TRISC
            self.pic_reg_write(0x008C, tris)

            #-----------
            # ch:1
            #-----------

            tris = self.pic_reg_read(0x008C, 3)  # TRISA,B,C
            ansel = self.pic_reg_read(0x018C, 3)  # ANSELA,B,C
            tris[0] |= 0x10  # RA4 入力へ
            tris[2] &= 0xDF  # RC5 出力へ
            ansel[0] &= 0xEF  # RA4 デジタル
            ansel[2] &= 0xDF  # RC5 デジタル
            self.pic_reg_write(0x008C, tris)
            self.pic_reg_write(0x018C, ansel)

            #-----------
            # ch:2
            #-----------

            tris = self.pic_reg_read(0x008C, 3)  # TRISA,B,C
            ansel = self.pic_reg_read(0x018C, 3)  # ANSELA,B,C
            tris[2] |= 0x10  # RC4入力へ
            tris[2] &= 0xF7  # RC3 出力へ
            ansel[2] &= 0xE7  # RC3,4 デジタル
            self.pic_reg_write(0x008C, tris)
            self.pic_reg_write(0x018C, ansel)

            #-----------
            # ch:3
            #-----------

            # config
            tris = self.pic_reg_read(0x008C, 3)  # TRISA,B,C
            ansel = self.pic_reg_read(0x018C, 3)  # ANSELA,B,C
            tris[0] &= 0xFB  # RA2 出力へ
            ansel[0] &= 0xFB  # RA2 デジタル
            self.pic_reg_write(0x008C, tris)
            self.pic_reg_write(0x018C, ansel)

        finally:
            # unLock
            self.tcp_client.unlock(self.slot)

    def send(self, msg):
        """
        データを送信します。
        """

        # Lock
        self.tcp_client.lock(self.slot)
        try:

            datas = json.loads(msg)

            for data in datas:

                # ch
                ch = data['ch']
                # 1周期長さ[us] 0.1(0.125)～2048
                period = data['period']
                # パルス幅 [us] 0～0.3125～period
                pulse_width = data['pulse_width']

                # PWM計算
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
                    raise ValueError('period error!')
                prx = prx - 1 if prx != 0 else 0

                if pulse_width < 0 or pulse_width > period:
                    raise ValueError('pulse_width error!')

                ccp10bit = round(pulse_width * 32 / txcon_val)
                ccpcon54 = (ccp10bit & 0x0003) << 4
                ccprxl = ccp10bit >> 2

                # パラメータ表示例
                #print('1周期長さ=', period, '[us]')
                #print('周波数=', 1. / period * 1000000, '[Hz]')
                #print('パルス幅 =', pulse_width, '[us]')
                #print('duty比 =', pulse_width / period * 100, '[%]')

                if ch == 1:

                    self.pic_reg_write(0x001B, [prx])   # PR2
                    self.pic_reg_write(0x001C, [0x04 | txcon])  # T2CON
                    self.pic_reg_write(0x0291, [ccprxl])  # CCPR1L
                    self.pic_reg_write(0x0293, [0x0C | ccpcon54])  # CCP1CON

                elif ch == 2:

                    self.pic_reg_write(0x0416, [prx])   # PR4
                    self.pic_reg_write(0x0417, [0x04 | txcon])  # T4CON
                    self.pic_reg_write(0x0298, [ccprxl])  # CCPR2L
                    self.pic_reg_write(0x029A, [0x0C | ccpcon54])  # CCP2CON

                elif ch == 3:

                    self.pic_reg_write(0x041D, [prx])   # PR6
                    self.pic_reg_write(0x041E, [0x04 | txcon])  # T6CON
                    self.pic_reg_write(0x0311, [ccprxl])  # CCPR3L
                    self.pic_reg_write(0x0313, [0x0C | ccpcon54])  # CCP3CON

        finally:
            # unLock
            self.tcp_client.unlock(self.slot)


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
        tp16_out = Tp16_out(slot, host)
        tp16_out.start()
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            tp16_out.send(data)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
