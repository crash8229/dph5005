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
from interface import DPH5005
from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW
from qtpy_led import Led
from serial_port_scanner import serial_ports

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")


class LineEditWithLabel(QW.QWidget):
    def __init__(self, label: str, parent: Optional[QW.QWidget] = None):
        super().__init__(parent)
        layout = QW.QHBoxLayout(self)
        layout.setSpacing(0)
        self.label = QW.QLabel(label, self, alignment=QC.Qt.AlignRight)
        layout.addWidget(self.label)
        self.line_edit = QW.QLineEdit("", self, alignment=QC.Qt.AlignLeft)
        layout.addWidget(self.line_edit)


class IndicatorWithLabel(QW.QWidget):
    def __init__(self, label: str, parent: Optional[QW.QWidget]):
        super().__init__(parent)
        layout = QW.QHBoxLayout(self)
        layout.setSpacing(0)
        self.label = QW.QLabel(label, self, alignment=QC.Qt.AlignRight)
        layout.addWidget(self.label)
        self.indicator = QW.QLabel("", self, alignment=QC.Qt.AlignLeft)
        layout.addWidget(self.indicator)


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
        led_size = (25, 25)

        #### Control Tab ####
        control_window = QW.QWidget(main_tabs)
        control_layout = QW.QVBoxLayout(control_window)
        # control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(0)
        main_tabs.addTab(control_window, "Control")

        ## Title ##
        title = QW.QLabel(" DPH5005 Controller", control_window)
        title.setMaximumHeight(18)
        control_layout.addWidget(title, alignment=QC.Qt.AlignHCenter)

        ## Device Connection ##
        connect_row = QW.QWidget(control_window)
        control_layout.addWidget(connect_row, alignment=QC.Qt.AlignLeft)
        connect_row.setMaximumHeight(55)
        connect_layout = QW.QHBoxLayout(connect_row)

        # Device Address Field
        self.address = LineEditWithLabel("Address:", connect_row)
        connect_layout.addWidget(self.address)
        self.address = self.address.line_edit
        self.address.setValidator(QG.QIntValidator(1, 255, self.address))
        self.address.setMaximumWidth(38)
        self.address.setText("255")

        # Serial Port Menu
        serial_widget = QW.QWidget(connect_row)
        # connect_layout.addWidget(serial_widget, alignment=QC.Qt.AlignLeft)
        connect_layout.addWidget(serial_widget)
        serial_layout = QW.QHBoxLayout(serial_widget)
        serial_layout.addWidget(
            QW.QLabel("Port:", serial_widget), alignment=QC.Qt.AlignRight
        )
        self.serial_port_menu = QW.QComboBox(serial_widget)
        serial_layout.addWidget(self.serial_port_menu, alignment=QC.Qt.AlignLeft)
        self.serial_port_menu.addItems(["/dev/ttyAMA0", "1", "2", "3"])
        self.serial_port_menu.setMinimumWidth(110)

        # Connection Buttons
        self.connect_buttons = QW.QStackedWidget(connect_row)
        connect_layout.addWidget(self.connect_buttons)
        connect_button = QW.QPushButton("Connect", self.connect_buttons)
        disconnect_button = QW.QPushButton("Disconnect", self.connect_buttons)
        self.connect_buttons.addWidget(connect_button)
        self.connect_buttons.addWidget(disconnect_button)

        # Separator
        connect_layout.addWidget(QW.QLabel("|", connect_row))

        # Connection Status
        port_status = QW.QHBoxLayout()
        connect_layout.addLayout(port_status)
        port_status.addWidget(QW.QLabel("Port Connected?:"), alignment=QC.Qt.AlignRight)
        self.port_connected = Led(connect_row)
        self.port_connected.setFixedSize(*led_size)
        port_status.addWidget(self.port_connected, alignment=QC.Qt.AlignLeft)

        device_status = QW.QHBoxLayout()
        connect_layout.addLayout(device_status)
        device_status.addWidget(
            QW.QLabel("Device Connected?:"), alignment=QC.Qt.AlignRight
        )
        self.device_connected = Led(connect_row)
        self.device_connected.setFixedSize(*led_size)
        device_status.addWidget(self.device_connected, alignment=QC.Qt.AlignLeft)

        ## Readings ##
        reading_group = QW.QGroupBox("Readings", control_window)
        control_layout.addWidget(reading_group)

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
    app.setFont(QG.QFontDatabase.systemFont(QG.QFontDatabase.FixedFont))
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
