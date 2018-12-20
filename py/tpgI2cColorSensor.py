import sys
from tp00 import Tp00
import tpUtils
from constant import *
import json
import time
from tpConfig import TpConfig


class TpgI2cColorSensor:
    """
    TP Grove - I2C Color Sensor
    """

    TCS34725_COMMAND_BIT = 0x80

    TCS34725_ENABLE = 0x00
    # RGBC Interrupt Enable
    TCS34725_ENABLE_AIEN = 0x10
    # Wait enable - Writing 1 activates the wait timer
    TCS34725_ENABLE_WEN = 0x08
    # RGBC Enable - Writing 1 actives the ADC, 0 disables it
    TCS34725_ENABLE_AEN = 0x02
    # Power on - Writing 1 activates the internal oscillator, 0 disables it
    TCS34725_ENABLE_PON = 0x01
    # Integration time
    TCS34725_ATIME = 0x01
    # Wait time (if TCS34725_ENABLE_WEN is asserted)
    TCS34725_WTIME = 0x03
    # WLONG0 = 2.4ms   WLONG1 = 0.029s
    TCS34725_WTIME_2_4MS = 0xFF
    # WLONG0 = 204ms   WLONG1 = 2.45s
    TCS34725_WTIME_204MS = 0xAB
    # WLONG0 = 614ms   WLONG1 = 7.4s
    TCS34725_WTIME_614MS = 0x00
    # Clear channel lower interrupt threshold
    TCS34725_AILTL = 0x04
    TCS34725_AILTH = 0x05
    # Clear channel upper interrupt threshold
    TCS34725_AIHTL = 0x06
    TCS34725_AIHTH = 0x07
    # Persistence register - basic SW filtering mechanism for interrupts
    TCS34725_PERS = 0x0C
    # Every RGBC cycle generates an interrupt
    TCS34725_PERS_NONE = 0b0000
    # 1 clean channel value outside threshold range generates an interrupt
    TCS34725_PERS_1_CYCLE = 0b0001
    # 2 clean channel values outside threshold range generates an interrupt
    TCS34725_PERS_2_CYCLE = 0b0010
    # 3 clean channel values outside threshold range generates an interrupt
    TCS34725_PERS_3_CYCLE = 0b0011
    # 5 clean channel values outside threshold range generates an interrupt
    TCS34725_PERS_5_CYCLE = 0b0100
    # 10 clean channel values outside threshold range generates an interrupt
    TCS34725_PERS_10_CYCLE = 0b0101
    # 15 clean channel values outside threshold range generates an interrupt
    TCS34725_PERS_15_CYCLE = 0b0110
    # 20 clean channel values outside threshold range generates an interrupt
    TCS34725_PERS_20_CYCLE = 0b0111
    # 25 clean channel values outside threshold range generates an interrupt
    TCS34725_PERS_25_CYCLE = 0b1000
    # 30 clean channel values outside threshold range generates an interrupt
    TCS34725_PERS_30_CYCLE = 0b1001
    # 35 clean channel values outside threshold range generates an interrupt
    TCS34725_PERS_35_CYCLE = 0b1010
    # 40 clean channel values outside threshold range generates an interrupt
    TCS34725_PERS_40_CYCLE = 0b1011
    # 45 clean channel values outside threshold range generates an interrupt
    TCS34725_PERS_45_CYCLE = 0b1100
    # 50 clean channel values outside threshold range generates an interrupt
    TCS34725_PERS_50_CYCLE = 0b1101
    # 55 clean channel values outside threshold range generates an interrupt
    TCS34725_PERS_55_CYCLE = 0b1110
    # 60 clean channel values outside threshold range generates an interrupt
    TCS34725_PERS_60_CYCLE = 0b1111
    TCS34725_CONFIG = 0x0D
    # Choose between short and long (12x) wait times via TCS34725_WTIME
    TCS34725_CONFIG_WLONG = 0x02
    # Set the gain level for the sensor
    TCS34725_CONTROL = 0x0F
    # 0x44 = TCS34721/TCS34725, 0x4D = TCS34723/TCS34727
    TCS34725_ID = 0x12
    TCS34725_STATUS = 0x13
    # RGBC Clean channel interrupt
    TCS34725_STATUS_AINT = 0x10
    # Indicates that the RGBC channels have completed an integration cycle
    TCS34725_STATUS_AVALID = 0x01

    TCS34725_INTEGRATIONTIME_2_4MS = 0xFF  # 2.4ms - 1 cycle    - Max Count: 1024
    TCS34725_INTEGRATIONTIME_24MS = 0xF6   # 24ms  - 10 cycles  - Max Count: 10240
    TCS34725_INTEGRATIONTIME_50MS = 0xEB  # 50ms  - 20 cycles  - Max Count: 20480
    TCS34725_INTEGRATIONTIME_101MS = 0xD5  # 101ms - 42 cycles  - Max Count: 43008
    TCS34725_INTEGRATIONTIME_154MS = 0xC0  # 154ms - 64 cycles  - Max Count: 65535
    TCS34725_INTEGRATIONTIME_700MS = 0x00  # 700ms - 256 cycles - Max Count: 65535

    TCS34725_GAIN_1X = 0x00  # No gain
    TCS34725_GAIN_4X = 0x01  # 2x gain
    TCS34725_GAIN_16X = 0x02  # 16x gain
    TCS34725_GAIN_60X = 0x03  # 60x gain

    TCS34725_CDATAL = 0x14  # Clear channel data
    TCS34725_CDATAH = 0x15
    TCS34725_RDATAL = 0x16  # Red channel data
    TCS34725_RDATAH = 0x17
    TCS34725_GDATAL = 0x18  # Green channel data
    TCS34725_GDATAH = 0x19
    TCS34725_BDATAL = 0x1A  # Blue channel data
    TCS34725_BDATAH = 0x1B

    # Lookup table for integration time delays.
    INTEGRATION_TIME_DELAY = {
        0xFF: 0.0024,  # 2.4ms - 1 cycle    - Max Count: 1024
        0xF6: 0.024,   # 24ms  - 10 cycles  - Max Count: 10240
        0xEB: 0.050,   # 50ms  - 20 cycles  - Max Count: 20480
        0xD5: 0.101,   # 101ms - 42 cycles  - Max Count: 43008
        0xC0: 0.154,   # 154ms - 64 cycles  - Max Count: 65535
        0x00: 0.700    # 700ms - 256 cycles - Max Count: 65535
    }

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """

        self.slot = slot
        self.comm = I2C
        self.host = host

        # アドレス
        self.i2c_addr = 0x29

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

            # confからmodeを取得する
            if (self.host is None or self.host == ''):
                self.host = 'localhost'
            tp_config = TpConfig(self.host, self.slot, self.comm)
            setting = tp_config.get_setting()

            _integrationTime = setting['settings']['integrationTime']
            integrationTime = self.TCS34725_INTEGRATIONTIME_2_4MS
            if _integrationTime == '2.4ms':
                integrationTime = self.TCS34725_INTEGRATIONTIME_2_4MS
            elif _integrationTime == '24ms':
                integrationTime = self.TCS34725_INTEGRATIONTIME_24MS
            elif _integrationTime == '50ms':
                integrationTime = self.TCS34725_INTEGRATIONTIME_50MS
            elif _integrationTime == '101ms':
                integrationTime = self.TCS34725_INTEGRATIONTIME_101MS
            elif _integrationTime == '154ms':
                integrationTime = self.TCS34725_INTEGRATIONTIME_154MS
            elif _integrationTime == '700ms':
                integrationTime = self.TCS34725_INTEGRATIONTIME_700MS

            _gain = setting['settings']['gain']
            gain = self.TCS34725_GAIN_4X
            if _gain == '1x':
                gain = self.TCS34725_GAIN_1X
            elif _gain == '4x':
                gain = self.TCS34725_GAIN_4X
            elif _gain == '16x':
                gain = self.TCS34725_GAIN_16X
            elif _gain == '60x':
                gain = self.TCS34725_GAIN_60X

            c = self._readU8(self.TCS34725_ID)

            if c != 0x44:
                raise ValueError('TpgI2cColorSensor init failed.')

            # 設定
            self._set_integration_time(integrationTime)
            self._set_gain(gain)

            # デバイスを有効にする
            self._enable()

        finally:
            # unLock
            self.tp00.unlock(self.slot)

    def _set_integration_time(self, integration_time):
        """
        TC34725の積分時間を設定します。
         - TCS34725_INTEGRATIONTIME_2_4MS  = 2.4ms - 1 cycle    - Max Count: 1024
         - TCS34725_INTEGRATIONTIME_24MS   = 24ms  - 10 cycles  - Max Count: 10240
         - TCS34725_INTEGRATIONTIME_50MS   = 50ms  - 20 cycles  - Max Count: 20480
         - TCS34725_INTEGRATIONTIME_101MS  = 101ms - 42 cycles  - Max Count: 43008
         - TCS34725_INTEGRATIONTIME_154MS  = 154ms - 64 cycles  - Max Count: 65535
         - TCS34725_INTEGRATIONTIME_700MS  = 700ms - 256 cycles - Max Count: 65535
        """
        self._integration_time = integration_time
        self._write8(self.TCS34725_ATIME, integration_time)

    def _set_gain(self, gain):
        """
        ゲインの調整 TCS34725 (光に対する感度)
         - TCS34725_GAIN_1X   = No gain
         - TCS34725_GAIN_4X   = 2x gain
         - TCS34725_GAIN_16X  = 16x gain
         - TCS34725_GAIN_60X  = 60x gain
        """
        self._write8(self.TCS34725_CONTROL, gain)

    def _enable(self):
        """
        有効にします
        """

        self._write8(self.TCS34725_ENABLE, self.TCS34725_ENABLE_PON)
        time.sleep(0.01)
        self._write8(self.TCS34725_ENABLE,
                     (self.TCS34725_ENABLE_PON | self.TCS34725_ENABLE_AEN))

    def _write8(self, reg, value):
        """
        Write a 8-bit value to a register.
        """

        send_data = []
        send_data.append(
            {"act": "w", "add": self.i2c_addr, "cmd": self.TCS34725_COMMAND_BIT | reg, "v": [value]})
        self.tp00.send(json.dumps(send_data))

    def _readU8(self, reg):
        """
        Read an unsigned 8-bit register.
        """

        send_data = []
        send_data.append(
            {"act": "r", "add": self.i2c_addr, "cmd": self.TCS34725_COMMAND_BIT | reg, "len": 1})
        _result = self.tp00.send(json.dumps(send_data))
        result_data = json.loads(_result.decode())
        rtn = result_data[0][0]

        return rtn

    def _readU16LE(self, reg):
        """
        Read a 16-bit little endian register.
        """

        send_data = []
        send_data.append(
            {"act": "r", "add": self.i2c_addr, "cmd": self.TCS34725_COMMAND_BIT | reg, "len": 2})
        _result = self.tp00.send(json.dumps(send_data))
        result_data = json.loads(_result.decode())

        ret1 = result_data[0][0]
        ret2 = result_data[0][1] * 256
        rtn = (ret1 + ret2) & 0x0FFF

        return rtn

    def get_data(self):
        """
        値を取得します。
        """

        time.sleep(self.INTEGRATION_TIME_DELAY[self._integration_time])

        # 0 - 1の範囲で取得
        div = ((256 - self._integration_time) * 1024)
        r = self._readU16LE(self.TCS34725_RDATAL) / div
        g = self._readU16LE(self.TCS34725_GDATAL) / div
        b = self._readU16LE(self.TCS34725_BDATAL) / div
        c = self._readU16LE(self.TCS34725_CDATAL) / div

        # 小数点3桁まで
        return {"r": round(r, 3), "g": round(g, 3), "b": round(b, 3), "c": round(c, 3)}


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
        tpgI2cColorSensor = TpgI2cColorSensor(slot, host)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            recv_data = tpgI2cColorSensor.get_data()
            tpUtils.nodeOut(json.dumps(recv_data))
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
            tpUtils.nodeOut("")
