@echo off
REM Wrapper the Windows Scheduled Task calls. Edit the python path if you use a venv.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py >> run.log 2>&1
) else (
    python run.py >> run.log 2>&1
)
