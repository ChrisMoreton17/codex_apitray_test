import json
import os
import sys
from pathlib import Path

import requests
from PyQt5 import QtCore, QtGui, QtWidgets

CONFIG_PATH = Path.home() / '.api_tray_config.json'


def load_config():
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open('r', encoding='utf-8') as f:
            return json.load(f)
    return {'api_url': '', 'api_key': ''}


def save_config(config):
    with CONFIG_PATH.open('w', encoding='utf-8') as f:
        json.dump(config, f)


def check_api(api_url: str, api_key: str) -> bool:
    if not api_url:
        return False
    try:
        headers = {'Authorization': f'Bearer {api_key}'} if api_key else {}
        response = requests.get(api_url, headers=headers, timeout=5)
        return response.ok
    except requests.RequestException:
        return False


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.setWindowTitle('API Settings')
        self.api_url_edit = QtWidgets.QLineEdit(config.get('api_url', ''))
        self.api_key_edit = QtWidgets.QLineEdit(config.get('api_key', ''))
        self.api_key_edit.setEchoMode(QtWidgets.QLineEdit.Password)

        form = QtWidgets.QFormLayout()
        form.addRow('API URL:', self.api_url_edit)
        form.addRow('API Key:', self.api_key_edit)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_values(self):
        return {'api_url': self.api_url_edit.text(), 'api_key': self.api_key_edit.text()}


class TrayApp(QtWidgets.QSystemTrayIcon):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.config = load_config()
        self.setIcon(self._create_icon('gray'))
        self.setToolTip('API Status Checker')

        menu = QtWidgets.QMenu()
        check_action = menu.addAction('Check Now')
        check_action.triggered.connect(self.update_status)
        settings_action = menu.addAction('Settings')
        settings_action.triggered.connect(self.show_settings)
        menu.addSeparator()
        quit_action = menu.addAction('Quit')
        quit_action.triggered.connect(QtWidgets.qApp.quit)
        self.setContextMenu(menu)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(60000)  # check every minute

        if not self.config.get('api_url'):
            self.show_settings()
        else:
            self.update_status()

        self.show()

    def _create_icon(self, color: str) -> QtGui.QIcon:
        pixmap = QtGui.QPixmap(16, 16)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        brush = QtGui.QBrush(QtGui.QColor(color))
        painter.setBrush(brush)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(0, 0, 15, 15)
        painter.end()
        return QtGui.QIcon(pixmap)

    def show_settings(self):
        dialog = SettingsDialog(config=self.config)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.config = dialog.get_values()
            save_config(self.config)
            self.update_status()

    def update_status(self):
        ok = check_api(self.config.get('api_url'), self.config.get('api_key'))
        color = 'green' if ok else 'red'
        self.setIcon(self._create_icon(color))
        self.setToolTip(f'API status: {"OK" if ok else "DOWN"}')


if __name__ == '__main__':
    os.environ['QT_QPA_PLATFORM'] = os.environ.get('QT_QPA_PLATFORM', 'offscreen')
    app = QtWidgets.QApplication(sys.argv)
    tray = TrayApp(app)
    sys.exit(app.exec_())
