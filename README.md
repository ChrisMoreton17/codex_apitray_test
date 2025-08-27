# API Tray Status App

This project provides a small cross-platform system tray application that checks the status of an API and displays a green or red icon accordingly. Users can configure the API URL and optional API key through a settings dialog. Configuration values are stored in `~/.api_tray_config.json`.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the tray application:

```bash
python app.py
```

On the first run, you will be prompted to enter the API URL and optional API key. The application periodically checks the API and updates the tray icon:

- **Green** – API responded successfully.
- **Red** – API request failed or returned a non-OK status.

You can right-click the tray icon to access settings, manually trigger a check, or quit the app.
