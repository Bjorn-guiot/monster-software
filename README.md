# Monster Energy Scream Challenge

## Hardware Setup: Shure MV7

Use the microphone via USB, not XLR; XLR requires a separate audio interface and its own calibration. In the Shure MOTIV app, configure the MV7 to **Manual / minimum gain / Flat** and disable compressor, limiter, and Auto Level—otherwise they will affect the score.

## Monster Energy Soundboard Application

### Installation

Required packages:
```
python -m pip install PyQt6 sounddevice numpy
```

### Running the Application

Start with:
```
python soundboard.py
```

### Calibration

The app displays a dB SPL scale from 0 to 150 dB. For accurate physical measurements, adjust the `CALIBRATION_OFFSET_DB` to match your measurement microphone.
