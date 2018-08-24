import libscrc
import binascii
import struct
import serial


class DPH5005:
    def __init__(self, port):
        self.port = None
        self.connect_port(port)
        # port = serial.Serial('/dev/ttyUSB0', timeout=5)
        # print(port.name)
        self.byte_packer = struct.Struct('>B')
        self.data_packer = struct.Struct('>H')
        self.crc_packer = struct.Struct('<H')

        # Model # of DPH5005 is b'\x14\x55' in hex

        # self.address = b'\x01'

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

        self.limits = {'ADDRESS': (1, 255),
                       'V-SET': (0, 50),
                       'I-SET': (0, 5.1),
                       'LOCK': (0, 1),
                       'ON/OFF': (0, 1),
                       'B-LED': (0, 5)}

    def connect_port(self, port):
        self.disconnect_port()
        self.port = serial.Serial(port, timeout=1)

    def disconnect_port(self):
        if self.port is not None:
            self.port.close()
            self.port = None

    def __get_crc(self, message):
        checksum = libscrc.modbus(message)
        return self.crc_packer.pack(checksum)

    def send(self, command, byte_length):
        if self.port is not None:
            self.port.write(command)
            return self.port.read(byte_length)
        return b'\x00'

    def send_command(self, address=int(), mode=str(), registers=('', ''), data=(0, 0)):
        message = self.byte_packer.pack(address)
        message += self.mode[mode]
        expected_response = message
        message += self.register[registers[0]]
        if mode == 'read':
            message += self.data_packer.pack(len(registers))
        elif mode == 'single_write':
            message += self.data_packer.pack(data[0])
        elif mode == 'multi_write':
            message += self.data_packer.pack(len(registers))
            message += self.byte_packer.pack(2 * len(data))
            for datum in data:
                message += self.data_packer.pack(datum)
        crc = self.__get_crc(message)
        command = message + crc


if __name__ == "__main__":
    pass
    dph = DPH5005('COM2')
    dph.send_command(1, 'single_write', ['LOCK'], [1])
    # data = b'\x00\x00'
    # data = 0
    # command = b'\x01' + dph.mode['single_write'] + dph.register['LOCK'] + dph.data_packer.pack(data)

    # crc = dph.__get_crc(command)

    # command += crc
    # print(binascii.hexlify(command))
    # dph.port.write(command)
    # response = dph.port.read(100)
    # print(binascii.hexlify(response))
    # print(command == response)
