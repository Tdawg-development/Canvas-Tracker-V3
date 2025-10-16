@echo off
echo Canvas Tracker V3 - Bulk Integration Test Runner
echo ==============================================

echo.
echo This script will run the bulk Canvas integration test that syncs
echo ALL available courses from your Canvas instance to the database.
echo.

cd /d "%~dp0"
python test-environment\test_bulk_canvas_integration.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Test execution failed with error code %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Test execution completed successfully.
pause