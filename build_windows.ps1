# Build the Windows executable from this project folder.
$ErrorActionPreference = "Stop"

python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name MonsterEnergyScreamChallenge `
    --icon monster-logo.ico `
    --add-data "logo-clean.png;." `
    soundboard.py

Write-Host "Windows build created: dist\MonsterEnergyScreamChallenge.exe"
