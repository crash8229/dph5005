# import queue
# from bin.DPH5005_Interface import DPH5005

class Command_Handler:
    def __init__(self, command_queue, data_queue, device):
        self.command_queue = command_queue
        self.data_queue = data_queue
        self.device = device

        # self.command_queue = queue.PriorityQueue()
        # self.data_queue = queue.Queue(1)
        # self.device = DPH5005()

        self.main_loop()

    def main_loop(self):
        while True:
            if self.device.is_port_alive():
                cmd = self.command_queue.get()
                if cmd[0] == 0:
                    while not self.command_queue.empty():
                        self.command_queue.get_nowait()
                data = self.device.send_command(*cmd[2])
                if data[1]['mode'] == 'read':
                    if self.data_queue.full():
                        self.data_queue.get_nowait()
                    self.data_queue.put(data)
            else:
                while not self.command_queue.empty():
                    self.command_queue.get_nowait()
