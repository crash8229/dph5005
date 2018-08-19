import libscrc
import binascii
import struct
import serial

port = serial.Serial('COM1', timeout=1)
# port = serial.Serial('/dev/ttyUSB0', timeout=5)
# print(port.name)

# Model # of DPH5005 is b'\x14\x55' in hex

address = b'\x01'

mode = {'read': b'\x03',
        'single_write': b'\x06',
        'multi_write': b'\x10'}

register = {'V-SET': b'\x00\x00',
            'I-SET': b'\x00\x01',
            'V-OUT': b'\x00\x02',
            'I-OUT': b'\x00\x03',
            'POWER': b'\x00\x04',
            'V-IN': b'\x00\x05',
            'LOCK': b'\x00\x06',
            'PROTECT': b'\x00\x07',
            'CV/CC': b'\x00\x08',
            'ON/OFF': b'\x00\x09',
            'B-LED': b'\x00\x0A',
            'MODEL': b'\x00\x0B',
            'VERSION': b'\x00\x0C'}

limits = {'V-SET': (0, 50),
          'I-SET': (0, 5.1),
          'LOCK': (0, 1),
          'ON/OFF': (0, 1),
          'B-LED': (0, 5)}


def calc_crc(message):
    checksum = libscrc.modbus(message)
    return struct.Struct('< H').pack(checksum)


data = b'\x00\x01'
# data = b'\x00\x01'
# command = binascii.unhexlify('010600060000')
# command = binascii.unhexlify(address + mode + register + data)
# command = address + function['single_write'] + b'\x00\x23' + data
command = address + mode['read'] + register['MODEL'] + data
# command = data
# print(command)

crc = calc_crc(command)

# print(binascii.hexlify(crc))
command += crc
print(binascii.hexlify(command))
port.write(command)
response = port.read(100)
print(binascii.hexlify(response))
print(command == response)
