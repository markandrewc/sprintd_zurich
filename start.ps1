# Startet die App: Transkriptions-Dienst, Fraud-Analyse-Dienst und Dashboard, je in einem eigenen Fenster.
#   .\start.ps1             # Dashboard auf http://localhost:7860
#   .\start.ps1 -Analyse    # zusätzlich die Entwickler-Oberfläche auf http://localhost:7861
# Ein Fenster schliessen (oder Ctrl+C darin) beendet den jeweiligen Teil.
param([switch]$Analyse)

$root = $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

function Start-Part($title, $module) {
    Start-Process powershell -WorkingDirectory $root -ArgumentList "-NoExit", "-Command",
        "`$Host.UI.RawUI.WindowTitle = '$title'; `$env:PYTHONIOENCODING = 'utf-8'; & '$python' -m $module"
}

Start-Part "Transkription (8001)" "transcription.api"
Start-Part "Fraud-Analyse (8002)" "fraud_analysis.api"
Start-Part "Dashboard (7860)" "dashboard.app"
if ($Analyse) { Start-Part "Analyse-UI (7861)" "analysis_ui.app" }

Write-Host "Gestartet. Dashboard: http://localhost:7860  (die Modelle brauchen beim ersten Start etwa eine Minute)"
if ($Analyse) { Write-Host "Analyse-UI: http://localhost:7861" }
