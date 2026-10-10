# Startet die App unter Windows: Transkription, Fraud-Analyse, Dashboard.
#   .\start.ps1             # Dashboard auf http://localhost:7860
#   .\start.ps1 -Analyse    # zusätzlich die Entwickler-Oberfläche auf http://localhost:7861
# Die eigentliche Logik steht in start.py; Ctrl+C beendet alle Teile.
param([switch]$Analyse)

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
$arguments = @("$PSScriptRoot\start.py")
if ($Analyse) { $arguments += "--analyse" }
& $python @arguments
