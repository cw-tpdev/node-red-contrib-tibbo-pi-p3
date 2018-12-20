#!/usr/bin/python3
from tpP3Interface import TpP3Interface

inter = TpP3Interface()
inter.read_pic_fw_ver()
print('Board FW ver =', inter.get_pic_fw_ver())
