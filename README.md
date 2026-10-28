# 🎅 Santa Pet

A lightweight desktop companion that walks across your screen, reminds you to drink water, and keeps an eye on your PC health.

## Features

| Feature | Description |
|---------|-------------|
| 🎅 Walking Santa | Pixel-art Santa wanders left and right at the bottom of your screen |
| 💧 Water Reminder | Pops up a reminder at your chosen interval (default 30 min) |
| 🏥 PC Doctor | Live report: CPU, RAM, disk, battery, network, uptime |
| 🧹 Cache Cleaner | Scans & clears temp files, browser caches — shows sizes before cleaning |
| ⚙️ Settings | Adjust walking speed and reminder interval |
| 🖱 Draggable | Drag Santa anywhere on your screen |

## Quick Start

### Run from source
```bash
pip install -r requirements.txt
python santa_pet.py
```

### Download exe
Grab the latest `SantaPet.exe` from [Releases](../../releases) — no install needed, just double-click.

## Usage

- **Left-click** Santa → speech bubble greeting
- **Drag** Santa anywhere on screen
- **Right-click** → menu with all features

## Build exe yourself
```bat
build.bat
```
Output goes to `dist\SantaPet.exe`.

## Release a new version

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions builds the exe and creates the release automatically.

## Requirements

- Windows 10 / 11
- Python 3.9+ (to run from source)
