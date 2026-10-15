@echo off
rem Met dans PY un Python qui s'execute vraiment : le lanceur "py", sinon "python".
rem Le faux "python" du Microsoft Store echoue a -c et est donc ecarte. Utilise par maj.bat et envoi.bat.
set "PY="
py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
if not defined PY (python -c "import sys" >nul 2>&1 && set "PY=python")
if not defined PY (python3 -c "import sys" >nul 2>&1 && set "PY=python3")
if not defined PY (
  echo Python introuvable. Installe-le depuis https://www.python.org/downloads/ ^(cocher "Add python.exe to PATH"^),
  echo puis desactive les alias "python.exe" du Microsoft Store : Parametres ^> Applications ^> Alias d'execution.
  exit /b 1
)
exit /b 0
