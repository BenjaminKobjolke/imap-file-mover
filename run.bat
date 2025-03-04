@echo off
echo Running IMAP File Mover...
call %~dp0\venv\Scripts\activate.bat
python main.py
pause
