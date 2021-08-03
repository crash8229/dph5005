#!/usr/bin/env python3
import argparse
import struct
import threading
from typing import Optional, Dict, Tuple, Union, Sequence

import serial

FUNCTION: Dict[str, bytes] = {
    "read": b"\x03",
    "single_write": b"\x06",
    "multiple_write": b"\x10",
}

BYTE_PACKER: struct.Struct = struct.Struct(">B")
DATA_PACKER: struct.Struct = struct.Struct(">H")
CRC_PACKER: struct.Struct = struct.Struct("<H")


class DPH5005:
    # Model # of DPH5005 is b'\x14\x55' in hex or 5205 in decimal
    MODEL: int = 5205

    __REGISTER_MAP: Dict[str, bytes] = {
        "V-SET": b"\x00\x00",
        "I-SET": b"\x00\x01",
        "V-OUT": b"\x00\x02",
        "I-OUT": b"\x00\x03",
        "POWER": b"\x00\x04",
        "V-IN": b"\x00\x05",
        "LOCK": b"\x00\x06",
        "PROTECT": b"\x00\x07",
        "CV/CC": b"\x00\x08",
        "ON/OFF": b"\x00\x09",
        "B-LED": b"\x00\x0A",
        "MODEL": b"\x00\x0B",
        "VERSION": b"\x00\x0C",
    }

    REGISTERS: Tuple[str] = tuple(__REGISTER_MAP.keys())

    LIMITS: Dict[str, Tuple[int, int]] = {
        "ADDRESS": (1, 255),
        "V-SET": (0, 50),
        "I-SET": (0, 5),
        "LOCK": (0, 1),
        "ON/OFF": (0, 1),
        "B-LED": (0, 5),
    }

    DECIMAL_PLACES: Dict[str, int] = {
        "ADDRESS": 0,
        "V-SET": 2,
        "I-SET": 3,
        "V-OUT": 2,
        "I-OUT": 3,
        "POWER": 2,
        "V-IN": 2,
        "LOCK": 0,
        "PROTECT": 0,
        "CV/CC": 0,
        "ON/OFF": 0,
        "B-LED": 0,
        "MODEL": 0,
        "VERSION": 0,
    }

    def __init__(self) -> None:
        self.port: Optional[serial.Serial] = None
        self.cmd_lock: threading.Lock = threading.Lock()

    # Generates the CRC for the modbus packet
    @staticmethod
    def get_crc(message: bytes) -> bytes:
        msg = bytearray(message)
        crc = 0xFFFF
        for b in msg:
            crc ^= b
            for i in range(8):
                if crc & 0x0001 == 0x0001:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return CRC_PACKER.pack(crc)

    # Handles connecting to a serial port. If it was connected to a previous port. it will disconnect from it first.
    def connect_port(self, port: str) -> bool:
        self.disconnect_port()
        try:
            self.port = serial.Serial(port, timeout=1)
        except serial.SerialException:
            return False
        return True

    def is_port_alive(self) -> bool:
        if self.port is None:
            return False
        try:
            self.port.inWaiting()
        except (OSError, serial.SerialException):
            self.disconnect_port()
            return False
        return True

    # Handles closing the serial port if one was opened.
    def disconnect_port(self) -> None:
        if self.port is not None:
            self.port.close()
            self.port = None

    def __send(self, command: bytes, byte_length: int) -> bytes:
        with self.cmd_lock:
            if self.is_port_alive():
                self.port.write(command)
                return self.port.read(byte_length)
            return b"\x00"

    # This sends a message to the device.
    # Arguments:
    # address = device address number set on the device
    # mode = the function to be performed, look at self.mode for accepted functions
    # registers = a tuple of the starting register and how many registers to interact with for read and multiple write
    #             for single write, it is just the register to write to.
    # data = read does not have any extra data needed
    #        single write just needs the value to write in the register
    #        multiple write needs a tuple of the data to be written to each register
    def send_command(
        self,
        address: int,
        mode: str,
        register: str,
        *,
        num_reg: Optional[int] = None,
        data: Union[int, Sequence[int], None] = None
    ) -> Tuple[bool, Dict[str, Union[int, str, tuple]]]:
        # Assemble the command and its expected response
        command = BYTE_PACKER.pack(address)
        command += FUNCTION[mode]
        expected_response = command
        command += self.__REGISTER_MAP[register]
        if mode == "read":
            command += DATA_PACKER.pack(num_reg)
            expected_response += BYTE_PACKER.pack(num_reg * 2)
            for i in range(0, num_reg):
                expected_response += b"\x00\x00"
        elif mode == "single_write":
            command += DATA_PACKER.pack(data)
            expected_response += self.__REGISTER_MAP[register]
            expected_response += DATA_PACKER.pack(data)
        elif mode == "multiple_write":
            command += DATA_PACKER.pack(num_reg)
            command += BYTE_PACKER.pack(2 * num_reg)
            for i in range(0, num_reg):
                command += DATA_PACKER.pack(data[i])
            expected_response += self.__REGISTER_MAP[register]
            expected_response += DATA_PACKER.pack(num_reg)
        command += self.get_crc(command)
        expected_response += self.get_crc(expected_response)

        # Send command and save any response
        response = self.__send(command, len(expected_response))

        # Checks to see if the response is valid and parses it if it is.
        if response[-2:] == self.get_crc(response[:-2]):
            return True, self.__parse_response(command, response)
        else:
            idx = self.REGISTERS.index(register)
            registers_affected = (
                (register,) if num_reg is None else self.REGISTERS[idx : idx + num_reg]
            )
            return False, {
                "address": address,
                "mode": mode,
                "registers": tuple(registers_affected),
            }

    def __parse_response(
        self, command: bytes, response: bytes
    ) -> Dict[str, Union[int, str, tuple]]:
        parsed_data = dict()

        # Gets the address
        address = response[:1]
        address = BYTE_PACKER.unpack(address)[0]
        parsed_data["address"] = address

        # Gets the mode
        mode = response[1:2]
        for m in FUNCTION.items():
            if mode == m[1]:
                mode = m[0]
                break
        parsed_data["mode"] = mode

        # crc = response[-2:]
        response = response[:-2]
        response = response[2:]

        # Gets the extra data in the response. The data present depends on the mode.
        if mode == "read":
            starting_register = command[2:4]
            for item in self.__REGISTER_MAP.items():
                if starting_register == item[1]:
                    starting_register = item[0]
                    break
            number_of_registers = BYTE_PACKER.unpack(response[:1])[0] // 2
            response = response[1:]
            starting_index = self.REGISTERS.index(starting_register)
            parsed_data["registers"] = self.REGISTERS[
                starting_index : starting_index + number_of_registers
            ]
            parsed_data["data"] = list()
            for i in range(0, number_of_registers):
                parsed_data["data"].append(DATA_PACKER.unpack(response[:2])[0])
                response = response[2:]
        elif mode == "single_write":
            register = response[:2]
            parsed_data["data"] = (DATA_PACKER.unpack(response[2:])[0],)
            for item in self.__REGISTER_MAP.items():
                if register == item[1]:
                    register = item[0]
                    break
            parsed_data["registers"] = (register,)
        elif mode == "multiple_write":
            starting_register = response[:2]
            number_of_registers = DATA_PACKER.unpack(response[2:])[0]
            for item in self.__REGISTER_MAP.items():
                if starting_register == item[1]:
                    starting_register = item[0]
                    break
            starting_index = self.REGISTERS.index(starting_register)
            parsed_data["registers"] = self.REGISTERS[
                starting_index : starting_index + number_of_registers
            ]
            command = command[:-2]
            command = command[7:]
            parsed_data["data"] = list()
            for i in range(0, number_of_registers):
                parsed_data["data"].append(DATA_PACKER.unpack(command[:2])[0])
                command = command[2:]
        else:
            # It should never reach this point as it checks for a valid packet, but it does hurt to have it.
            return dict()
        parsed_data["registers"] = tuple(parsed_data["registers"])
        parsed_data["data"] = tuple(parsed_data["data"])
        return parsed_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="DPH5005 Interface")
    parser.add_argument("port", help="Port of the DPH5005")
    args = parser.parse_args()

    dph = DPH5005()
    dph.connect_port(args.port)
    print(dph.send_command(address=1, mode="read", register="V-SET", num_reg=11))
    print(dph.send_command(1, "read", "MODEL", num_reg=1))
    print(dph.send_command(address=1, mode="single_write", register="V-SET", data=11))
    print(
        dph.send_command(
            address=1,
            mode="multiple_write",
            register="V-SET",
            num_reg=2,
            data=(5, 500),
        )
    )
