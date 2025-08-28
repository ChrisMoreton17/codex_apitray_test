import os
import sys

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


class TrayApp(QtWidgets.QSystemTrayIcon):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.config = load_config()
        # Backfill defaults for newly added settings
        self.config.setdefault('interval_seconds', 60)
        self.config.setdefault('notify_mode', 'all')
        # Initial neutral icon before first check
        self.setIcon(self._create_icon('gray', label='…'))
        self.setToolTip('API Status Checker')
        self.last_ok = None

        menu = QtWidgets.QMenu()
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
                from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
                app = NSApplication.sharedApplication()
                # Accessory policy still keeps us as a UIElement without Dock, but allows focus
                app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
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

    def update_status(self):
        ok = check_api(self.config.get('api_url'), self.config.get('api_key'))
        color = 'green' if ok else 'red'
        label = '✓' if ok else '!'
        self.setIcon(self._create_icon(color, label=label))
        interval = int(self.config.get('interval_seconds', 60))
        self.setToolTip(f'API status: {"OK" if ok else "DOWN"} • every {interval}s')
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


if __name__ == '__main__':
    os.environ['QT_QPA_PLATFORM'] = os.environ.get('QT_QPA_PLATFORM', 'cocoa')
    # Ensure system tray is available
    if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
        # Fail fast if no tray (e.g., remote sessions without menu bar)
        QtWidgets.QMessageBox.critical(None, 'API Tray Status', 'No system tray available on this system.')
        sys.exit(1)

    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # On macOS, hide Dock icon when running unbundled via python app.py
    if sys.platform == 'darwin':
        try:
            from AppKit import NSApplication, NSApplicationActivationPolicyProhibited
            NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyProhibited)
        except Exception:
            # AppKit (pyobjc) not installed; skipping dock-hide in script mode.
            pass

    tray = TrayApp(app)
    sys.exit(app.exec_())
