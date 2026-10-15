@echo off
rem Mise a jour en un double-clic : git pull, puis relie les nouveaux skills a ~/.claude.
cd /d "%~dp0"
call trouver_python.bat || (pause & exit /b 1)
%PY% setup.py --pull
pause
