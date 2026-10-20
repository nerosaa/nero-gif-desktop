# Run on a Windows machine with Python 3.11+ installed.
# Produces dist\NeroGifConverter\ and NERO-Tools-GIF-Converter-windows-x64.zip
# NEVER set NERO_LICENSE_SECRET in this script or commit a real secret.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name NeroGifConverter `
  --add-data "assets\DejaVuSans.ttf;assets" `
  --hidden-import nero_gif `
  --hidden-import nero_gif.gui `
  --hidden-import nero_gif.converter `
  --hidden-import nero_gif.license_check `
  --hidden-import nero_gif.paths `
  --hidden-import nero_gif.cli `
  run_gui.py

if (-not (Test-Path "dist\NeroGifConverter\NeroGifConverter.exe")) {
  throw "NeroGifConverter.exe not produced"
}

$stage = "artifact-stage\NERO-Tools-GIF-Converter"
if (Test-Path "artifact-stage") { Remove-Item -Recurse -Force "artifact-stage" }
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item -Recurse -Force "dist\NeroGifConverter\*" $stage\
Copy-Item -Force "README.md" "$stage\README.md"
Copy-Item -Force "README-WINDOWS.txt" "$stage\README-WINDOWS.txt"
Copy-Item -Force "third_party\FFMPEG_NOTICE.md" "$stage\FFMPEG_NOTICE.md"
Copy-Item -Force "LICENSE" "$stage\LICENSE"

$zip = "NERO-Tools-GIF-Converter-windows-x64.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path "$stage\*" -DestinationPath $zip -CompressionLevel Optimal

Write-Host "Output folder: dist\NeroGifConverter\"
Write-Host "Artifact zip:  $zip"
Write-Host "Buyers need ffmpeg on PATH (or ffmpeg.exe beside the exe). See third_party\FFMPEG_NOTICE.md"
