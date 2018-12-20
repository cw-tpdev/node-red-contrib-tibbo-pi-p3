#!/bin/sh
node-red-stop
python3 ../board_fw_ver.py
echo ''
./picberry/picberry -f pic18f66k40 -g C:18,D:17,M:14 -w P3.2.hex
echo ''
sleep 1
python3 ../board_fw_ver.py
node-red-start
