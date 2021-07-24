#!/usr/bin/python3

import argparse
import binascii
import datetime
import queue
import struct
import threading
import time
import tkinter as tk

import serial
from interface import DPH5005


class DPH5005Emulator:
    def __init__(self, port: str, interactive: bool = False, update_rate: int = 250):
        self.byte_packer = struct.Struct(">B")
        self.data_packer = struct.Struct(">H")
        self.port = serial.Serial(port, timeout=1)
        self.dph = DPH5005()
        self.update_rate = update_rate
        self.__interactive = interactive

        self.address = 1
        self.registers = [
            0,  # V-SET
            0,  # I-SET
            0,  # V-OUT
            0,  # I-OUT
            0,  # POWER
            0,  # V-IN
            0,  # LOCK
            0,  # PROTECT
            0,  # CV/CC
            0,  # ON/OFF
            0,  # B-LED
            5205,  # MODEL
            255,
        ]  # VERSION

        self.register_entries = list()

        self.data_queue = queue.LifoQueue(1)
        self.lock: threading.Lock = threading.Lock()

        if interactive:
            self.__gui_setup()
        else:
            self.emulator()

    def __gui_setup(self):
        root = tk.Tk()
        self.root = root
        root.grid_columnconfigure(index=1, weight=1)
        root.title("DPH5005 Emulator")
        bg_color = root["background"]

        frame = tk.Frame(root)
        frame.grid(row=0, column=0, sticky="we", columnspan=2)
        tk.Label(frame, text="Ignore Function: ", justify=tk.LEFT).pack(side=tk.LEFT)
        self.read_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            frame, variable=self.read_var, text="Read", selectcolor=bg_color
        ).pack(side=tk.LEFT)
        self.single_write_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            frame,
            variable=self.single_write_var,
            text="Single Write",
            selectcolor=bg_color,
        ).pack(side=tk.LEFT)
        self.multiple_write_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            frame,
            variable=self.multiple_write_var,
            text="Multiple Write",
            selectcolor=bg_color,
        ).pack(side=tk.LEFT)

        self.address_entry_var = tk.StringVar(name="address")
        self.address_entry_var.set(f"{self.address}")
        self.address_entry_var.trace("w", self.address_validate)
        tk.Label(root, text="Device Address: ").grid(row=1, column=0, sticky=tk.W)
        address_entry = tk.Entry(
            root,
            width=5,
            state=tk.NORMAL,
            justify=tk.CENTER,
            textvariable=self.address_entry_var,
        )
        address_entry.grid(row=1, column=1, sticky=tk.W)

        tk.Label(root, text="Time Received: ").grid(row=2, column=0, sticky=tk.W)
        self.time_entry = tk.Entry(root, state=tk.DISABLED, justify=tk.CENTER)
        self.time_entry.configure(
            disabledbackground=self.time_entry["background"],
            disabledforeground=self.time_entry["foreground"],
        )
        self.time_entry.grid(row=2, column=1, sticky=tk.W)

        tk.Label(root, text="Command Received: ").grid(row=3, column=0, sticky=tk.W)
        self.command_entry = tk.Entry(root, state=tk.DISABLED, justify=tk.CENTER)
        self.command_entry.configure(
            disabledbackground=self.command_entry["background"],
            disabledforeground=self.command_entry["foreground"],
        )
        self.command_entry.grid(row=3, column=1, sticky="we")

        tk.Label(root, text="Function: ").grid(row=4, column=0, sticky=tk.W)
        self.function_entry = tk.Entry(root, state=tk.DISABLED, justify=tk.CENTER)
        self.function_entry.configure(
            disabledbackground=self.function_entry["background"],
            disabledforeground=self.function_entry["foreground"],
        )
        self.function_entry.grid(row=4, column=1, sticky=tk.W)

        tk.Label(root, text="Response: ").grid(row=5, column=0, sticky=tk.W)
        self.response_entry = tk.Entry(
            root, width=60, state=tk.DISABLED, justify=tk.CENTER
        )
        self.response_entry.configure(
            disabledbackground=self.response_entry["background"],
            disabledforeground=self.response_entry["foreground"],
        )
        self.response_entry.grid(row=5, column=1, sticky="we")

        r = 6
        for i in range(0, len(self.dph.REGISTERS)):
            self.register_entries.append(tk.StringVar(name=self.dph.REGISTERS[i]))
            self.register_entries[i].set(self.registers[i])
            self.register_entries[i].trace(
                "w",
                lambda *args, var=self.register_entries[
                    i
                ], index=i: self.register_validate(var, index),
            )
            tk.Label(root, text="{0}: ".format(self.dph.REGISTERS[i])).grid(
                row=r, column=0, sticky=tk.W
            )
            tk.Entry(
                root,
                state=tk.NORMAL,
                justify=tk.CENTER,
                textvariable=self.register_entries[i],
            ).grid(row=r, column=1, sticky=tk.W)
            r += 1

        self.thread = threading.Thread(
            target=self.emulator, name="emulator", daemon=True
        )
        self.thread.start()

        root.after(0, self.update)
        root.mainloop()

    def address_validate(self, *args):
        value = self.address_entry_var.get()
        if value == "":
            return
        try:
            value = int(value)
        except ValueError:
            self.address_entry_var.set(self.address)
            return
        limit = self.dph.LIMITS["ADDRESS"]
        if value < limit[0] or value > limit[1]:
            self.address_entry_var.set(self.address)
            return
        self.address = value

    def register_validate(self, var, index):
        value = var.get()
        if value == "":
            return
        try:
            value = int(value)
        except ValueError:
            return
        if self.dph.REGISTERS[index] in self.dph.LIMITS:
            name = self.dph.REGISTERS[index]
            limit = self.dph.LIMITS[name]
            real_value = value * 10 ** (-1 * self.dph.DECIMAL_PLACES[name])
            if limit[0] <= real_value <= limit[1]:
                self.registers[index] = value
        else:
            if 0 <= value <= 65535:
                self.registers[index] = value

    @staticmethod
    def pretty_print(data):
        label = data[0]
        len_label = len(max(data[0]))
        value = [str(v) for v in data[1]]
        len_value = len(max(value))
        for lbl, val in zip(label, value):
            print(f"{lbl:{len_label}}: {val:{len_value}}")

    def print_info(self):
        # Print out configuration
        print("DPH5005 Emulator")
        msg = (["Port", "Address", "Registers"], [self.port.port, self.address, ""])
        self.pretty_print(msg)
        msg = [[], []]
        for reg in range(len(self.dph.REGISTERS)):
            msg[0].append(f"  {self.dph.REGISTERS[reg]}")
            msg[1].append(f"{self.registers[reg]:5d}")
        self.pretty_print(msg)
        print("")

    def emulator(self):
        self.print_info()
        while True:
            if self.port.in_waiting != 0:
                command = self.port.read(self.port.in_waiting)
                address = command[0]
                time_received = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                device_address = self.address
                if address != device_address:
                    continue
                mode = command[1:2]
                response = None
                starting_register = self.data_packer.unpack(command[2:4])[0]
                print("Device Address: {0}".format(address))
                print("Time Received: {0}".format(time_received))
                print("Received Command: {0}".format(binascii.hexlify(command)))
                if mode == b"\x03":
                    mode = "Read"
                    print("Function: Read")
                    num_of_reg = self.data_packer.unpack(command[4:6])[0]
                    response = command[:2] + self.byte_packer.pack(num_of_reg * 2)
                    for i in range(0, num_of_reg):
                        response += self.data_packer.pack(
                            self.registers[starting_register + i]
                        )
                    response += self.dph.get_crc(response)
                    print("Response: {0}".format(binascii.hexlify(response)))
                    self.port.write(response)
                elif mode == b"\x06":
                    mode = "Single Write"
                    print("Function: Single Write")
                    data = self.data_packer.unpack(command[4:6])[0]
                    self.registers[starting_register] = data
                    response = command[:4] + self.data_packer.pack(
                        self.registers[starting_register]
                    )
                    response += self.dph.get_crc(response)
                    print("Response: {0}".format(binascii.hexlify(response)))
                    self.port.write(response)
                elif mode == b"\x10":
                    mode = "Multiple Write"
                    print("Function: Multiple Write")
                    # num_of_reg = data_packer.unpack(command[4:6])[0]  # Seems I don't need this info
                    bytes_written = command[6]
                    data = command[7 : 7 + bytes_written]
                    for i in range(0, bytes_written, 2):
                        self.registers[
                            starting_register + i // 2
                        ] = self.data_packer.unpack(data[i : i + 2])[0]
                    response = command[:6] + self.dph.get_crc(command[:6])
                    print("Response: {0}".format(binascii.hexlify(response)))
                    self.port.write(response)
                else:
                    print("Function: Unknown Function")
                print("")
                if (
                    self.__interactive
                    and not (self.read_var.get() and mode == "Read")
                    and not (self.single_write_var.get() and mode == "Single Write")
                    and not (self.multiple_write_var.get() and mode == "Multiple Write")
                ):
                    with self.lock:
                        if self.data_queue.full():
                            self.data_queue.get()
                        self.data_queue.put(
                            [
                                time_received,
                                binascii.hexlify(command),
                                mode,
                                binascii.hexlify(response),
                            ]
                        )
            else:
                time.sleep(0.001)  # Small sleep

    def update(self):
        start = time.perf_counter()
        with self.lock:
            if self.data_queue.full():
                data = self.data_queue.get()
                if (
                    not (self.read_var.get() and data[2] == "Read")
                    and not (self.single_write_var.get() and data[2] == "Single Write")
                    and not (
                        self.multiple_write_var.get() and data[2] == "Multiple Write"
                    )
                ):
                    self.entry_update(self.time_entry, data[0])
                    self.entry_update(self.command_entry, data[1])
                    self.entry_update(self.function_entry, data[2])
                    self.entry_update(self.response_entry, data[3])
        self.register_entry_update()
        self.root.after(
            round(self.update_rate - (time.perf_counter() - start)), self.update
        )

    def register_entry_update(self):
        for i in range(0, len(self.register_entries)):
            if self.register_entries[i].get() != "" and self.registers[i] != int(
                self.register_entries[i].get()
            ):
                self.register_entries[i].set(self.registers[i])

    @staticmethod
    def entry_update(entry, text):
        if entry["state"] == tk.DISABLED:
            entry["state"] = tk.NORMAL
            entry.delete(0, tk.END)
            entry.insert(0, text)
            entry["state"] = tk.DISABLED
        else:
            entry.delete(0, tk.END)
            entry.insert(0, text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="DPH5005 Emulator",
        description="Emulates the behavior of the DPH5005 over serial.",
    )
    parser.add_argument("-i", action="store_true", help="Interactive mode with GUI")
    parser.add_argument(
        "-u", default=250, type=int, help="Rate in milliseconds to update the widgets"
    )
    parser.add_argument("port", help="Name of the port to listen on")
    args = parser.parse_args()

    # Exit gracefully on keyboard interrupt
    try:
        DPH5005Emulator(port=args.port, interactive=args.i, update_rate=args.u)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nExiting")
