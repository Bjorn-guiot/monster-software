# Monster Energy Scream Challenge

## Windows app without VS Code

Use `dist/MonsterEnergyScreamChallenge.exe`. The target PC does not need Python, VS Code, or any packages installed.

Keep the `.exe` in a folder where it has write permissions. The app creates `highscores.json` and the `daily_exports` folder beside it.

## macOS app

The same source code works on macOS, but a native `.app` must be built on a Mac. On the Mac, open Terminal in this folder and run:

```bash
chmod +x build_macos.sh
./build_macos.sh
```

The finished app is `dist/MonsterEnergyScreamChallenge.app`. On its first start, allow microphone access in **System Settings → Privacy & Security → Microphone**. Build separately on Apple Silicon and Intel Macs when you need native packages for both processor types.

For Gmail delivery on macOS, set the app password in Terminal before opening the app:

```bash
launchctl setenv MONSTER_SMTP_APP_PASSWORD "YOUR_GMAIL_APP_PASSWORD"
open dist/MonsterEnergyScreamChallenge.app
```

Do not put the Gmail app password into the source code.

## Rebuilding the Windows app

On Windows, run:

```powershell
.\build_windows.ps1
```

## Gmail delivery setup

The daily Excel export is sent from `screamchallenge@gmail.com` to `bjornguiot@gmail.com`. Create a Gmail app password, then run this once in PowerShell on the festival PC, replacing the placeholder with the app password:

```powershell
[Environment]::SetEnvironmentVariable("MONSTER_SMTP_APP_PASSWORD", "PASTE_YOUR_GMAIL_APP_PASSWORD_HERE", "User")
```

Close and reopen the app afterwards. Never put the Gmail app password into this source code or share it in chat.

## Running the source code

```powershell
python -m pip install -r requirements.txt
python soundboard.py
```


## Shure MV7 setup

Use the microphone via USB, not XLR; XLR needs a separate audio interface and calibration. In the Shure MOTIV app, set the MV7 to **Manual / minimum gain / Flat** and turn off the compressor, limiter, and Auto Level, otherwise they affect the score.
