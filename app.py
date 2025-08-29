import os
import sys
import logging
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from core import load_config, save_config, check_api


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, config=None, title='API Settings', first_run=False):
        super().__init__(parent)
        self.setWindowTitle(title)
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

        # Make sure the dialog is visible and front-most on first run in menu bar mode
        if first_run:
            self.setModal(True)
            # Keep on top so it doesn't get lost behind other apps
            self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
            # Utility/tool window style often plays nicer for LSUIElement apps
            self.setWindowFlag(QtCore.Qt.Tool, True)

    def get_values(self):
        return {'api_url': self.api_url_edit.text(), 'api_key': self.api_key_edit.text()}


def _setup_logging():
    log = logging.getLogger('apitray')
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    try:
        log_dir = Path.home() / 'Library' / 'Logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / 'api_test_tray.log'
    except Exception:
        log_path = Path.home() / 'api_test_tray.log'
    fh = logging.FileHandler(str(log_path), encoding='utf-8')
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fh.setFormatter(fmt)
    log.addHandler(fh)
    # Also echo to stderr when run from terminal
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    log.addHandler(sh)
    log.info('Logging initialized → %s', log_path)
    return log


class TrayApp(QtWidgets.QSystemTrayIcon):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.log = _setup_logging()
        self.config = load_config()
        # Backfill defaults for newly added settings
        self.config.setdefault('interval_seconds', 60)
        self.config.setdefault('notify_mode', 'all')
        # Initial neutral icon before first check
        self.setIcon(self._create_icon('gray', label='…'))
        self.setToolTip('API Status Checker')
        self.last_ok = None
        self.log.info('App started. Config loaded (url=%s, interval=%ss, notify=%s).',
                      ('set' if self.config.get('api_url') else 'missing'),
                      self.config.get('interval_seconds', 60),
                      self.config.get('notify_mode', 'all'))

        menu = QtWidgets.QMenu()
        open_window_action = menu.addAction('Open App Window…')
        open_window_action.triggered.connect(self.open_main_window)
        check_action = menu.addAction('Check Now')
        check_action.triggered.connect(self.update_status)
        menu.addSeparator()
        set_url_action = menu.addAction('Set API URL…')
        set_url_action.triggered.connect(self.set_api_url)
        set_key_action = menu.addAction('Set API Key…')
        set_key_action.triggered.connect(self.set_api_key)
        set_interval_action = menu.addAction('Set Interval…')
        set_interval_action.triggered.connect(self.set_interval)
        # Notifications submenu
        notif_menu = menu.addMenu('Notifications')
        self.notifications_group = QtWidgets.QActionGroup(self)
        self.notifications_group.setExclusive(True)
        self.notif_all_action = notif_menu.addAction('All (Down + Recovered)')
        self.notif_all_action.setCheckable(True)
        self.notif_fail_action = notif_menu.addAction('Failures Only')
        self.notif_fail_action.setCheckable(True)
        self.notif_off_action = notif_menu.addAction('Off')
        self.notif_off_action.setCheckable(True)
        self.notifications_group.addAction(self.notif_all_action)
        self.notifications_group.addAction(self.notif_fail_action)
        self.notifications_group.addAction(self.notif_off_action)
        # Reflect current mode
        mode = self.config.get('notify_mode', 'all')
        if mode == 'fail':
            self.notif_fail_action.setChecked(True)
        elif mode == 'off':
            self.notif_off_action.setChecked(True)
        else:
            self.notif_all_action.setChecked(True)
        # Connect changes
        self.notif_all_action.triggered.connect(lambda: self.set_notify_mode('all'))
        self.notif_fail_action.triggered.connect(lambda: self.set_notify_mode('fail'))
        self.notif_off_action.triggered.connect(lambda: self.set_notify_mode('off'))
        settings_action = menu.addAction('Settings')
        settings_action.triggered.connect(self.show_settings)
        menu.addSeparator()
        quit_action = menu.addAction('Quit')
        quit_action.triggered.connect(QtWidgets.qApp.quit)
        self.setContextMenu(menu)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_status)
        self.update_timer()

        if not self.config.get('api_url'):
            self.show_first_run()
            # Also open the main window for clearer onboarding
            self.open_main_window()
        else:
            self.update_status()

        self.show()
        # On launch, give a small nudge so users notice it's running
        try:
            self.showMessage('API Test Tray', 'Running in the menu bar. Click the icon to open settings.', QtWidgets.QSystemTrayIcon.Information, 4000)
        except Exception:
            pass

    def _create_icon(self, color: str, label: str = '') -> QtGui.QIcon:
        # Draw a larger pixmap for crispness on HiDPI and scale down
        size = 64
        pm = QtGui.QPixmap(size, size)
        pm.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pm)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        # Outer border for visibility in busy menu bars
        pen = QtGui.QPen(QtGui.QColor('#000000'))
        pen.setWidthF(size * 0.05)
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(color)))
        margin = size * 0.08
        painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)
        # Label (✓, !, …) for readability
        if label:
            font = QtGui.QFont()
            font.setBold(True)
            font.setPointSizeF(size * 0.45)
            painter.setFont(font)
            painter.setPen(QtGui.QPen(QtGui.QColor('#FFFFFF')))
            rect = QtCore.QRectF(0, 0, size, size)
            painter.drawText(rect, QtCore.Qt.AlignCenter, label)
        painter.end()
        icon = QtGui.QIcon()
        icon.addPixmap(pm.scaled(16, 16, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        icon.addPixmap(pm.scaled(32, 32, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        icon.addPixmap(pm.scaled(64, 64, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        return icon

    def show_settings(self):
        dialog = SettingsDialog(config=self.config, title='API Settings')
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.config = dialog.get_values()
            # keep existing interval if not managed by dialog
            self.config.setdefault('interval_seconds', load_config().get('interval_seconds', 60))
            self.config.setdefault('notify_mode', load_config().get('notify_mode', 'all'))
            save_config(self.config)
            self.update_timer()
            self.update_status()

    def show_first_run(self):
        # Try to bring our app and dialog to front on macOS LSUIElement
        if sys.platform == 'darwin':
            try:
                from AppKit import NSApplication, NSApplicationActivationPolicyRegular
                app = NSApplication.sharedApplication()
                # Show a real app UI (Dock + menu) for setup
                app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
                app.activateIgnoringOtherApps_(True)
            except Exception:
                pass
        dialog = SettingsDialog(config=self.config, title='Welcome — Set API Endpoint', first_run=True)
        dialog.activateWindow()
        dialog.raise_()
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.config = dialog.get_values()
            self.config.setdefault('interval_seconds', load_config().get('interval_seconds', 60))
            self.config.setdefault('notify_mode', load_config().get('notify_mode', 'all'))
            save_config(self.config)
            self.update_timer()
            self.update_status()

    # --- App window (Dock-visible) ---
    def open_main_window(self):
        if not hasattr(self, '_main_window') or self._main_window is None:
            self._main_window = MainWindow(self)
        # Ensure Dock presence and focus on macOS
        if sys.platform == 'darwin':
            try:
                from AppKit import NSApplication, NSApplicationActivationPolicyRegular
                app = NSApplication.sharedApplication()
                app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
                app.activateIgnoringOtherApps_(True)
            except Exception:
                pass
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()

    def update_status(self):
        ok = False
        status_code = None
        err = None
        try:
            from core import check_api_details
            ok, status_code, err = check_api_details(self.config.get('api_url'), self.config.get('api_key'))
        except Exception as e:
            err = str(e)
        color = 'green' if ok else 'red'
        label = '✓' if ok else '!'
        self.setIcon(self._create_icon(color, label=label))
        interval = int(self.config.get('interval_seconds', 60))
        self.setToolTip(f'API status: {"OK" if ok else "DOWN"} • every {interval}s')
        # Log result
        url_state = 'set' if self.config.get('api_url') else 'missing'
        if ok:
            self.log.info('Check OK (url=%s, status=%s)', url_state, status_code)
        else:
            if err:
                self.log.warning('Check DOWN (url=%s, error=%s)', url_state, err)
            else:
                self.log.warning('Check DOWN (url=%s, status=%s)', url_state, status_code)
        # Notifications according to mode
        mode = self.config.get('notify_mode', 'all')
        # Notify on transition to DOWN
        if self.last_ok is True and not ok and mode in ('all', 'fail'):
            self.showMessage('API Down', 'The API did not respond successfully.', QtWidgets.QSystemTrayIcon.Critical, 5000)
        # Notify on recovery
        if self.last_ok is False and ok and mode == 'all':
            self.showMessage('API Recovered', 'The API is responding again.', QtWidgets.QSystemTrayIcon.Information, 4000)
        self.last_ok = ok

    def update_timer(self):
        interval_ms = max(5, int(self.config.get('interval_seconds', 60))) * 1000
        self.timer.start(interval_ms)

    def set_api_url(self):
        current = self.config.get('api_url', '')
        text, ok = QtWidgets.QInputDialog.getText(None, 'Set API URL', 'Enter API URL:', QtWidgets.QLineEdit.Normal, current)
        if ok and text:
            self.config['api_url'] = text.strip()
            save_config(self.config)
            self.update_status()

    def set_api_key(self):
        current = self.config.get('api_key', '')
        text, ok = QtWidgets.QInputDialog.getText(None, 'Set API Key', 'Enter API Key:', QtWidgets.QLineEdit.Password, current)
        if ok:
            self.config['api_key'] = text
            save_config(self.config)
            self.update_status()

    def set_interval(self):
        current = int(self.config.get('interval_seconds', 60))
        value, ok = QtWidgets.QInputDialog.getInt(None, 'Set Interval', 'Seconds between checks:', current, 5, 86400, 1)
        if ok:
            self.config['interval_seconds'] = int(value)
            save_config(self.config)
            self.update_timer()

    def set_notify_mode(self, mode: str):
        self.config['notify_mode'] = mode
        save_config(self.config)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, tray: TrayApp):
        super().__init__()
        self.tray = tray
        self.setWindowTitle('API Test Tray')
        self.resize(800, 500)

        # Top section: status
        self.status_label = QtWidgets.QLabel('Status: Unknown')
        self.detail_label = QtWidgets.QLabel('')
        status_layout = QtWidgets.QVBoxLayout()
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.detail_label)
        status_box = QtWidgets.QGroupBox('Current Status')
        status_box.setLayout(status_layout)

        # Controls
        self.btn_check = QtWidgets.QPushButton('Check Now')
        self.btn_settings = QtWidgets.QPushButton('Open Settings…')
        self.btn_open_config = QtWidgets.QPushButton('Reveal Config File')
        self.btn_open_logs = QtWidgets.QPushButton('Reveal Log File')
        ctrl_layout = QtWidgets.QHBoxLayout()
        ctrl_layout.addWidget(self.btn_check)
        ctrl_layout.addWidget(self.btn_settings)
        ctrl_layout.addStretch(1)
        ctrl_layout.addWidget(self.btn_open_config)
        ctrl_layout.addWidget(self.btn_open_logs)

        # Log view
        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setReadOnly(True)
        mono = QtGui.QFont('Menlo' if sys.platform == 'darwin' else 'Monospace')
        mono.setStyleHint(QtGui.QFont.Monospace)
        self.log_view.setFont(mono)
        log_box = QtWidgets.QGroupBox('Recent Activity')
        v = QtWidgets.QVBoxLayout()
        v.addWidget(self.log_view)
        log_box.setLayout(v)

        # Central layout
        central = QtWidgets.QWidget()
        cl = QtWidgets.QVBoxLayout(central)
        cl.addWidget(status_box)
        cl.addLayout(ctrl_layout)
        cl.addWidget(log_box, 1)
        self.setCentralWidget(central)

        # Signals
        self.btn_check.clicked.connect(self._check_now)
        self.btn_settings.clicked.connect(self.tray.show_settings)
        self.btn_open_config.clicked.connect(self._reveal_config)
        self.btn_open_logs.clicked.connect(self._reveal_logs)

        # Initial refresh
        self.refresh_from_last()

    def refresh_from_last(self):
        ok = self.tray.last_ok
        if ok is None:
            self.status_label.setText('Status: Not checked yet')
        else:
            self.status_label.setText('Status: OK' if ok else 'Status: DOWN')
        # We only log summaries here; detailed logs are in the file
        self._append_log('Window opened. Use Check Now to test the endpoint.')

    def _append_log(self, line: str):
        self.log_view.append(line)

    def _check_now(self):
        from core import check_api_details
        cfg = self.tray.config
        ok, status, err = check_api_details(cfg.get('api_url'), cfg.get('api_key'))
        if ok:
            self.status_label.setText(f'Status: OK ({status})')
            self._append_log(f'Check OK (status={status})')
        else:
            self.status_label.setText('Status: DOWN')
            self._append_log(f'Check DOWN (status={status}, err={err})')
        # Also update tray icon + internal state
        self.tray.update_status()

    def _reveal_config(self):
        from core import CONFIG_PATH
        if sys.platform == 'darwin':
            QtCore.QProcess.startDetached('open', [str(CONFIG_PATH)])
        else:
            QtCore.QProcess.startDetached(str(CONFIG_PATH))

    def _reveal_logs(self):
        log_path = Path.home() / ('Library/Logs' if sys.platform == 'darwin' else '') / 'api_test_tray.log'
        if sys.platform == 'darwin':
            QtCore.QProcess.startDetached('open', [str(log_path)])
        else:
            QtCore.QProcess.startDetached(str(log_path))

if __name__ == '__main__':
    os.environ['QT_QPA_PLATFORM'] = os.environ.get('QT_QPA_PLATFORM', 'cocoa')
    # Create the application FIRST before any QtWidgets calls that touch platform state.
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    # Ensure system tray is available (after app exists)
    try:
        tray_available = QtWidgets.QSystemTrayIcon.isSystemTrayAvailable()
    except Exception:
        tray_available = False
    if not tray_available:
        # Show a dialog informing the user and keep the main window available for diagnostics
        QtWidgets.QMessageBox.critical(None, 'API Tray Status', 'No system tray available on this system. Opening app window for diagnostics.')
        # Proceed without a tray; the main window can still be used

    # On macOS, allow dock presence; we'll toggle to Regular when opening windows

    tray = TrayApp(app)
    sys.exit(app.exec_())
