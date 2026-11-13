import hashlib
import platform
import sys
import uuid

from PySide6.QtGui import QGuiApplication, QFont
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def get_machine_id() -> str:
    raw = (
        platform.node()
        + platform.system()
        + platform.processor()
        + str(uuid.getnode())
    )
    return hashlib.sha256(raw.encode()).hexdigest()


class MachineIdWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Machine ID Retriever")
        self.setFixedSize(620, 160)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout()

        row = QHBoxLayout()
        label = QLabel("Machine ID")
        self.machine_id_edit = QLineEdit()
        self.machine_id_edit.setReadOnly(True)
        self.machine_id_edit.setFont(QFont("Consolas", 9))
        row.addWidget(label)
        row.addWidget(self.machine_id_edit)

        buttons = QHBoxLayout()
        get_btn = QPushButton("Get")
        copy_btn = QPushButton("Copy")
        get_btn.clicked.connect(self.on_get)
        copy_btn.clicked.connect(self.on_copy)
        buttons.addWidget(get_btn)
        buttons.addWidget(copy_btn)

        root.addLayout(row)
        root.addLayout(buttons)
        self.setLayout(root)

    def on_get(self) -> None:
        self.machine_id_edit.setText(get_machine_id())

    def on_copy(self) -> None:
        value = self.machine_id_edit.text().strip()
        if not value:
            QMessageBox.warning(self, "Copy", "Click Get first.")
            return
        QGuiApplication.clipboard().setText(value)
        QMessageBox.information(self, "Copy", "Machine ID copied to clipboard.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MachineIdWindow()
    win.show()
    sys.exit(app.exec())
