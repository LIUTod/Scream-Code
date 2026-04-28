#!/usr/bin/env python3
"""
Scream-Code · 跨平台统一安装入口

自动检测操作系统并调用对应的安装逻辑，处理权限提升，
确保在 macOS / Linux / Windows 上都能一键完成安装。

用法:
    python3 install.py

权限说明:
    - 基础安装（venv、pip 包）不需要管理员权限
    - 注册系统 PATH 需要管理员权限（自动检测并提示）
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path


# ── 终端样式 ──────────────────────────────────────────────
class _Color:
    RED = "\033[0;31m"
    GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    CYAN = "\033[0;36m"
    MAGENTA = "\033[0;35m"
    BLUE = "\033[0;34m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def _is_color_supported() -> bool:
    return sys.stdout.isatty() and os.environ.get("TERM", "") not in ("", "dumb")


_C = _Color if _is_color_supported() else type("NoColor", (), {k: "" for k in _Color.__dict__ if not k.startswith("_")})()  # type: ignore[assignment]


def _banner() -> None:
    print("")
    print(f"{_C.MAGENTA}{_C.BOLD}  ╔══════════════════════════════════════════════════════════╗{_C.RESET}")
    print(f"{_C.MAGENTA}{_C.BOLD}  ║{_C.RESET}  {_C.CYAN}{_C.BOLD}🜂 Scream-Code{_C.RESET}  {_C.DIM}·{_C.RESET}  {_C.BOLD}跨平台一键安装{_C.RESET}              {_C.MAGENTA}{_C.BOLD}║{_C.RESET}")
    print(f"{_C.MAGENTA}{_C.BOLD}  ╚══════════════════════════════════════════════════════════╝{_C.RESET}")
    print(f"{_C.DIM}     操作系统: {platform.system()} {platform.machine()}{_C.RESET}")
    print("")


def _step(msg: str) -> None:
    print(f"{_C.CYAN}{_C.BOLD}▶{_C.RESET}  {msg}")


def _ok(msg: str) -> None:
    print(f"{_C.GREEN}{_C.BOLD}✅{_C.RESET} {msg}")


def _warn(msg: str) -> None:
    print(f"{_C.YELLOW}{_C.BOLD}⚠️{_C.RESET}  {msg}")


def _die(msg: str) -> None:
    print(f"{_C.RED}{_C.BOLD}💥{_C.RESET} {_C.RED}{msg}{_C.RESET}", file=sys.stderr)
    sys.exit(1)


def _info(msg: str) -> None:
    print(f"{_C.DIM}   {msg}{_C.RESET}")


# ── 权限检测 ──────────────────────────────────────────────
def _is_windows() -> bool:
    return platform.system() == "Windows"


def _is_macos() -> bool:
    return platform.system() == "Darwin"


def _is_linux() -> bool:
    return platform.system() == "Linux"


def _is_root() -> bool:
    try:
        return os.geteuid() == 0  # type: ignore[attr-defined,unused-ignore]
    except AttributeError:
        return False


def _has_sudo() -> bool:
    if _is_windows():
        return False
    try:
        result = subprocess.run(
            ["sudo", "-n", "true"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _is_admin_windows() -> bool:
    if not _is_windows():
        return False
    try:
        import ctypes

        return ctypes.windll.shell32.IsUserAnAdmin() != 0  # type: ignore[attr-defined,unused-ignore]
    except Exception:
        return False


# ── Python 检测 ───────────────────────────────────────────
def _check_python() -> Path:
    _step("🐍 检查 Python 3.10+ 环境…")
    python_exe = Path(sys.executable)
    if sys.version_info < (3, 10):
        _die(
            f"需要 Python 3.10+，当前为 {sys.version}\n"
            f"   • macOS: brew install python@3.12\n"
            f"   • Debian/Ubuntu: sudo apt install python3 python3-venv python3-pip\n"
            f"   • 官网: https://www.python.org/downloads/"
        )
    _ok(f"Python 就绪: {sys.version.split()[0]}")
    return python_exe


def _check_pip(python: Path) -> None:
    _step("📎 检查 pip…")
    try:
        subprocess.run(
            [str(python), "-m", "pip", "--version"],
            check=True,
            capture_output=True,
            timeout=30,
        )
    except Exception:
        _die(
            "无法执行 pip。请安装 pip:\n"
            "   • python3 -m ensurepip --upgrade\n"
            "   • 或 sudo apt install python3-pip"
        )
    _ok("pip 可用")


# ── 核心安装逻辑（POSIX）───────────────────────────────────
def _install_posix(python: Path) -> int:
    root = Path(__file__).resolve().parent
    os.chdir(root)

    req_file = root / "requirements.txt"
    setup_file = root / "setup.py"
    if not req_file.exists():
        _die("未找到 requirements.txt，请在仓库根目录运行本脚本。")
    if not setup_file.exists():
        _die("未找到 setup.py，请在仓库根目录运行本脚本。")

    venv_dir = root / ".venv"
    venv_python = venv_dir / "bin" / "python3"
    venv_pip = venv_dir / "bin" / "pip"

    _step("🔧 准备虚拟环境 (.venv)…")
    if not venv_dir.exists():
        subprocess.run([str(python), "-m", "venv", str(venv_dir)], check=True)
        _ok("已创建 .venv")
    else:
        _ok("已存在 .venv，将复用并升级")

    if not (venv_python.exists() and venv_pip.exists()):
        _die(f"虚拟环境异常: {venv_python}")

    print("")
    print(f"{_C.BLUE}{_C.BOLD}📦 正在安装依赖…{_C.RESET}")
    subprocess.run([str(venv_pip), "install", "-q", "--upgrade", "pip", "setuptools", "wheel"], check=True)
    subprocess.run([str(venv_pip), "install", "-q", "-r", str(req_file)], check=True)
    subprocess.run([str(venv_pip), "install", "-q", "-e", str(root)], check=True)
    _ok("依赖安装完成")

    # 写入启动包装器（使用绝对路径，避免 editable-install finder 在 Python 3.14+ 失效）
    venv_scream = venv_dir / "bin" / "scream"
    venv_scream.write_text(
        '#!/usr/bin/env bash\n'
        'set -euo pipefail\n'
        f'ROOT="{root}"\n'
        'export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"\n'
        f'exec "$ROOT/.venv/bin/python3" -m src.main "$@"\n',
        encoding="utf-8",
    )
    venv_scream.chmod(0o755)
    venv_scream_config = venv_dir / "bin" / "scream-config"
    venv_scream_config.write_text(
        '#!/usr/bin/env bash\n'
        'set -euo pipefail\n'
        f'ROOT="{root}"\n'
        'export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"\n'
        f'exec "$ROOT/.venv/bin/python3" -m src.main config "$@"\n',
        encoding="utf-8",
    )
    venv_scream_config.chmod(0o755)
    _ok("已写入启动包装器")

    # PATH 注册
    print("")
    _step("🔗 注册 scream 到系统 PATH…")
    path_targets = [Path("/usr/local/bin"), Path("/opt/local/bin"), Path.home() / ".local" / "bin"]
    path_installed = False
    target_bin: Path | None = None

    for target in path_targets:
        if target.exists() and os.access(target, os.W_OK):
            target_bin = target
            break

    if target_bin is None:
        target_bin = Path.home() / ".local" / "bin"
        target_bin.mkdir(parents=True, exist_ok=True)

    def _install_wrapper(src: Path, dst: Path) -> bool:
        wrapper = f'#!/usr/bin/env bash\nset -euo pipefail\nexec "{src}" "$@"\n'
        try:
            if dst.exists() or dst.is_symlink():
                dst.unlink()
            dst.write_text(wrapper, encoding="utf-8")
            dst.chmod(0o755)
            return True
        except OSError:
            return False

    scream_link = target_bin / "scream"
    scream_config_link = target_bin / "scream-config"

    if _install_wrapper(venv_scream, scream_link) and _install_wrapper(venv_scream_config, scream_config_link):
        _ok(f"已注册到 {target_bin}")
        _info("可以直接在终端输入 scream 启动了")
        path_installed = True
    else:
        if _has_sudo() or _is_root():
            _warn(f"无法写入 {target_bin}，尝试 sudo…")
            try:
                wrapper = f'#!/usr/bin/env bash\nset -euo pipefail\nexec "{venv_scream}" "$@"\n'
                subprocess.run(["sudo", "tee", str(scream_link)], input=wrapper, text=True, check=True)
                subprocess.run(["sudo", "chmod", "+x", str(scream_link)], check=True)
                wrapper = f'#!/usr/bin/env bash\nset -euo pipefail\nexec "{venv_scream_config}" "$@"\n'
                subprocess.run(["sudo", "tee", str(scream_config_link)], input=wrapper, text=True, check=True)
                subprocess.run(["sudo", "chmod", "+x", str(scream_config_link)], check=True)
                _ok(f"已使用 sudo 注册到 {target_bin}")
                path_installed = True
            except Exception:
                _warn("sudo 注册失败")
        else:
            _warn(f"无权限写入 {target_bin}")

    if not path_installed:
        _warn("未注册到系统 PATH")
        _info("请手动将以下目录加入 PATH：")
        _info(f"export PATH=\"{venv_dir / 'bin'}:$PATH\"")
        _info("（可添加到 ~/.bashrc 或 ~/.zshrc）")

    # 检查用户级 PATH
    if str(target_bin) not in os.environ.get("PATH", "") and str(target_bin).startswith(str(Path.home())):
        _warn(f"{target_bin} 不在当前 PATH 中")
        _info("请执行: export PATH=\"{}:$PATH\"".format(target_bin))
        _info("（建议添加到 ~/.bashrc 或 ~/.zshrc）")

    # Playwright
    print("")
    print(f"{_C.BLUE}{_C.BOLD}👁️ 正在初始化视觉引擎 (Playwright)…{_C.RESET}")
    try:
        subprocess.run([str(venv_python), "-m", "playwright", "install", "chromium"], check=True)
        _ok("Chromium 已就绪")
    except Exception:
        _warn("Chromium 安装未成功，可稍后手动执行:")
        _info(f"{venv_python} -m playwright install chromium")

    # 用户目录
    print("")
    _step("📁 创建用户配置目录…")
    scream_home = Path.home() / ".scream"
    (scream_home / "skills").mkdir(parents=True, exist_ok=True)
    (scream_home / "screenshots").mkdir(parents=True, exist_ok=True)
    _ok("~/.scream 已就绪")

    # 启动
    print("")
    print(f"{_C.GREEN}{_C.BOLD}✅ 安装完成！正在启动 Scream-Code…{_C.RESET}")
    print(f"{_C.DIM}   （若需配置 API Key，将随后进入交互向导）{_C.RESET}")
    print("")
    os.execv(str(venv_python), [str(venv_python), "-m", "src.main"])
    return 0  # never reached


# ── 核心安装逻辑（Windows）─────────────────────────────────
def _install_windows(python: Path) -> int:
    root = Path(__file__).resolve().parent
    os.chdir(root)

    req_file = root / "requirements.txt"
    setup_file = root / "setup.py"
    if not req_file.exists():
        _die("未找到 requirements.txt，请在仓库根目录运行本脚本。")
    if not setup_file.exists():
        _die("未找到 setup.py，请在仓库根目录运行本脚本。")

    is_admin = _is_admin_windows()
    if not is_admin:
        _warn("未以管理员身份运行，PATH 注册将受限。")
        _info("建议以管理员身份重新运行此脚本以自动注册 PATH。")
        _info("右键点击 PowerShell → 以管理员身份运行")

    venv_dir = root / ".venv"
    venv_python = venv_dir / "Scripts" / "python.exe"
    venv_scripts = venv_dir / "Scripts"

    _step("🔧 准备虚拟环境 (.venv)…")
    if not venv_dir.exists():
        subprocess.run([str(python), "-m", "venv", str(venv_dir)], check=True)
        _ok("已创建 .venv")
    else:
        _ok("已存在 .venv，将复用并升级")

    if not venv_python.exists():
        _die(f"虚拟环境异常: {venv_python}")

    print("")
    print(f"{_C.BLUE}{_C.BOLD}📦 正在安装依赖…{_C.RESET}")
    subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], check=True)
    subprocess.run([str(venv_python), "-m", "pip", "install", "-r", str(req_file)], check=True)
    subprocess.run([str(venv_python), "-m", "pip", "install", "-e", str(root)], check=True)
    _ok("依赖安装完成")

    # PATH 注册
    # pip install -e . 已自动生成 scream.exe / scream-config.exe（调用 cli_entry）
    print("")
    _step("🔗 注册 scream 到系统 PATH…")
    import winreg

    def _add_to_path_machine(directory: str) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                current, _ = winreg.QueryValueEx(key, "Path")
                paths = [p for p in current.split(";") if p and p != directory]
                new_path = ";".join(paths + [directory])
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                # 通知系统环境变量已更改
                import ctypes

                HWND_BROADCAST = 0xFFFF
                WM_SETTINGCHANGE = 0x1A
                ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment")
            return True
        except Exception:
            return False

    def _add_to_path_user(directory: str) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                try:
                    current, _ = winreg.QueryValueEx(key, "Path")
                except FileNotFoundError:
                    current = ""
                paths = [p for p in current.split(";") if p and p != directory]
                new_path = ";".join(paths + [directory])
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            return True
        except Exception:
            return False

    path_installed = False
    if is_admin:
        if _add_to_path_machine(str(venv_scripts)):
            _ok("已注册到系统 PATH（所有用户）")
            _info("可以直接在 PowerShell / CMD 中输入 scream 启动")
            path_installed = True
        else:
            _warn("无法注册到系统 PATH")
    else:
        if _add_to_path_user(str(venv_scripts)):
            _ok("已注册到用户 PATH")
            _info("请重启 PowerShell 后输入 scream 启动")
            path_installed = True
        else:
            _warn("无法注册到 PATH")

    if not path_installed:
        _info("请手动将以下路径加入环境变量 Path：")
        _info(str(venv_scripts))

    # Playwright
    print("")
    print(f"{_C.BLUE}{_C.BOLD}👁️ 正在初始化视觉引擎 (Playwright)…{_C.RESET}")
    try:
        subprocess.run([str(venv_python), "-m", "playwright", "install", "chromium"], check=True)
        _ok("Chromium 已就绪")
    except Exception:
        _warn("Chromium 安装未成功，可稍后手动执行:")
        _info(f'{venv_python} -m playwright install chromium')

    # 用户目录
    print("")
    _step("📁 创建用户配置目录…")
    scream_home = Path.home() / ".scream"
    (scream_home / "skills").mkdir(parents=True, exist_ok=True)
    (scream_home / "screenshots").mkdir(parents=True, exist_ok=True)
    _ok("~/.scream 已就绪")

    # 启动
    print("")
    print(f"{_C.GREEN}{_C.BOLD}✅ 安装完成！正在启动 Scream-Code…{_C.RESET}")
    print(f"{_C.DIM}   （若需配置 API Key，将随后进入交互向导）{_C.RESET}")
    print("")
    os.execv(str(venv_python), [str(venv_python), "-m", "src.main"])
    return 0  # never reached


# ── 主入口 ────────────────────────────────────────────────
def main() -> int:
    _banner()

    python = _check_python()
    _check_pip(python)

    if _is_windows():
        return _install_windows(python)
    elif _is_macos() or _is_linux():
        return _install_posix(python)
    else:
        _warn(f"未识别的操作系统: {platform.system()}")
        _info("尝试使用 POSIX 安装流程…")
        return _install_posix(python)


if __name__ == "__main__":
    raise SystemExit(main())
