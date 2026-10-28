# 🎅 Santa Pet

A desktop companion that walks across your screen, reminds you to drink water, tracks your PC health, and syncs your to-do list with **Google Tasks**.

![Santa walking across the screen](.github/preview.gif)

---

## Features

| Feature | Description |
|---------|-------------|
| 🎅 Animated Santa | 3D sprite Santa wanders across the bottom of your screen |
| 💧 Water Reminder | Pop-up at your chosen interval (default 30 min) |
| 🏥 PC Health | Live CPU, RAM, disk, battery, network & uptime report |
| 🧹 Cache Cleaner | Scans temp files and browser caches — shows sizes before cleaning |
| ✅ Google Tasks | To-do list synced with your Google Tasks account |
| ⚙️ Settings | Adjust walk speed and reminder interval |
| 🖱 Draggable | Drag Santa anywhere on screen |

---

## Requirements

- **Windows 10 / 11**
- **Python 3.9+**

---

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/Linson-J/santa-pet.git
cd santa-pet
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. (Optional) Connect Google Tasks

To sync your to-do list with Google Tasks:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → **APIs & Services** → **Library** → enable **Google Tasks API**
3. **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
   - Application type: **Desktop app**
4. Download the JSON file → rename it to `credentials.json`
5. Move it to:
   ```
   C:\Users\<YourName>\AppData\Roaming\SantaPet\credentials.json
   ```
6. Launch the app and right-click Santa → **Google Tasks** → **Connect**  
   A browser tab will open — sign in with your Google account and approve access.

---

## How to Run

```bash
python santa_pet.py
```

Santa will appear at the bottom-right of your screen.

| Action | What it does |
|--------|--------------|
| **Left-click** Santa | Speech bubble greeting |
| **Right-click** Santa | Opens the feature menu |
| **Drag** Santa | Move him anywhere |

---

## Build a standalone EXE

```bat
build.bat
```

Output: `dist\SantaPet.exe` — no Python install needed, just double-click.

### Release a new version

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions builds the EXE and publishes it as a GitHub Release automatically.

---

## Project Structure

```
santa-pet/
├── santa_pet.py        # Main app — window, animation, menus
├── todo_manager.py     # Google Tasks integration & To-Do window
├── assets/             # Sprite frames (CC0 — OpenGameArt)
│   ├── walk/           # Walking animation (13 frames)
│   ├── idle/           # Idle animation (16 frames)
│   ├── run/            # Running animation (11 frames)
│   ├── jump/           # Jump animation (16 frames)
│   └── slide/          # Slide animation (11 frames)
├── requirements.txt
└── build.bat
```

---

## Credits

- Santa sprites: [pzUH on OpenGameArt](https://opengameart.org/content/santa-claus-free-sprites) — **CC0 Public Domain**
