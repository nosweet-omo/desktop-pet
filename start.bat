@echo off
chcp 65001 >nul
title 桌宠 - 陪你写代码
echo.
echo   ╔══════════════════════════╗
echo   ║     桌宠 启动中...      ║
echo   ║   陪你写代码的小伙伴     ║
echo   ╚══════════════════════════╝
echo.
cd /d "%~dp0"
python -u pet.py
pause
