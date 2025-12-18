# Скрипт для запуска приложения с правильным интерпретатором
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Активируем venv
& "$scriptPath\venv\Scripts\Activate.ps1"

# Запускаем приложение
python main.py

# Ожидаем нажатия клавиши перед закрытием
Write-Host "Нажмите любую клавишу для выхода..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

