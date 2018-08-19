from kivy import require
require('1.10.0')
from kivy.config import Config
Config.set('graphics', 'resizable', False)
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '480')
from kivy.app import App
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.clock import Clock
from bin.serial_port_scanner import serial_ports
from kivy.uix.gridlayout import GridLayout
import os


class DPH5005Controller(App):
    def build(self):
        main = MainScreen()
        Clock.schedule_interval(main.update, 1.0 / 60.0)
        return main


class MainScreen(GridLayout):

    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)

        # self.serial_port_menu_button = ObjectProperty()
        # Builder.load_file('DPH5005Controller.kv')
        self.serial_port_menu = DropDown()
        self.ports = list()
        self.serial_port_update()
        self.serial_port_menu_button.bind(on_release=self.serial_port_menu.open)
        self.serial_port_menu.bind(on_select=lambda instance, x: setattr(self.serial_port_menu_button, 'text', x))

    def serial_port_update(self):
        self.ports = serial_ports()
        self.serial_port_menu.clear_widgets()
        for port in self.ports:
            btn = Button(text=port,
                         size_hint=(1, None),
                         font_size=self.serial_port_menu_button.font_size)
            btn.bind(on_release=lambda btn: self.serial_port_menu.select(btn.text))
            self.serial_port_menu.add_widget(btn)

    def is_number(self, num):
        try:
            float(num)
        except ValueError:
            return False
        return True

    def on_close(self):
        App.get_running_app().stop()

    def update(self, dt):
        pass


def opendrop(event, widget):
    widget.open()


if __name__ == '__main__':
    DPH5005Controller().run()
