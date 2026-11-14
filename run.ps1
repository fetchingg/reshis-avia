$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Сначала выполните установку по README.md: python -m venv .venv и pip install -r requirements.txt'
}
& $projectPython manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { throw 'Не удалось применить миграции' }
Write-Host 'Решись Авиа: http://127.0.0.1:8877/ (остановка: Ctrl+C)'
& $projectPython manage.py runserver 127.0.0.1:8877
exit $LASTEXITCODE
