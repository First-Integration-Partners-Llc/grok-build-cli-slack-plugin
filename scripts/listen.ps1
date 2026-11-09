# Foreground listener for Windows. The implementation is scripts/listen.py.
#   pwsh -File ./scripts/listen.ps1
#   pwsh -File ./scripts/listen.ps1 -SelfTest

param(
    [switch] $SelfTest
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $here "listen.py"
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "Python 3 is not on PATH."
}
$pyArgs = @($script)
if ($SelfTest) {
    $pyArgs += "--self-test"
}
& $python.Source @pyArgs
if ($null -ne $LASTEXITCODE) {
    exit $LASTEXITCODE
}
exit 0
