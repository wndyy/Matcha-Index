@echo off
echo Creating Python 3.9 virtual environment...
py -3.9 -m venv paddle-env

echo Installing dependencies (this will take a few minutes)...
call paddle-env\Scripts\activate
python -m pip install -r requirements.txt

echo.
echo ============================================
echo Setup complete!
echo.
echo To use the environment, run:
echo   paddle-env\Scripts\activate
echo ============================================