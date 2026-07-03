@echo off
chcp 65001 >nul
echo ========================================
echo   Claude Pet - 桌面宠物安装脚本
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 安装依赖
echo [1/3] 安装依赖...
pip install -r "%~dp0requirements.txt" -q
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
echo       依赖安装完成

:: 创建 PowerShell Profile（自动启动宠物）
echo [2/3] 配置 PowerShell 自动启动...
set "PROFILE_DIR=%USERPROFILE%\Documents\PowerShell"
if not exist "%PROFILE_DIR%" mkdir "%PROFILE_DIR%"

set "PET_SCRIPT=%~dp0claude_pet.py"
set "PYTHONW=%LOCALAPPDATA%\Python313\pythonw.exe"
if not exist "%PYTHONW%" (
    for /f "delims=" %%i in ('where pythonw 2^>nul') do set "PYTHONW=%%i"
)

:: 写入 Profile（如果不存在则创建，如果已存在则追加）
findstr /C:"claude_pet" "%PROFILE_DIR%\Microsoft.PowerShell_profile.ps1" >nul 2>&1
if errorlevel 1 (
    echo. >> "%PROFILE_DIR%\Microsoft.PowerShell_profile.ps1"
    echo # Claude Pet - 自动启动桌面宠物 >> "%PROFILE_DIR%\Microsoft.PowerShell_profile.ps1"
    echo $petScript = "%PET_SCRIPT:\=\\%" >> "%PROFILE_DIR%\Microsoft.PowerShell_profile.ps1"
    echo $pythonw = "%PYTHONW:\=\\%" >> "%PROFILE_DIR%\Microsoft.PowerShell_profile.ps1"
    echo $existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue ^| >> "%PROFILE_DIR%\Microsoft.PowerShell_profile.ps1"
    echo     Where-Object { $_.CommandLine -match "claude_pet" -and $_.Name -match "python" } >> "%PROFILE_DIR%\Microsoft.PowerShell_profile.ps1"
    echo if (-not $existing -and (Test-Path $petScript)) { >> "%PROFILE_DIR%\Microsoft.PowerShell_profile.ps1"
    echo     Start-Process $pythonw -ArgumentList $petScript -WindowStyle Hidden >> "%PROFILE_DIR%\Microsoft.PowerShell_profile.ps1"
    echo } >> "%PROFILE_DIR%\Microsoft.PowerShell_profile.ps1"
    echo       PowerShell Profile 已配置
) else (
    echo       PowerShell Profile 已存在，跳过
)

:: 复制 Claude Code hook 配置
echo [3/3] 配置 Claude Code Hook...
set "CLAUDE_DIR=%USERPROFILE%\.claude"
if not exist "%CLAUDE_DIR%" mkdir "%CLAUDE_DIR%"

echo.
echo ========================================
echo   安装完成！
echo ========================================
echo.
echo 使用方法:
echo   1. 打开新的 PowerShell 窗口，宠物自动启动
echo   2. 在 Claude Code 所在目录放置 .claude/settings.json
echo   3. 宠物会根据 Claude Code 状态自动切换动画
echo.
echo 手动启动: pythonw "%PET_SCRIPT%"
echo.
pause
