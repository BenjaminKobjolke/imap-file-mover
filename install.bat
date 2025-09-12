@echo off
echo Creating virtual environment...
call python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing requirements...
call pip install -r requirements.txt

echo Checking configuration files...
if not exist settings.json (
    echo Creating settings.json from example...
    copy settings_example.json settings.json
    echo Please update settings.json
) else (
    echo settings.json already exists, skipping...
)

echo Installation complete!

