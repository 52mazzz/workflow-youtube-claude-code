@echo off
rem Envoi en un double-clic : git add, commit, pull (travail de l'autre PC), push.
rem Message facultatif : envoi.bat "pokemon-ia : script"
cd /d "%~dp0"
call trouver_python.bat || (pause & exit /b 1)
%PY% envoi.py %*
pause
