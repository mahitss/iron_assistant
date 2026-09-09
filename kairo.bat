@echo off
set PYTHONPATH=%~dp0backend;%~dp0;%PYTHONPATH%
python "%~dp0scripts\kairo.py" %*
