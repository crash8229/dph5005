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
        self.port = serial.Serial(port, timeout=5)

    def disconnect_port(self):
        if self.port is not None:
            self.port.close()
            self.port = None

    def __get_crc(self, message):
        checksum = libscrc.modbus(message)
        # print(hex(checksum))
        # print(self.crc_packer.pack(checksum))
        # print(self.crc_packer.unpack(self.crc_packer.pack(checksum)))
        return self.crc_packer.pack(checksum)

    def send(self, command, byte_length):
        if self.port is not None:
            self.port.write(command)
            return self.port.read(byte_length)
        return b'\x00'

    def send_command(self, address=0, mode='', registers=('', 0), data=(0, 0)):
        # Assemble the command and its expected response
        command = self.byte_packer.pack(address)
        command += self.mode[mode]
        expected_response = command
        command += self.register[registers[0]]
        if mode == 'read':
            command += self.data_packer.pack(registers[1])
            expected_response += self.byte_packer.pack(registers[1] * 2)
            for i in range(0, registers[1]):
                expected_response += b'\x00\x00'
        elif mode == 'single_write':
            command += self.data_packer.pack(data[0])
            expected_response += self.register[registers[0]]
            expected_response += self.data_packer.pack(data[0])
        elif mode == 'multi_write':
            command += self.data_packer.pack(registers[1])
            command += self.byte_packer.pack(2 * registers[1])
            for i in range(0, registers[1]):
                command += self.data_packer.pack(data[i])
            expected_response += self.register[registers[0]]
            expected_response += self.data_packer.pack(registers[1])
        command += self.__get_crc(command)
        expected_response += self.__get_crc(expected_response)

        response = self.send(command, len(expected_response))
        print(binascii.hexlify(response))
        print(binascii.hexlify(command))
        print(len(command))
        print(binascii.hexlify(expected_response))
        print(expected_response == response)
        print(len(expected_response))
        print(expected_response[:2])
        print(expected_response[2:4])
        if mode == 'read':
            if len(response) == len(expected_response):
                print('Good Read')
            else:
                print('Error in read length')
        if response[-2:] == self.__get_crc(response[:-2]):
            print('Good Write')
        else:
            print('Error in crc')

if __name__ == "__main__":
    pass
    dph = DPH5005('COM2')
    dph.send_command(1, 'multi_write', ['LOCK', 2], [0, 2, 3, 4])
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
