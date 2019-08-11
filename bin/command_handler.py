import queue


class Command_Handler:
    def __init__(self, command_queue, data_queue, device):
        self.command_queue = command_queue
        self.data_queue = data_queue
        self.device = device

        self.main_loop()

    def main_loop(self):
        while True:
            if self.device.is_port_alive():
                cmd = self.command_queue.get()
                if self.data_queue.full():
                    try:
                        self.data_queue.get_nowait()
                    except queue.Empty:
                        pass
                if cmd[0] == 0:
                    while not self.command_queue.empty():
                        try:
                            self.command_queue.get_nowait()
                        except queue.Empty:
                            pass
                data = self.device.send_command(*cmd[2])
                if data[1]['mode'] == 'read':
                    self.data_queue.put(data)
            else:
                while not self.command_queue.empty():
                    self.command_queue.get_nowait()
