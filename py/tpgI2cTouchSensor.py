import sys
from tp00 import Tp00
import tpUtils
from constant import *
import json
import time

# Register addresses.
MPR121_I2CADDR_DEFAULT = 0x5A
MPR121_TOUCHSTATUS_L = 0x00
MPR121_TOUCHSTATUS_H = 0x01
MPR121_FILTDATA_0L = 0x04
MPR121_FILTDATA_0H = 0x05
MPR121_BASELINE_0 = 0x1E
MPR121_MHDR = 0x2B
MPR121_NHDR = 0x2C
MPR121_NCLR = 0x2D
MPR121_FDLR = 0x2E
MPR121_MHDF = 0x2F
MPR121_NHDF = 0x30
MPR121_NCLF = 0x31
MPR121_FDLF = 0x32
MPR121_NHDT = 0x33
MPR121_NCLT = 0x34
MPR121_FDLT = 0x35
MPR121_TOUCHTH_0 = 0x41
MPR121_RELEASETH_0 = 0x42
MPR121_DEBOUNCE = 0x5B
MPR121_CONFIG1 = 0x5C
MPR121_CONFIG2 = 0x5D
MPR121_CHARGECURR_0 = 0x5F
MPR121_CHARGETIME_1 = 0x6C
MPR121_ECR = 0x5E
MPR121_AUTOCONFIG0 = 0x7B
MPR121_AUTOCONFIG1 = 0x7C
MPR121_UPLIMIT = 0x7D
MPR121_LOWLIMIT = 0x7E
MPR121_TARGETLIMIT = 0x7F
MPR121_GPIODIR = 0x76
MPR121_GPIOEN = 0x77
MPR121_GPIOSET = 0x78
MPR121_GPIOCLR = 0x79
MPR121_GPIOTOGGLE = 0x7A
MPR121_SOFTRESET = 0x80


class TpgI2cTouchSensor:
    """
    TP Grove - I2C Touch Sensor
    """

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """

        self.slot = slot
        self.comm = I2C
        self.host = host

        # アドレス
        self.i2c_addr = 0x5A

        self.tp00 = Tp00(self.slot, self.comm, self.host)
        self.tp00.start()

        self.__reset()

    def __reset(self):
        """
        初期化
        """
        # Lock
        self.tp00.lock(self.slot)
        try:

            # リセット
            send_data = []
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_SOFTRESET, "v": [0x63]})
            self.tp00.send(json.dumps(send_data))
            time.sleep(0.001)

            # デフォルト値の設定
            send_data = []
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_ECR, "v": [0x00]})
            self.tp00.send(json.dumps(send_data))

            # デフォルト値の確認
            send_data = []
            send_data.append(
                {"act": "r", "add": self.i2c_addr, "cmd": MPR121_CONFIG2, "len": 1})
            _result = self.tp00.send(json.dumps(send_data))
            result_data = json.loads(_result.decode())
            c = result_data[0][0]

            if c != 0x24:
                raise ValueError('TpgI2cTouchSensor init failed.')

            # しきい値の設定
            self.__set_thresholds(12, 6)

            # 制御レジスタの構成
            send_data = []
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_MHDR, "v": [0x01]})
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_NHDR, "v": [0x01]})
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_NCLR, "v": [0x0E]})
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_FDLR, "v": [0x00]})
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_MHDF, "v": [0x01]})
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_NHDF, "v": [0x05]})
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_NCLF, "v": [0x01]})
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_FDLF, "v": [0x00]})
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_NHDT, "v": [0x00]})
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_NCLT, "v": [0x00]})
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_FDLT, "v": [0x00]})

            # Set other configuration registers.
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_DEBOUNCE, "v": [0]})
            # default, 16uA charge current
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_CONFIG1, "v": [0x10]})
            # 0.5uS encoding, 1ms period
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_CONFIG2, "v": [0x20]})
            # Enable all electrodes.
            # start with first 5 bits of baseline tracking
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_ECR, "v": [0x8F]})

            self.tp00.send(json.dumps(send_data))

        finally:
            # unLock
            self.tp00.unlock(self.slot)

    def __set_thresholds(self, touch, release):
        """
        提供されたすべての入力のタッチおよびリリースのしきい値を設定する
        touchとreleaseの値は0〜255の間の値でなければなりません
        """
        assert touch >= 0 and touch <= 255, 'touch must be between 0-255 (inclusive)'
        assert release >= 0 and release <= 255, 'release must be between 0-255 (inclusive)'
        for i in range(12):
            send_data = []
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_TOUCHTH_0 + 2*i, "v": [touch]})
            send_data.append(
                {"act": "w", "add": self.i2c_addr, "cmd": MPR121_RELEASETH_0 + 2*i, "v": [release]})
            self.tp00.send(json.dumps(send_data))

    def get_data(self):
        """
        値を取得します。
        """
        send_data = []
        send_data.append(
            {"act": "r", "add": self.i2c_addr, "cmd": MPR121_TOUCHSTATUS_L, "len": 2})
        _result = self.tp00.send(json.dumps(send_data))
        result_data = json.loads(_result.decode())

        ret1 = result_data[0][0]
        ret2 = result_data[0][1] * 256
        current_touched = (ret1 + ret2) & 0x0FFF

        objRet = []
        for i in range(12):
            pin_bit = 1 << i
            flg = 0
            if current_touched & pin_bit:
                # touched
                flg = 1

            objRet.append(flg)

        return objRet


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
        tpgI2cTouchSensor = TpgI2cTouchSensor(slot, host)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            recv_data = tpgI2cTouchSensor.get_data()
            tpUtils.nodeOut(json.dumps(recv_data))
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
            tpUtils.nodeOut("")
