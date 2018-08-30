#!/usr/bin/env python

from kivy import require

require('1.10.1')
from kivy.config import Config

Config.set('graphics', 'resizable', False)
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '480')
from kivy.app import App
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang.builder import Builder
import os
from bin.serial_port_scanner import serial_ports
from bin.DPH5005_Interface import DPH5005

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin')
buildkv = Builder.load_file(os.path.join('bin', 'dph5005_gui_layout.kv'))


def on_close():
    App.get_running_app().stop()


class MainScreen(Screen):

    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        Clock.schedule_interval(self.update, 0.5)

        self.device = DPH5005()

        self.serial_port_status.source = os.path.join(root, 'blank.png')
        self.address.status.source = os.path.join(root, 'x.png')
        self.lock.status.source = os.path.join(root, 'lock-unlocked.png')
        self.v_set.status.source = os.path.join(root, 'blank.png')
        self.i_set.status.source = os.path.join(root, 'blank.png')
        self.b_led_set.status.source = os.path.join(root, 'blank.png')

        self.update_list = {'V-SET': self.v_set,
                            'I-SET': self.i_set,
                            'V-OUT': self.v_out,
                            'I-OUT': self.i_out,
                            'POWER': self.power,
                            'V-IN': self.v_in,
                            'LOCK': self.lock,
                            'PROTECT': self.protect,
                            'CV/CC': self.cvcc,
                            'ON/OFF': self.enable,
                            'B-LED': self.b_led_set}

        # self.controller_names = ['V-SET',
        #                          'I-SET',
        #                          'LOCK',
        #                          'ON/OFF',
        #                          'B-LED']

        self.ports = list()
        self.address.changed = True

        # self.v_set_value = 0.0
        # self.i_set_value = 0.0
        # self.b_led_set_value = 0

        self.serial_port_menu = DropDown()
        self.serial_port_update()
        self.serial_port_button.bind(on_release=self.serial_port_menu.open)
        self.serial_port_menu.bind(on_select=self.serial_connect)

    def serial_port_update(self):
        self.ports = self.get_ports()
        self.serial_port_menu.clear_widgets()
        for port in self.ports:
            btn = Button(text=port, size_hint=(1, None), font_size=self.serial_port_button.font_size)
            btn.bind(on_release=lambda btn: self.serial_port_menu.select(btn.text))
            self.serial_port_menu.add_widget(btn)
        if self.device.is_port_alive():
            btn = Button(text='Disconnect', size_hint=(1, None), font_size=self.serial_port_button.font_size)
            btn.bind(on_release=lambda btn: self.serial_port_menu.select(btn.text))
            self.serial_port_menu.add_widget(btn)

    def get_ports(self):
        ports = serial_ports()
        if '/dev/ttyAMA0' in ports:
            ports.remove('/dev/ttyAMA0')
        return ports

    def lock_toggle(self, state=2):
        if state == 1 or self.lock.status.status == 'unlocked':
            self.device.send_command(self.address.value, 'single_write', ('LOCK', 1), (1, 0))
            self.lock.status.source = os.path.join(root, 'lock-locked.png')
            self.lock.background_color = (0, 1, 0, 1)
            self.lock.status.status = 'locked'
        elif state == 0 or self.lock.status.status == 'locked':
            self.device.send_command(self.address.value, 'single_write', ('LOCK', 1), (0, 0))
            self.lock.status.source = os.path.join(root, 'lock-unlocked.png')
            self.lock.background_color = (1, 0, 0, 1)
            self.lock.status.status = 'unlocked'

    def enable_toggle(self, state=2):
        if state == 1 or self.enable.text == 'OFF':
            self.device.send_command(self.address.value, 'single_write', ('ON/OFF', 1), (1, 0))
            self.enable.text = 'ON'
            self.enable.background_color = (0, 1, 0, 1)
        elif state == 0 or self.enable.text == 'ON':
            self.device.send_command(self.address.value, 'single_write', ('ON/OFF', 1), (0, 0))
            self.enable.text = 'OFF'
            self.enable.background_color = (1, 0, 0, 1)

    # TODO: Maybe make it show the value again if the person is not focused and it has been a while
    def warning_address(self):
        # if address.text != str(self.address.value):
        self.address.status.source = os.path.join(root, 'warning.png')

    def warning_control(self, textbox):
        textbox.status.source = os.path.join(root, 'warning.png')

    def validate_address(self):
        if self.address.text == '':
            self.address.text = str(self.address.value)
            return
        self.address.value = int(self.limit_check('ADDRESS', int(self.address.text)))
        self.address.text = str(self.address.value)
        self.address.changed = True
        self.address.status.source = os.path.join(root, 'x.png')

    def validate(self, name, mode, slider, text):
        # if slider.value != float(text.text):
        if slider.do_not_update:
            slider.do_not_update = False
        elif mode == 'text':
            if text.text == '':
                text.text = str(slider.value)
            value = self.limit_check(name, float(text.text))
            if name == 'B-LED':
                text.text = str(int(value))
            else:
                text.text = str(value)
            if slider.value != value:
                slider.do_not_update = True
                slider.value = value
            slider.changed = True
            # value = int(value * 10 ** self.device.precision[name])
            # self.device.send_command(self.address.value, 'single_write', (name, 1), (value, 0))
        elif mode == 'slider':
            value = self.limit_check(name, slider.value)
            if name == 'B-LED':
                text.text = str(int(value))
            else:
                text.text = str(value)
            slider.changed = True
        text.status.source = os.path.join(root, 'blank.png')

    # def slider_send_command(self, name, value):
    #     value = int(value * 10 ** self.device.precision[name])
    #     self.device.send_command(self.address.value, 'single_write', (name, 1), (value, 0))

    def limit_check(self, name, value):
        low, high = self.device.limits[name]
        f = '{:.' + str(self.device.precision[name]) + 'f}'
        value = float(f.format(value))
        # if int(address.text) >= min and int(address.text) <= max:
        if low <= value <= high:
            return value
        elif low > value:
            return low
        elif high < value:
            return high
        else:
            return None

    def serial_disconnect(self):
        self.device.disconnect_port()
        self.serial_port_button.text = 'Select Port'
        self.serial_port_status.source = os.path.join(root, 'blank.png')
        self.address.changed = True

    def serial_connect(self, dropdown, port):
        if port == 'Disconnect':
            self.serial_disconnect()
            return
        self.serial_port_button.text = port
        if self.device.connect_port(port):
            self.serial_port_status.source = os.path.join(root, 'check.png')
        else:
            self.serial_port_status.source = os.path.join(root, 'x.png')
        self.address.changed = True

    def is_number(self, num):
        try:
            float(num)
        except ValueError:
            return False
        return True

    def on_close(self):
        on_close()

    def update(self, dt):
        self.serial_port_check()
        self.address_check()
        self.slider_check()
        self.read_device()

    def serial_port_check(self):
        if self.serial_port_button.text != 'Select Port' and not self.device.is_port_alive():
            self.serial_port_button.text = 'Select Port'
            self.serial_port_status.source = os.path.join(root, 'blank.png')
            self.address.changed = True
            self.controllers.disabled = True
        if self.ports != self.get_ports():
            self.serial_port_update()
            if self.serial_port_button.text in self.ports:
                self.serial_port_button.text = 'Select Port'
                self.serial_port_status.source = os.path.join(root, 'blank.png')
                self.address.changed = True
                self.controllers.disabled = True

    def address_check(self):
        if self.address.changed:
            if self.device.is_port_alive() and self.address.value is not None:
                data = self.device.send_command(self.address.value, 'read', ('MODEL', 1))
                if data[0] and data[1]['data'][0] == 5205:
                    self.address.status.source = os.path.join(root, 'check.png')
                    self.address.changed = False
                    self.controllers.disabled = False
                else:
                    self.address.status.source = os.path.join(root, 'x.png')
                    self.address.changed = False
                    self.controllers.disabled = True
            else:
                if self.address.status.source == os.path.join(root, 'check.png'):
                    self.address.status.source = os.path.join(root, 'x.png')
                    self.controllers.disabled = True

    def slider_check(self):
        if not self.controllers.disabled and self.device.is_port_alive():
            if self.v_set.slider.changed or self.i_set.slider.changed:
                data = list()
                data.append(int(self.v_set.slider.value * 10 ** self.device.precision['V-SET']))
                data.append(int(self.i_set.slider.value * 10 ** self.device.precision['I-SET']))
                self.device.send_command(self.address.value, 'multiple_write', ('V-SET', 2), data)
                self.v_set.slider.changed = False
                self.i_set.slider.changed = False
            if self.b_led_set.slider.changed:
                data = (int(self.b_led_set.slider.value * 10 ** self.device.precision['B-LED']), 0)
                self.device.send_command(self.address.value, 'single_write', ('B-LED', 1), data)
                self.b_led_set.slider.changed = False

    def read_device(self):
        if not self.controllers.disabled and self.device.is_port_alive():
            # ['V-SET', 'I-SET', 'V-OUT', 'I-OUT', 'POWER', 'V-IN', 'LOCK', 'PROTECT', 'CV/CC', 'ON/OFF', 'B-LED']
            display_list = [self.v_set, self.i_set, self.v_set]
            check, data = self.device.send_command(self.address.value, 'read', ('V-SET', 11))
            if check:
                print(data)
                return
                data = dict(zip(data['registers'], data['data']))
                for item in data.items():
                    name, datum = item
                    if name == 'V-SET' or name == 'I-SET' or name == 'B-LED':
                        pass
                    elif name == 'LOCK':
                        pass
                    elif name == 'ON/OFF':
                        pass
                    elif name == 'POWER':
                        pass
                    else:
                        f = '{:.' + str(self.device.precision[name]) + 'f}'
                        self.update_list[name].text = f.format(datum * 10 ** (-1 * self.device.precision[name]))



class GraphScreen(Screen):

    def __init__(self, **kwargs):
        super(GraphScreen, self).__init__(**kwargs)
        Clock.schedule_interval(self.update, 0.5)

    def update(self, dt):
        pass

    def on_close(self):
        on_close()


class DPH5005Controller(App):
    def build(self):
        main_screen = MainScreen(name='MainScreen')
        graph_screen = GraphScreen(name='GraphScreen')
        screen_manager = ScreenManager()
        screen_manager.add_widget(main_screen)
        screen_manager.add_widget(graph_screen)
        return screen_manager


if __name__ == '__main__':
    DPH5005Controller().run()
