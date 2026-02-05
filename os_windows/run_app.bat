@echo off
REM Скрипт для запуска приложения с правильным интерпретатором
cd /d "%~dp0"
call venv\Scripts\activate.bat
python main.py
pause

