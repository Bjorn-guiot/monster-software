# Monster Energy Scream Challenge

Benodigde installaties:
    python -m pip install PyQt6 sounddevice numpy

Start de applicatie met:
    python soundboard.py

De app toont een dB SPL-schaal van 0 tot 150 dB. Voor correcte, fysieke waarden
moet de CALIBRATION_OFFSET_DB afgestemd worden op de gebruikte meetmicrofoon.


## Shure MV7 instellen

Gebruik de microfoon via USB, niet via XLR; XLR vereist een aparte audio-interface en eigen kalibratie. Stel in de Shure MOTIV-app de MV7 in op **Manual / minimum gain / Flat** en zet compressor, limiter en Auto Level uit, anders beïnvloeden die de score.
