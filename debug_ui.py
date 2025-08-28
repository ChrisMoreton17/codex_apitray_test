import sys
import time
import threading
import logging
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from core import load_config, check_api_details, CONFIG_PATH


LOG_PATH = (Path.home() / 'Library' / 'Logs' / 'api_test_tray.log') if sys.platform == 'darwin' else (Path.home() / 'api_test_tray.log')


class LogTailer(QtCore.QObject):
    line_received = QtCore.pyqtSignal(str)

    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        self._stop = threading.Event()

    def start(self):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        pos = 0
        while not self._stop.is_set():
            try:
                with self.path.open('r', encoding='utf-8', errors='ignore') as f:
                    f.seek(pos)
                    for line in f:
                        self.line_received.emit(line.rstrip('\n'))
                    pos = f.tell()
            except FileNotFoundError:
                pass
            time.sleep(0.5)


class DebugWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('API Test Tray — Debug')
        self.resize(900, 600)

        # Top: Controls + Config
        self.url_label = QtWidgets.QLabel('API URL:')
        self.url_value = QtWidgets.QLabel('')
        self.key_label = QtWidgets.QLabel('API Key:')
        self.key_value = QtWidgets.QLabel('')
        self.interval_label = QtWidgets.QLabel('Interval:')
        self.interval_value = QtWidgets.QLabel('')
        self.notif_label = QtWidgets.QLabel('Notifications:')
        self.notif_value = QtWidgets.QLabel('')

        grid = QtWidgets.QGridLayout()
        grid.addWidget(self.url_label, 0, 0)
        grid.addWidget(self.url_value, 0, 1)
        grid.addWidget(self.key_label, 1, 0)
        grid.addWidget(self.key_value, 1, 1)
        grid.addWidget(self.interval_label, 2, 0)
        grid.addWidget(self.interval_value, 2, 1)
        grid.addWidget(self.notif_label, 3, 0)
        grid.addWidget(self.notif_value, 3, 1)

        self.btn_refresh = QtWidgets.QPushButton('Refresh Config')
        self.btn_check = QtWidgets.QPushButton('Check Now')
        self.btn_open_config = QtWidgets.QPushButton('Open Config File')
        self.btn_open_logs = QtWidgets.QPushButton('Open Log File')

        btns = QtWidgets.QHBoxLayout()
        btns.addWidget(self.btn_refresh)
        btns.addWidget(self.btn_check)
        btns.addStretch(1)
        btns.addWidget(self.btn_open_config)
        btns.addWidget(self.btn_open_logs)

        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setReadOnly(True)
        mono = QtGui.QFont('Menlo' if sys.platform == 'darwin' else 'Monospace')
        mono.setStyleHint(QtGui.QFont.Monospace)
        self.log_view.setFont(mono)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(grid)
        layout.addLayout(btns)
        layout.addWidget(self.log_view, 1)

        self.btn_refresh.clicked.connect(self.refresh_config)
        self.btn_check.clicked.connect(self.check_now)
        self.btn_open_config.clicked.connect(self.open_config)
        self.btn_open_logs.clicked.connect(self.open_logs)

        self.tailer = LogTailer(LOG_PATH)
        self.tailer.line_received.connect(self._append_log)
        self.tailer.start()

        self.refresh_config()
        self._append_log(f"Debug UI started. Watching log: {LOG_PATH}")

    def closeEvent(self, event):
        self.tailer.stop()
        super().closeEvent(event)

    def _append_log(self, line: str):
        self.log_view.append(line)

    def refresh_config(self):
        cfg = load_config()
        self.url_value.setText(cfg.get('api_url', '') or '<not set>')
        masked = '*' * len(cfg.get('api_key', '') or '')
        self.key_value.setText(masked or '<none>')
        self.interval_value.setText(str(cfg.get('interval_seconds', 60)))
        self.notif_value.setText(cfg.get('notify_mode', 'all'))

    def check_now(self):
        cfg = load_config()
        ok, status, err = check_api_details(cfg.get('api_url'), cfg.get('api_key'))
        ts = time.strftime('%H:%M:%S')
        if ok:
            self._append_log(f"[{ts}] DEBUGUI Check OK (status={status})")
        else:
            self._append_log(f"[{ts}] DEBUGUI Check DOWN (status={status}, err={err})")

    def open_config(self):
        if sys.platform == 'darwin':
            QtCore.QProcess.startDetached('open', [str(CONFIG_PATH)])
        else:
            QtCore.QProcess.startDetached(str(CONFIG_PATH))

    def open_logs(self):
        if sys.platform == 'darwin':
            QtCore.QProcess.startDetached('open', [str(LOG_PATH)])
        else:
            QtCore.QProcess.startDetached(str(LOG_PATH))


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = DebugWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

