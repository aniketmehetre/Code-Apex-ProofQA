@echo off
setlocal

set PYTHON=.venv\Scripts\python.exe

if "%1"=="setup" goto setup
if "%1"=="lint" goto lint
if "%1"=="test" goto test
if "%1"=="twin" goto twin
if "%1"=="bench" goto bench
if "%1"=="demo" goto demo
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
echo Twin target: (stub for Phase 1)
exit /b 0

:bench
echo Bench target: (stub for Phase 9)
exit /b 0

:demo
echo Demo target: (stub for Phase 13)
exit /b 0
