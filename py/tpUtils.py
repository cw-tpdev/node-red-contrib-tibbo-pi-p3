"""
tpUtils 共通処理
"""
import sys


def stdout(msg):
    """
    標準出力します。
    """

    sys.stdout.write(str(msg) + '\n')
    sys.stdout.flush()


def stderr(msg):
    """
    標準エラーを出力します。
    """

    sys.stderr.write(msg)
    sys.stderr.flush()


def nodeOut(msg):
    """
    Nodeのアウトプット用の文字列を標準出力します。
    """

    sys.stdout.write("[TP NODE OP]" + str(msg) + '\n')
    sys.stdout.flush()


def dec_to_bcd(dec):
    """
    入力された値をBCDコードに変換します。
    """

    low = (dec % 10)
    high = round(((dec - low) / 10))
    return (high << 4) + low


def bcd_to_dec(bcd):
    """
    入力されたBCDコードにintに変換します。
    """

    low = bcd & 0x0F
    high = (bcd >> 4) & 0x0F
    return high * 10 + low


def slot_int_to_str(slot_int):
    """
    slot番号をslot文字列に変更します。
    1 -> 'S01' 
    """
    return 'S' + '{0:02d}'.format(slot_int)


def slot_str_to_int(slot_str):
    """
    slog文字列をslot番号に変更します。
    'S01' -> 1 
    """
    return int(slot_str[1:3])


def line_int_to_str(line_int):
    """
    line番号をline文字に変更します。
    1 -> 'A' 
    4 -> 'D' 
    """
    return chr(ord('A') - 1 + line_int)


def line_str_to_int(line_str):
    """
    line番号をline文字に変更します。
    'A' -> 1 
    'D' -> 4 
    """
    return ord(line_str) - ord('A') + 1


def to_num(num):
    """
    引数を数値に変換します。
    """
    return int(num) if type(num) is str else num


def to_float(num):
    """
    引数をFloatに変換します。
    """
    return float(num) if type(num) is str else num
