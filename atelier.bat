@echo off
rem L'atelier en un double-clic : ouvre dans le navigateur la page qui suit toutes les videos et les deux PC (atelier.py).
rem Laisser cette fenetre ouverte (la reduire) ; la fermer arrete l'atelier. Relance : rouvre simplement la page.
cd /d "%~dp0"
call trouver_python.bat || (pause & exit /b 1)
title Atelier TSAR
%PY% atelier.py
pause
