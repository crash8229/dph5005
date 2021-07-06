#!/usr/bin/env python3

import os
import sys
from typing import Optional, List, Sequence, Union, Tuple, Dict

import qdarkstyle
from interface import DPH5005
from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW
from qtpy_led import Led
from serial.serialutil import SerialException
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

        self.serial_port_refresh()

    def closeEvent(self, event):
        self.serial_disconnect()
        event.accept()

    #### Public Functions ####
    @staticmethod
    def get_ports() -> List[str]:
        ports = serial_ports()
        # Exclude Raspberry Pi serial port used for bluetooth
        if "/dev/ttyAMA0" in ports:
            ports.remove("/dev/ttyAMA0")
        return ports

    @property
    def address(self) -> int:
        return int(self.__address.text())

    def serial_port_refresh(self) -> None:
        ports = self.get_ports()
        self.serial_port_menu.clear()
        self.serial_port_menu.addItems(ports)
        self.serial_port_menu.addItem("Refresh")
        if self.device.is_port_alive():
            port = self.device.port.port
            self.serial_port_menu.setCurrentIndex(self.serial_port_menu.findText(port))

    def serial_disconnect(self) -> None:
        self.device.disconnect_port()
        self.__device_state(False)
        self.port_connected.turn_off()
        self.connect_buttons.setCurrentIndex(0)
        self.__address.setEnabled(True)
        self.serial_port_menu.setEnabled(True)

    def serial_connect(self) -> None:
        port = self.serial_port_menu.currentText()

        if self.device.is_port_alive():
            self.serial_disconnect()

        if self.device.connect_port(port):
            # Port is open
            self.port_connected.turn_on()
            self.connect_buttons.setCurrentIndex(1)
            self.__address.setEnabled(False)
            self.serial_port_menu.setEnabled(False)

            # Can we talk to the DPH5005 device
            response = self.read("MODEL", 1)
            if response[0] and response[1]["data"][0] == self.device.model:
                self.__device_state(True)
            else:
                self.__device_state(False)
        else:
            self.serial_disconnect()

    def read(
        self, register: str, num_reg: int
    ) -> Tuple[bool, Dict[str, Union[int, str, tuple]]]:
        return self.__send_command("read", register, num_reg=num_reg)

    def single_write(
        self, register: str, data: int
    ) -> Tuple[bool, Dict[str, Union[int, str, tuple]]]:
        return self.__send_command("single_write", register, data=data)

    def multiple_write(
        self, register: str, num_reg: int, data: Sequence[int]
    ) -> Tuple[bool, Dict[str, Union[int, str, tuple]]]:
        return self.__send_command(
            "multiple_write", register, num_reg=num_reg, data=data
        )

    #### Private Functions ####
    # Creates the GUI
    def __gui_setup(self) -> None:
        # Create tabs
        main_tabs = QW.QTabWidget(self)
        self.setCentralWidget(main_tabs)

        self.__gui_setup_control_tab(main_tabs)

    def __gui_setup_control_tab(self, parent: QW.QTabWidget) -> None:
        #### Control Tab ####
        control_window = QW.QWidget(parent)
        control_layout = QW.QVBoxLayout(control_window)
        control_layout.setSpacing(0)
        parent.addTab(control_window, "Control")
        led_size = (25, 25)

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
        self.__address = LineEditWithLabel("Address:", connect_row)
        connect_layout.addWidget(self.__address)
        self.__address = self.__address.line_edit
        self.__address.setValidator(QG.QIntValidator(1, 255, self.__address))
        self.__address.setMinimumWidth(38)
        self.__address.setMaximumWidth(38)
        self.__address.setText("1")

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
        self.serial_port_menu.setMinimumWidth(120)
        self.serial_port_menu.currentIndexChanged.connect(
            self.__serial_menu_index_changed
        )

        # Connection Buttons
        self.connect_buttons = QW.QStackedWidget(connect_row)
        connect_layout.addWidget(self.connect_buttons)
        connect_button = QW.QPushButton("Connect", self.connect_buttons)
        connect_button.clicked.connect(self.serial_connect)
        disconnect_button = QW.QPushButton("Disconnect", self.connect_buttons)
        disconnect_button.clicked.connect(self.serial_disconnect)
        self.connect_buttons.addWidget(connect_button)
        self.connect_buttons.addWidget(disconnect_button)

        # Separator
        connect_layout.addWidget(QW.QLabel("|", connect_row))

        # Connection Status
        port_status = QW.QHBoxLayout()
        connect_layout.addLayout(port_status)
        port_status.addWidget(QW.QLabel("Port Status:"), alignment=QC.Qt.AlignRight)
        self.port_connected = Led(connect_row)
        self.port_connected.setFixedSize(*led_size)
        port_status.addWidget(self.port_connected, alignment=QC.Qt.AlignLeft)

        device_status = QW.QHBoxLayout()
        connect_layout.addLayout(device_status)
        device_status.addWidget(QW.QLabel("Device Status:"), alignment=QC.Qt.AlignRight)
        self.device_connected = Led(connect_row)
        self.device_connected.setFixedSize(*led_size)
        device_status.addWidget(self.device_connected, alignment=QC.Qt.AlignLeft)

        ## Device related widget ##
        device_fields = QW.QWidget(control_window)
        device_fields_layout = QW.QVBoxLayout(device_fields)
        self.device_fields = device_fields
        device_fields.setEnabled(False)
        control_layout.addWidget(device_fields)

        # Readings #
        reading_group = QW.QGroupBox("Readings", device_fields)
        device_fields_layout.addWidget(reading_group)

        # Controls #
        control_group = QW.QGroupBox("Controls", device_fields)
        device_fields_layout.addWidget(control_group)

    @QC.Slot(int)
    def __serial_menu_index_changed(self, idx: int) -> None:
        if (
            self.serial_port_menu.count() > 1
            and self.serial_port_menu.count() - 1 == idx
        ):
            self.serial_port_refresh()

    def __device_state(self, state: bool) -> None:
        self.device_connected.set_status(state)
        self.device_fields.setEnabled(state)

    def __send_command(
        self,
        mode: str,
        register: str,
        *,
        num_reg: Optional[int] = None,
        data: Union[int, Sequence[int], None] = None
    ) -> Tuple[bool, Dict[str, Union[int, str, tuple]]]:
        response = (False, {})
        if self.device.is_port_alive():
            try:
                # If it fails, it will retry until it runs out of attempts
                attempts_left = 1
                while attempts_left > 0:
                    attempts_left -= 1
                    response = self.device.send_command(
                        self.address, mode, register, num_reg=num_reg, data=data
                    )
                    if response[0]:
                        attempts_left = 0
                if not response[0]:
                    # Something happened with the device, disable controls
                    self.__device_state(False)
            except SerialException:
                # Something happened with the port
                # Turn off port status led and disable device controls
                self.port_connected.turn_off()
                self.__device_state(False)
        else:
            # Not connected to a port
            # Call disconnect method to make sure the GUI is in the right state
            self.serial_disconnect()
        return response

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
