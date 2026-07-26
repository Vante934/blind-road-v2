@echo off
title 视界导航 - Cloudflare Tunnel
echo ================================
echo  视界导航系统 - 公网隧道
echo ================================
echo.
echo 正在启动Cloudflare隧道...
echo 等待URL生成，约3-5秒...
echo.
cloudflared tunnel --url http://localhost:8000
pause