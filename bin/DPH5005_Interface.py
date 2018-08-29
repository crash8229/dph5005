import libscrc
import struct
import serial


class DPH5005:
    def __init__(self):
        self.port = None
        # self.connect_port(port)
        self.byte_packer = struct.Struct('>B')
        self.data_packer = struct.Struct('>H')
        self.crc_packer = struct.Struct('<H')

        # Model # of DPH5005 is b'\x14\x55' in hex or 5205 in decimal

        self.mode = {'read': b'\x03',
                     'single_write': b'\x06',
                     'multiple_write': b'\x10'}

        self.registers = {'V-SET': b'\x00\x00',
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
        self.register_order = ['V-SET',
                               'I-SET',
                               'V-OUT',
                               'I-OUT',
                               'POWER',
                               'V-IN',
                               'LOCK',
                               'PROTECT',
                               'CV/CC',
                               'ON/OFF',
                               'B-LED',
                               'MODEL',
                               'VERSION']

        self.limits = {'ADDRESS': (1, 255),
                       'V-SET': (0, 50),
                       'I-SET': (0, 5),
                       'LOCK': (0, 1),
                       'ON/OFF': (0, 1),
                       'B-LED': (0, 5)}

        self.precision = {'ADDRESS': 0,
                          'V-SET': 2,
                          'I-SET': 3,
                          'V-OUT': 2,
                          'I-OUT': 3,
                          'POWER': (2, 1),
                          'V-IN': 2,
                          'LOCK': 0,
                          'PROTECT': 0,
                          'CV/CC': 0,
                          'ON/OFF': 0,
                          'B-LED': 0,
                          'MODEL': 0,
                          'VERSION': 0}

    # Handles connecting to a serial port. If it was connected to a previous port. it will disconnect from it first.
    def connect_port(self, port):
        self.disconnect_port()
        try:
            self.port = serial.Serial(port, timeout=1)
        except serial.SerialException:
            return False
        return True

    def is_port_alive(self):
        if self.port is None:
            # print(False)
            return False
        try:
            self.port.in_waiting
        except (OSError, serial.SerialException):
            self.disconnect_port()
            # print(False)
            return False
        # print(True)
        return True

    # Handles closing the serial port if one was opened.
    def disconnect_port(self):
        if self.port is not None:
            self.port.close()
            self.port = None

    def __get_crc(self, message):
        checksum = libscrc.modbus(message)
        return self.crc_packer.pack(checksum)

    def __send(self, command, byte_length):
        if self.is_port_alive():
            self.port.write(command)
            return self.port.read(byte_length)
        return b'\x00'

    def send_command(self, address=0, mode='', registers=('', 0), data=(0, 0)):
        # Assemble the command and its expected response
        command = self.byte_packer.pack(address)
        command += self.mode[mode]
        expected_response = command
        command += self.registers[registers[0]]
        if mode == 'read':
            command += self.data_packer.pack(registers[1])
            expected_response += self.byte_packer.pack(registers[1] * 2)
            for i in range(0, registers[1]):
                expected_response += b'\x00\x00'
        elif mode == 'single_write':
            command += self.data_packer.pack(data[0])
            expected_response += self.registers[registers[0]]
            expected_response += self.data_packer.pack(data[0])
        elif mode == 'multiple_write':
            command += self.data_packer.pack(registers[1])
            command += self.byte_packer.pack(2 * registers[1])
            for i in range(0, registers[1]):
                command += self.data_packer.pack(data[i])
            expected_response += self.registers[registers[0]]
            expected_response += self.data_packer.pack(registers[1])
        print(command)
        command += self.__get_crc(command)
        expected_response += self.__get_crc(expected_response)

        # Send command and save any response
        response = self.__send(command, len(expected_response))

        # Checks to see if the response is valid and parses it if it is.
        if mode == 'read' and len(response) == len(expected_response):
            return True, self.__parse_response(command, response)
        elif response[-2:] == self.__get_crc(response[:-2]):
            return True, self.__parse_response(command, response)
        else:
            return False, dict()

    def __parse_response(self, command, response):
        parsed_data = dict()

        # Gets the address
        address = response[:1]
        address = self.byte_packer.unpack(address)[0]
        parsed_data['address'] = address

        # Gets the mode
        mode = response[1:2]
        for m in self.mode.items():
            if mode == m[1]:
                mode = m[0]
                break
        parsed_data['mode'] = mode

        # crc = response[-2:]
        response = response[:-2]
        response = response[2:]

        # Gets the extra data in the response. The data present depends on the mode.
        if mode == 'read':
            starting_register = command[2:4]
            for item in self.registers.items():
                if starting_register == item[1]:
                    starting_register = item[0]
                    break
            number_of_registers = self.byte_packer.unpack(response[:1])[0] // 2
            response = response[1:]
            starting_index = self.register_order.index(starting_register)
            parsed_data['registers'] = self.register_order[starting_index: starting_index + number_of_registers]
            parsed_data['data'] = list()
            for i in range(0, number_of_registers):
                parsed_data['data'].append(self.data_packer.unpack(response[:2])[0])
                response = response[2:]
        elif mode == 'single_write':
            register = response[:2]
            parsed_data['data'] = self.data_packer.unpack(response[2:])[0]
            for item in self.registers.items():
                if register == item[1]:
                    register = item[0]
                    break
            parsed_data['registers'] = register
        elif mode == 'multiple_write':
            starting_register = response[:2]
            number_of_registers = self.data_packer.unpack(response[2:])[0]
            for item in self.registers.items():
                if starting_register == item[1]:
                    starting_register = item[0]
                    break
            starting_index = self.register_order.index(starting_register)
            parsed_data['registers'] = self.register_order[starting_index: starting_index + number_of_registers]
            command = command[:-2]
            command = command[7:]
            parsed_data['data'] = list()
            for i in range(0, number_of_registers):
                parsed_data['data'].append(self.data_packer.unpack(command[:2])[0])
                command = command[2:]
        else:
            # It should never reach this point as it check for a valid packet, but it does hurt to have it.
            return dict()
        return parsed_data


if __name__ == "__main__":
    dph = DPH5005()
    dph.connect_port('COM2')
    print(dph.send_command(1, 'read', ['PROTECT', 2], [0, 4, 3, 4]))
