# 启动交易系统的PowerShell脚本

# 获取脚本所在目录
if ($PSScriptRoot) {
    $ScriptDir = $PSScriptRoot
} else {
    # 备选方法：使用当前目录
    $ScriptDir = Get-Location
}

# 显示脚本目录（用于调试）
Write-Host "Script directory: $ScriptDir" -ForegroundColor Yellow

# 切换到脚本所在目录
Set-Location -Path $ScriptDir

# 显示当前目录（用于调试）
Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow

# 列出当前目录的文件（用于调试）
Write-Host "Files in current directory:" -ForegroundColor Yellow
Get-ChildItem | ForEach-Object { Write-Host "  $($_.Name)" }

# 检查server.exe是否存在
if (-not (Test-Path "server.exe")) {
    Write-Host "Error: server.exe not found in current directory" -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
} else {
    Write-Host "Found server.exe" -ForegroundColor Green
}

# 检查trade_executor.py是否存在
if (-not (Test-Path "trade_executor.py")) {
    Write-Host "Error: trade_executor.py not found in current directory" -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
} else {
    Write-Host "Found trade_executor.py" -ForegroundColor Green
}

# 检查Python是否可用
try {
    python --version | Out-Null
} catch {
    Write-Host "Error: Python is not installed or not in PATH" -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
}

# 在后台运行服务器
Write-Host "Starting server..."
Start-Process -FilePath "$ScriptDir\server.exe" -NoNewWindow -PassThru

# 等待服务器启动
Write-Host "Waiting for server to start..."
Start-Sleep -Seconds 3

# 在后台运行监控脚本
Write-Host "Starting monitor..."
$exePath = "C:\同花顺软件\同花顺\xiadan.exe"
$tesseractCmd = "C:\Program Files\Tesseract-OCR\tesseract.exe"

# 构建参数列表，确保包含空格的路径被正确处理
$arguments = @(
    "trade_executor.py",
    "--monitor",
    "--exe_path",
    "`"$exePath`"",
    "--tesseract_cmd",
    "`"$tesseractCmd`""
)

Start-Process -FilePath "python" -ArgumentList $arguments -NoNewWindow -PassThru

# 显示启动成功信息
Write-Host "Trading system started successfully!" -ForegroundColor Green
Write-Host "Server is running in background"
Write-Host "Monitor is watching trade requests"

# 等待用户输入
Read-Host "Press Enter to exit..."
