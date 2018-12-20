
import sys
from tp00 import Tp00
import json
from constant import *
import tpUtils
import time


class TpGrvRgbLcd_out:
    """
    TP Grove - LCD RGB Backlight
    """

    # commands
    LCD_CLEARDISPLAY = 0x01
    LCD_RETURNHOME = 0x02
    LCD_ENTRYMODESET = 0x04
    LCD_DISPLAYCONTROL = 0x08
    LCD_CURSORSHIFT = 0x10
    LCD_FUNCTIONSET = 0x20
    LCD_SETCGRAMADDR = 0x40
    LCD_SETDDRAMADDR = 0x80

    # flags for display entry mode
    LCD_ENTRYRIGHT = 0x00
    LCD_ENTRYLEFT = 0x02
    LCD_ENTRYSHIFTINCREMENT = 0x01
    LCD_ENTRYSHIFTDECREMENT = 0x00

    # flags for display on/off control
    LCD_DISPLAYON = 0x04
    LCD_DISPLAYOFF = 0x00
    LCD_CURSORON = 0x02
    LCD_CURSOROFF = 0x00
    LCD_BLINKON = 0x01
    LCD_BLINKOFF = 0x00

    # flags for display/cursor shift
    LCD_DISPLAYMOVE = 0x08
    LCD_CURSORMOVE = 0x00
    LCD_MOVERIGHT = 0x04
    LCD_MOVELEFT = 0x00

    def __init__(self, slot, host=None):
        """
        コンストラクタ
        """
        self.slot = slot
        self.comm = I2C
        self.host = host

        # アドレス
        self.i2c_addr_rgb = 0x62
        self.i2c_addr_text = 0x3e

        self.tp00 = Tp00(self.slot, self.comm, self.host)
        self.tp00.start()

    def set_rgb(self, r, g, b):
        """
        set RGB
        """

        send_data = []
        send_data.append(
            {"act": "w", "add": self.i2c_addr_rgb, "cmd": 0x00, "v": [0x00]})
        send_data.append(
            {"act": "w", "add": self.i2c_addr_rgb, "cmd": 0x01, "v": [0x00]})
        send_data.append(
            {"act": "w", "add": self.i2c_addr_rgb, "cmd": 0x08, "v": [0xaa]})

        send_data.append(
            {"act": "w", "add": self.i2c_addr_rgb, "cmd": 4, "v": [r]})
        send_data.append(
            {"act": "w", "add": self.i2c_addr_rgb, "cmd": 3, "v": [g]})
        send_data.append(
            {"act": "w", "add": self.i2c_addr_rgb, "cmd": 2, "v": [b]})
        self.tp00.send(json.dumps(send_data))

    def __text_command(self, cmd):
        """
        send command to display (no need for external use)
        """
        send_data = []
        send_data.append(
            {"act": "w", "add": self.i2c_addr_text, "cmd": 0x80, "v": [cmd]})
        self.tp00.send(json.dumps(send_data))

    def __to_jp(self, val):
        try:
            return ord(val.encode('shift-jis'))
        except:
            raise ValueError("Only single-byte characters can be used.")

    def set_text(self, text):
        """
        Update the display
        """
        self.__text_command(self.LCD_RETURNHOME)  # return home
        time.sleep(.05)
        self.__text_command(self.LCD_DISPLAYCONTROL |
                            self.LCD_DISPLAYON)  # display on, no cursor
        self.__text_command(0x28)  # 2 lines
        time.sleep(.05)
        count = 0
        row = 0
        while len(text) < 32:  # clears the rest of the screen
            text += ' '
        for c in text:
            if c == '\n' or count == 16:

                # 1行目もスペースで埋める
                for _ in range(16-count):
                    send_data = []
                    send_data.append(
                        {"act": "w", "add": self.i2c_addr_text, "cmd": 0x40, "v": [ord(' ')]})
                    self.tp00.send(json.dumps(send_data))

                count = 0
                row += 1
                if row == 2:
                    break
                # 2行目
                self.__text_command(0xc0)
                if c == '\n':
                    continue
            count += 1

            send_data = []
            send_data.append(
                {"act": "w", "add": self.i2c_addr_text, "cmd": 0x40, "v": [self.__to_jp(c)]})
            self.tp00.send(json.dumps(send_data))

    def clear(self):
        """
        clear display
        """
        self.__text_command(self.LCD_CLEARDISPLAY)


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
        tpGrvRgbLcd_out = TpGrvRgbLcd_out(slot, host)
    except Exception as e:
        tpUtils.stderr(str(e.args))
        sys.exit(0)

    while True:
        try:
            data = input()
            obj = json.loads(data)

            if (obj['act'] == 'rgb'):
                tpGrvRgbLcd_out.set_rgb(obj['r'], obj['g'], obj['b'])

            elif (obj['act'] == 'text'):
                tpGrvRgbLcd_out.set_text(obj['v'])

            elif (obj['act'] == 'clear'):
                tpGrvRgbLcd_out.clear()

        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            tpUtils.stderr(str(e.args))
