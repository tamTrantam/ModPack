@echo off
title Minecraft Forge Server with Playit Tunnel
echo ========================================
echo Launching Minecraft Forge Server...
echo ========================================

REM --- Check if user_jvm_args.txt exists ---
if not exist "user_jvm_args.txt" (
    echo Creating user_jvm_args.txt with default settings...
    echo -Xms4G > user_jvm_args.txt
    echo -Xmx6G >> user_jvm_args.txt
)

REM --- Start Minecraft Server ---
start "Forge Server" cmd /k java @user_jvm_args.txt @libraries/net/minecraftforge/forge/1.20.1-47.4.0/win_args.txt %*

timeout /t 5 >nul
echo.
echo ========================================
echo Starting Playit Tunnel Agent...
echo ========================================

REM --- Check if Playit.gg is installed ---
if not exist "C:\Program Files\playit_gg\bin\playit.exe" (
    echo Playit.gg not found! Please install it first.
    pause
    exit
)

REM --- Start Playit Agent ---
start "Playit Tunnel" cmd /k "C:\Program Files\playit_gg\bin\playit.exe"

echo.
echo Server and Playit tunnel are now running in separate windows.
pause