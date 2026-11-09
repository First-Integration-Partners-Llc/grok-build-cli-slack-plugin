# Detach the desktop listener and return. Grok runs this on SessionStart.
$ErrorActionPreference = "Continue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$starter = Join-Path $here "start_listener.py"
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    [Console]::Error.WriteLine("Python 3 is required to start the Slack listener.")
    exit 1
}
if ($python.Name -eq "py.exe" -or $python.Name -eq "py") {
    & $python.Source -3 $starter
} else {
    & $python.Source $starter
}
if ($null -ne $LASTEXITCODE) {
    exit $LASTEXITCODE
}
exit 0
