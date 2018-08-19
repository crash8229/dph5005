import libscrc
import binascii
import struct
import serial
import time

# port = serial.Serial('COM3', timeout=5)
port = serial.Serial('/dev/ttyUSB0', timeout=5)
print(port.name)
# address = '01'
# mode = '06'
# register = '0006'
# # data = b'0x0000'
# data = '0001'
address = b'\x01'
mode = b'\x06'
register = b'\x00\x06'
data = b'\x00\x00'
# data = b'\x00\x01'
# command = binascii.unhexlify('010600060000')
# command = binascii.unhexlify(address + mode + register + data)
command = address + mode + register + data
# command = data
# print(command)

crc = libscrc.modbus(command)
crc = struct.Struct('< H').pack(crc)
# print(binascii.hexlify(crc))
command += crc
print(binascii.hexlify(command))
port.write(command)
start_time = time.time()

print(binascii.hexlify(port.read(port.inWaiting())))
end_time = time.time()
print(end_time - start_time)