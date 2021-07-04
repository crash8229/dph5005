#!/usr/bin/env python3

# OP_CODE
# 0 - read model
# 1 - ON/OFF
# 2 - V-SET
# 3 - LOCK
# 4 - B-LED
# 5 - read all

import os
import sys
from typing import Optional, List

import qdarkstyle
from PySide2 import QtCore as QC
from PySide2 import QtWidgets as QW
from PySide2.QtGui import QFontDatabase
from interface import DPH5005
from serial_port_scanner import serial_ports

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")


class IndicatorWithLabel(QW.QWidget):
    def __init__(self, parent: Optional[QW.QWidget]):
        super().__init__(parent)


class DPH5005Controller(QW.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DPH5005 Controller")
        self.setFixedSize(800, 480)

        self.device = DPH5005()

        self.__gui_setup()

    def __gui_setup(self) -> None:
        main_tabs = QW.QTabWidget(self)
        self.setCentralWidget(main_tabs)

        #### Control Tab ####
        control_window = QW.QWidget(main_tabs)
        control_layout = QW.QGridLayout(control_window)
        main_tabs.addTab(control_window, "Control")

        # Title
        title = QW.QLabel(" DPH5005 Controller", control_window)
        # title.setAlignment(QC.Qt.AlignCenter)
        control_layout.addWidget(
            title, 0, 0, columnSpan=3, alignment=QC.Qt.AlignHCenter
        )

        # Close Button
        close_button = QW.QPushButton("X", control_window)
        close_button.setFixedSize(15, 20)
        close_button.clicked.connect(self.close)
        control_layout.addWidget(close_button, 0, 2)

        # Serial Port Connection

        # Readings
        reading_group = QW.QGroupBox("Readings", control_window)
        control_layout.addWidget(reading_group, 2, 0, rowSpan=3, columnSpan=3)

    @staticmethod
    def get_ports() -> List[str]:
        ports = serial_ports()
        # Exclude Raspberry Pi serial port used for bluetooth
        if "/dev/ttyAMA0" in ports:
            ports.remove("/dev/ttyAMA0")
        return ports

    def serial_port_update(self):
        self.ports = self.get_ports()
        # self.serial_port_menu.clear_widgets()
        # for port in self.ports:
        #     btn = Button(text=port, size_hint=(1, None), font_# Tabsize=self.serial_port_button.font_size)
        #     btn.bind(on_release=lambda btn: self.serial_port_menu.select(btn.text))
        #     self.serial_port_menu.add_widget(btn)
        # if self.device.is_port_alive():
        #     btn = Button(text='Disconnect', size_hint=(1, None), font_size=self.serial_port_button.font_size)
        #     btn.bind(on_release=lambda btn: self.serial_port_menu.select(btn.text))
        #     self.serial_port_menu.add_widget(btn)

    def serial_disconnect(self):
        self.device.disconnect_port()
        self.serial_port_button.text = "Select Port"
        self.serial_port_status.source = os.path.join(root, "images/blank.png")
        self.address.changed = True

    def serial_connect(self, dropdown, port):
        if port == "Disconnect":
            self.serial_disconnect()
            return
        self.serial_port_button.text = port
        if self.device.connect_port(port):
            self.serial_port_status.source = os.path.join(root, "images/check.png")
        else:
            self.serial_port_status.source = os.path.join(root, "images/x.png")
        self.address.changed = True

    def update_loop(self, dt):
        self.serial_port_check()
        self.address_check()
        self.read_timer += dt
        self.read_device()


if __name__ == "__main__":
    app = QW.QApplication([])
    app.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
    window = DPH5005Controller()

    rpi = False
    if sys.platform.startswith("linux"):
        try:
            with open("/sys/firmware/devicetree/base/model", "r") as f:
                model = f.readline()
            if "raspberry pi" in model.lower():
                rpi = True
        except FileNotFoundError:
            pass
    window.showFullScreen() if rpi else window.show()

    app.exec_()
