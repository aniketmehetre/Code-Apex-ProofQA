@echo off
setlocal

set PYTHON=.venv\Scripts\python.exe

if "%1"=="setup" goto setup
if "%1"=="lint" goto lint
if "%1"=="test" goto test
if "%1"=="twin" goto twin
if "%1"=="bench" goto bench
if "%1"=="demo" goto demo
if "%1"=="validate-menu" goto validate_menu
if "%1"=="" goto test

echo Unknown target: %1
exit /b 1

:setup
%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install -e .
%PYTHON% -m playwright install chromium
exit /b %ERRORLEVEL%

:lint
%PYTHON% -m ruff check .
exit /b %ERRORLEVEL%

:test
%PYTHON% -m pytest -v %2 %3 %4 %5
exit /b %ERRORLEVEL%

:twin
%PYTHON% apps\shop_twin\backend\main.py
exit /b %ERRORLEVEL%

:bench
shift
%PYTHON% -m proofbench.runner %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %ERRORLEVEL%

:demo
%PYTHON% demo\demo_runner.py
exit /b %ERRORLEVEL%

:validate_menu
%PYTHON% demo\validate_menu.py %2 %3
exit /b %ERRORLEVEL%
