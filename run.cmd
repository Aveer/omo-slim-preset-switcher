@echo off
setlocal
where pyw >nul 2>nul
if %errorlevel%==0 (
    start "" pyw -3 -m omo_slim_preset_switcher
    exit /b
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw -m omo_slim_preset_switcher
    exit /b
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m omo_slim_preset_switcher
    exit /b
)

python -m omo_slim_preset_switcher
