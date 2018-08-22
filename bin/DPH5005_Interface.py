import libscrc
import binascii
import struct
import serial


class DPH5005:
    def __init__(self):
        self.port = serial.Serial('COM4', timeout=1)
        # port = serial.Serial('/dev/ttyUSB0', timeout=5)
        # print(port.name)
        self.data_packer = struct.Struct('>H')
        self.crc_packer = struct.Struct('<H')

        # Model # of DPH5005 is b'\x14\x55' in hex

        self.address = b'\x01'

        self.mode = {'read': b'\x03',
                'single_write': b'\x06',
                'multi_write': b'\x10'}

        self.register = {'V-SET': b'\x00\x00',
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

        self.limits = {'V-SET': (0, 50),
                  'I-SET': (0, 5.1),
                  'LOCK': (0, 1),
                  'ON/OFF': (0, 1),
                  'B-LED': (0, 5)}

    def calc_crc(self, message):
        checksum = libscrc.modbus(message)
        return self.crc_packer.pack(checksum)


if __name__ == "__main__":
    dph = DPH5005()
    # data = b'\x00\x00'
    data = 0
    command = dph.address + dph.mode['single_write'] + dph.register['LOCK'] + dph.data_packer.pack(data)

    crc = dph.calc_crc(command)

    command += crc
    print(binascii.hexlify(command))
    dph.port.write(command)
    response = dph.port.read(100)
    print(binascii.hexlify(response))
    print(command == response)
