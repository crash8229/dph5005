import binascii
import queue
import struct
import threading
import tkinter as tk

import serial

from bin.DPH5005_Interface import DPH5005


class App:
    def __init__(self, port, update_rate):
        self.byte_packer = struct.Struct(">B")
        self.data_packer = struct.Struct(">H")
        self.port = serial.Serial(port, timeout=1)
        self.dph = DPH5005()
        self.update_rate = update_rate

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
        self.lock = False

        root = tk.Tk()
        self.root = root
        root.grid_columnconfigure(index=1, weight=1)
        root.title("DPH5005 Emulator")

        frame = tk.Frame(root)
        frame.grid(row=0, column=0, sticky="we", columnspan=2)
        tk.Label(frame, text="Ignore Function: ", justify=tk.LEFT).pack(side=tk.LEFT)
        self.read_var = tk.BooleanVar(value=False)
        tk.Checkbutton(frame, variable=self.read_var, text="Read").pack(side=tk.LEFT)
        self.single_write_var = tk.BooleanVar(value=False)
        tk.Checkbutton(frame, variable=self.single_write_var, text="Single Write").pack(
            side=tk.LEFT
        )
        self.multiple_write_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            frame, variable=self.multiple_write_var, text="Multiple Write"
        ).pack(side=tk.LEFT)

        self.address = tk.StringVar(name="address")
        self.address.set("1")
        self.address.trace("w", self.address_validate)
        tk.Label(root, text="Device Address: ").grid(row=1, column=0, sticky=tk.W)
        self.address_entry = tk.Entry(
            root, width=5, state=tk.NORMAL, justify=tk.CENTER, textvariable=self.address
        )
        self.address_entry.grid(row=1, column=1, sticky=tk.W)

        tk.Label(root, text="Command Received: ").grid(row=2, column=0, sticky=tk.W)
        self.command_entry = tk.Entry(root, state=tk.DISABLED, justify=tk.CENTER)
        self.command_entry.configure(
            disabledbackground=self.command_entry["background"],
            disabledforeground=self.command_entry["foreground"],
        )
        self.command_entry.grid(row=2, column=1, sticky="we")

        tk.Label(root, text="Function: ").grid(row=3, column=0, sticky=tk.W)
        self.function_entry = tk.Entry(root, state=tk.DISABLED, justify=tk.CENTER)
        self.function_entry.configure(
            disabledbackground=self.function_entry["background"],
            disabledforeground=self.function_entry["foreground"],
        )
        self.function_entry.grid(row=3, column=1, sticky=tk.W)

        tk.Label(root, text="Response: ").grid(row=4, column=0, sticky=tk.W)
        self.response_entry = tk.Entry(
            root, width=60, state=tk.DISABLED, justify=tk.CENTER
        )
        self.response_entry.configure(
            disabledbackground=self.response_entry["background"],
            disabledforeground=self.response_entry["foreground"],
        )
        self.response_entry.grid(row=4, column=1, sticky="we")

        r = 5
        for i in range(0, len(self.dph.register_order)):
            self.register_entries.append(tk.StringVar(name=self.dph.register_order[i]))
            self.register_entries[i].set(self.registers[i])
            self.register_entries[i].trace(
                "w",
                lambda *args, var=self.register_entries[
                    i
                ], index=i: self.register_validate(var, index),
            )
            tk.Label(root, text="{0}: ".format(self.dph.register_order[i])).grid(
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
        value = self.address.get()
        if value == "":
            return
        try:
            value = int(value)
        except ValueError:
            self.address.set(1)
            return
        limit = self.dph.limits["ADDRESS"]
        if value < limit[0] or value > limit[1]:
            self.address.set(1)

    def register_validate(self, var, index):
        value = var.get()
        if value == "":
            return
        try:
            value = int(value)
        except ValueError:
            return
        if self.dph.register_order[index] in self.dph.limits:
            name = self.dph.register_order[index]
            limit = self.dph.limits[name]
            real_value = value * 10 ** (-1 * self.dph.precision[name])
            if limit[0] <= real_value <= limit[1]:
                self.registers[index] = value
        else:
            if 0 <= value <= 65535:
                self.registers[index] = value

    def emulator(self):
        while True:
            if self.port.in_waiting != 0:
                command = self.port.read(self.port.in_waiting)
                address = command[0]
                device_address = self.address.get()
                if device_address.strip() == "" or address != int(device_address):
                    continue
                mode = command[1:2]
                response = None
                starting_register = self.data_packer.unpack(command[2:4])[0]
                print("Device Address: {0}".format(address))
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
                while self.lock:
                    pass
                if (
                    not (self.read_var.get() and mode == "Read")
                    and not (self.single_write_var.get() and mode == "Single Write")
                    and not (self.multiple_write_var.get() and mode == "Multiple Write")
                ):
                    self.lock = True
                    if self.data_queue.full():
                        self.data_queue.get()
                    self.data_queue.put(
                        [
                            address,
                            binascii.hexlify(command),
                            mode,
                            binascii.hexlify(response),
                        ]
                    )
                    self.lock = False

    def update(self):
        # print('updating ... is thread alive: {0}'.format(self.thread.is_alive()))
        # print(self.address_entry.get())
        while self.lock:
            pass
        self.lock = True
        if self.data_queue.full():
            data = self.data_queue.get()
            self.lock = False
            if (
                not (self.read_var.get() and data[2] == "Read")
                and not (self.single_write_var.get() and data[2] == "Single Write")
                and not (self.multiple_write_var.get() and data[2] == "Multiple Write")
            ):
                if self.address.get() != "":
                    self.address.set(data[0])
                self.entry_update(self.command_entry, data[1])
                self.entry_update(self.function_entry, data[2])
                self.entry_update(self.response_entry, data[3])
            # else:
            #     self.entry_update(self.address_entry, '')
            #     self.entry_update(self.command_entry, '')
            #     self.entry_update(self.function_entry, '')
            #     self.entry_update(self.response_entry, '')
        self.lock = False
        self.register_entry_update()
        self.root.after(self.update_rate, self.update)

    def register_entry_update(self):
        for i in range(0, len(self.register_entries)):
            if self.register_entries[i].get() != "" and self.registers[i] != int(
                self.register_entries[i].get()
            ):
                self.register_entries[i].set(self.registers[i])

    def entry_update(self, entry, text):
        if entry["state"] == tk.DISABLED:
            entry["state"] = tk.NORMAL
            entry.delete(0, tk.END)
            entry.insert(0, text)
            entry["state"] = tk.DISABLED
        else:
            entry.delete(0, tk.END)
            entry.insert(0, text)


App("/dev/tnt1", 250)
