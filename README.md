# Monster Energy Scream Challenge

## Windows app without VS Code

Use `dist/MonsterEnergyScreamChallenge.exe`. The target PC does not need Python, VS Code, or any packages installed.

Keep the `.exe` in a folder where it has write permissions. The app creates `highscores.json` and the `daily_exports` folder beside it.

## Running the source code

```powershell
python -m pip install -r requirements.txt
python soundboard.py
```


## Shure MV7 setup

Use the microphone via USB, not XLR; XLR needs a separate audio interface and calibration. In the Shure MOTIV app, set the MV7 to **Manual / minimum gain / Flat** and turn off the compressor, limiter, and Auto Level, otherwise they affect the score.
