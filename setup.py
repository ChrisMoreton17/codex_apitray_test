from setuptools import setup

APP = ['app.py']  # entry point script
OPTIONS = {
    # 'argv_emulation': True,   # remove this line to avoid Carbon dependency
    'packages': ['requests', 'charset_normalizer'],
    'includes': [
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'sip',
        'core',
    ],
    'qt_plugins': ['platforms', 'styles', 'imageformats'],  # include key Qt plugin groups
    'plist': {
        'LSUIElement': False,
        'CFBundleName': 'API Test Tray',
        'CFBundleIdentifier': 'com.example.apitesttray',
    },
}

setup(
    app=APP,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    python_requires='>=3.8',
    name='API Test Tray',
)
