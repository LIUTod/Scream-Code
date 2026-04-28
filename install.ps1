# =============================================================================
#  Scream-Code · 开箱即用安装脚本（Windows PowerShell）
#  在仓库根目录执行:
#    powershell -ExecutionPolicy Bypass -File .\install.ps1
#
#  权限说明：
#    - 普通用户即可运行大部分步骤（创建 .venv、安装 pip 包）
#    - 将 scream 注册到系统 PATH 需要管理员权限
#    - 若未以管理员运行，脚本会自动尝试请求 UAC 提升
# =============================================================================

$ErrorActionPreference = "Stop"

# ── 终端输出工具 ──────────────────────────────────────────
function Write-Die {
    param([string]$Message)
    Write-Host ""
    Write-Host "💥 $Message" -ForegroundColor Red
    exit 1
}

function Write-Step {
    param([string]$Message)
    Write-Host "▶ $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "   $Message" -ForegroundColor DarkGray
}

function Invoke-Safely {
    param(
        [string]$Title,
        [scriptblock]$Action,
        [string]$FixHint = "请检查网络、代理或权限后重试。"
    )
    try {
        & $Action
    } catch {
        Write-Die "$Title 失败。$FixHint"
    }
}

# ── 权限检测与提升 ────────────────────────────────────────
function Test-Admin {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Request-Admin {
    <#
    .SYNOPSIS
        尝试以管理员权限重新启动当前脚本。
    #>
    param([string]$ScriptPath)
    Write-Warn "需要管理员权限才能注册系统 PATH。"
    Write-Info "正在尝试请求 UAC 提升…"
    Start-Sleep -Seconds 1

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "powershell.exe"
    $psi.Arguments = "-ExecutionPolicy Bypass -File `"$ScriptPath`""
    $psi.Verb = "runas"
    $psi.WorkingDirectory = (Get-Location).Path
    try {
        [System.Diagnostics.Process]::Start($psi) | Out-Null
        exit 0
    } catch {
        Write-Warn "UAC 提升请求被拒绝或失败。"
        return $false
    }
}

# ── Python 检测 ───────────────────────────────────────────
function Get-PythonCommand {
    $candidates = @(
        @("python"),
        @("py", "-3")
    )
    foreach ($cmd in $candidates) {
        $exe = $cmd[0]
        if (Get-Command $exe -ErrorAction SilentlyContinue) {
            try {
                & $exe @($cmd[1..($cmd.Length - 1)]) --version *> $null
                return ,$cmd
            } catch {
                continue
            }
        }
    }
    return $null
}

function Test-PythonVersion {
    param([string[]]$PythonCmd)
    try {
        & $PythonCmd[0] @($PythonCmd[1..($PythonCmd.Length - 1)]) -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
        return $true
    } catch {
        return $false
    }
}

# ── PATH 注册 ─────────────────────────────────────────────
function Add-ToSystemPath {
    param([string]$Directory)
    try {
        $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
        $paths = $currentPath -split ';' | Where-Object { $_ -and ($_ -ne $Directory) }
        $newPath = ($paths + $Directory) -join ';'
        [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
        return $true
    } catch {
        return $false
    }
}

function Add-ToUserPath {
    param([string]$Directory)
    try {
        $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
        $paths = $currentPath -split ';' | Where-Object { $_ -and ($_ -ne $Directory) }
        $newPath = ($paths + $Directory) -join ';'
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        return $true
    } catch {
        return $false
    }
}

# ── 主流程 ────────────────────────────────────────────────
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║  🜂 Scream-Code · Windows 一键安装                        ║" -ForegroundColor Magenta
Write-Host "║                                                          ║" -ForegroundColor Magenta
Write-Host "║  需要管理员权限以注册系统 PATH                             ║" -ForegroundColor Magenta
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host "   $Root" -ForegroundColor DarkGray
Write-Host ""

# 检测管理员权限，若未提升则尝试自动提升
$isAdmin = Test-Admin
if (-not $isAdmin) {
    $elevated = Request-Admin -ScriptPath $MyInvocation.MyCommand.Path
    if ($elevated -eq $false) {
        Write-Warn "未获取管理员权限，将继续安装但无法自动注册 PATH。"
        Write-Info "安装完成后请手动将以下路径加入系统 PATH："
        Write-Info "$Root\.venv\Scripts"
    }
}

Write-Step "🐍 检查 Python 环境（需要 3.10+）..."
$pythonCmd = Get-PythonCommand
if ($null -eq $pythonCmd) {
    Write-Die "未检测到 Python。请前往 https://www.python.org/downloads/windows/ 下载并安装，安装时务必勾选 Add Python to PATH。"
}
if (-not (Test-PythonVersion -PythonCmd $pythonCmd)) {
    Write-Die "检测到的 Python 版本低于 3.10。请升级 Python 后重试。"
}
$pythonVersion = (& $pythonCmd[0] @($pythonCmd[1..($pythonCmd.Length - 1)]) --version) 2>&1
Write-Ok "Python 就绪：$pythonVersion"

Write-Step "📎 检查 pip（python -m pip）..."
try {
    & $pythonCmd[0] @($pythonCmd[1..($pythonCmd.Length - 1)]) -m pip --version *> $null
} catch {
    Write-Die "无法使用 pip。请先执行 python -m ensurepip --upgrade，然后重试安装。"
}
Write-Ok "pip 可用"

if (-not (Test-Path ".\requirements.txt")) {
    Write-Die "未找到 requirements.txt，请在项目根目录运行本脚本。"
}
if (-not (Test-Path ".\setup.py")) {
    Write-Die "未找到 setup.py，请在项目根目录运行本脚本。"
}

$venvDir = Join-Path $Root ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvScream = Join-Path $venvDir "Scripts\scream.exe"
$venvScripts = Join-Path $venvDir "Scripts"

Write-Step "🔧 准备项目虚拟环境 (.venv)..."
if (-not (Test-Path $venvDir)) {
    Invoke-Safely -Title "创建虚拟环境" -FixHint "请确认当前目录可写，并以可写权限打开终端。" -Action {
        & $pythonCmd[0] @($pythonCmd[1..($pythonCmd.Length - 1)]) -m venv ".venv"
    }
    Write-Ok "已创建 .venv"
} else {
    Write-Ok "检测到现有 .venv，将复用并升级依赖"
}

if (-not (Test-Path $venvPython)) {
    Write-Die "虚拟环境损坏：未找到 $venvPython。请删除 .venv 后重试。"
}

Write-Host ""
Write-Host "📦 正在安装依赖与命令入口..." -ForegroundColor Cyan
Invoke-Safely -Title "升级 pip / setuptools / wheel" -Action {
    & $venvPython -m pip install --upgrade pip setuptools wheel
}
Invoke-Safely -Title "安装 requirements.txt" -FixHint "可能是网络问题，请检查代理或稍后重试。" -Action {
    & $venvPython -m pip install -r ".\requirements.txt"
}
Invoke-Safely -Title "安装 Scream-Code（pip install -e .）" -FixHint "请确认仓库完整且 setup.py 可用。" -Action {
    & $venvPython -m pip install -e "."
}
Write-Ok "依赖安装完成"

# 写入 .cmd 包装器（使用绝对路径，避免 editable-install finder 潜在问题）
$screamCmd = Join-Path $venvScripts "scream.cmd"
$screamConfigCmd = Join-Path $venvScripts "scream-config.cmd"

@"
@echo off
set PYTHONPATH=$Root
"$venvPython" -m src.main %*
"@ | Set-Content -Path $screamCmd -Encoding UTF8

@"
@echo off
set PYTHONPATH=$Root
"$venvPython" -m src.main config %*
"@ | Set-Content -Path $screamConfigCmd -Encoding UTF8

Write-Ok "已写入启动包装器"

# 注册到系统 PATH
Write-Host ""
Write-Step "🔗 注册 scream 到系统 PATH..."
if ($isAdmin -or (Test-Admin)) {
    if (Add-ToSystemPath -Directory $venvScripts) {
        Write-Ok "已注册到系统 PATH（所有用户）"
        Write-Info "可以直接在 PowerShell / CMD 中输入 scream 启动了"
    } else {
        Write-Warn "无法注册到系统 PATH"
        Write-Info "请手动将以下路径加入系统环境变量 Path："
        Write-Info "$venvScripts"
    }
} else {
    if (Add-ToUserPath -Directory $venvScripts) {
        Write-Ok "已注册到用户 PATH"
        Write-Info "请重启 PowerShell 后输入 scream 启动"
    } else {
        Write-Warn "无法注册到 PATH"
        Write-Info "请手动将以下路径加入环境变量 Path："
        Write-Info "$venvScripts"
    }
}

Write-Host ""
Write-Host "👁️ 正在初始化视觉内核（Playwright Chromium）..." -ForegroundColor Cyan
try {
    & $venvPython -m playwright install chromium
    Write-Ok "Chromium 内核已就绪（/look 功能可用）"
} catch {
    Write-Warn "Chromium 安装失败，通常是网络问题。你可稍后手动执行："
    Write-Host "   $venvPython -m playwright install chromium" -ForegroundColor Yellow
}

Write-Host ""
Write-Step "📁 初始化用户目录..."
$screamHome = Join-Path $HOME ".scream"
$skillsDir = Join-Path $screamHome "skills"
$shotsDir = Join-Path $screamHome "screenshots"
Invoke-Safely -Title "创建 ~/.scream 目录结构" -FixHint "请检查你的用户目录权限。" -Action {
    New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null
    New-Item -ItemType Directory -Force -Path $shotsDir | Out-Null
}
Write-Ok "用户目录已就绪：$skillsDir / $shotsDir"

Write-Host ""
Write-Host "✅ 安装完成，正在启动 Scream-Code 首次配置向导..." -ForegroundColor Green
Write-Host "   （如需填写 API Key，按提示操作即可）" -ForegroundColor DarkGray
Write-Host ""

if (-not (Test-Path $venvScream)) {
    Write-Warn "未找到 $venvScream，尝试使用 Python 模块入口启动。"
    Invoke-Safely -Title "启动 scream" -Action {
        & $venvPython -m src.main
    }
    exit 0
}

Write-Host "下次可直接运行：" -ForegroundColor DarkGray
Write-Host "  scream" -ForegroundColor Cyan
Write-Host ""
Write-Host "────────── 以下为 Scream 输出 ──────────" -ForegroundColor Magenta
& $venvScream
