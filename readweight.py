import sys

from PySide6.QtCore import QObject, QCoreApplication, QTimer
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo


class ScaleReader(QObject):

    def __init__(self, port_name: str, baud: int = 9600):
        super().__init__()

        self.serial = QSerialPort()
        self.serial.setPortName(port_name)
        self.serial.setBaudRate(baud)

        self.serial.readyRead.connect(self.read_data)

        self.data_count = 0
        self.max_reads = 10   # Stop after 10 reads

    def open(self):
        return self.serial.open(QSerialPort.ReadOnly)

    def read_data(self):
        data = self.serial.readAll().data()

        try:
            text = data.decode(errors="ignore")
        except:
            text = str(data)

        print("RAW BYTES :", data)
        print("RAW TEXT  :", repr(text))
        print("-" * 50)

        self.data_count += 1

        # Stop after enough data
        if self.data_count >= self.max_reads:
            print("STOPPING...")
            self.serial.close()
            QTimer.singleShot(500, QCoreApplication.quit)


app = QCoreApplication(sys.argv)

print("AVAILABLE PORTS:")
for port in QSerialPortInfo.availablePorts():
    print(port.portName(), "-", port.description())

print("-" * 50)

# CHANGE COM7 TO YOUR SCALE PORT
reader = ScaleReader("COM7", 9600)

if not reader.open():
    print("FAILED TO OPEN PORT")
    sys.exit()

print("LISTENING TO SCALE RAW DATA...")
print("=" * 50)

sys.exit(app.exec())