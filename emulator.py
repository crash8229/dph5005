import serial
import struct
from bin.DPH5005_Interface import DPH5005
import binascii

byte_packer = struct.Struct('>B')
port = serial.Serial('COM1', timeout=1)
dph = DPH5005()

while True:
    if port.in_waiting != 0:
        command = port.read(port.in_waiting)
        mode = command[1:2]
        address = command[0]
        print("Device Address: {0}".format(address))
        if mode == b'\x03':
            num_of_reg_read = byte_packer.unpack(command[5:6])[0]
            response = command[:2] + byte_packer.pack(num_of_reg_read * 2)
            for i in range(0, num_of_reg_read):
                response += b'\x14\x55'
            response += dph.get_crc(response)
            port.write(response)
            print(binascii.hexlify(response))
        else:
            print(binascii.hexlify(command))
            port.write(command)
