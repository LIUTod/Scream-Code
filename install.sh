#!/usr/bin/env bash
# =============================================================================
#  Scream-Code · 开箱即用安装脚本（macOS / Linux）
#  在仓库根目录执行:  bash install.sh   或   chmod +x install.sh && ./install.sh
#
#  权限说明：
#    - 普通用户即可运行大部分步骤（创建 .venv、安装 pip 包）
#    - 将 scream 注册到系统 PATH 需要管理员权限
#    - 脚本会自动检测权限并尝试最佳安装路径
# =============================================================================
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
cd "$ROOT" || exit 1

# ── 终端样式 ──────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BLUE='\033[0;34m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

die() {
  echo -e "${RED}${BOLD}💥${RESET} ${RED}$*${RESET}" >&2
  exit 1
}

warn() { echo -e "${YELLOW}${BOLD}⚠️${RESET}  $*"; }
ok()   { echo -e "${GREEN}${BOLD}✅${RESET} $*"; }
step() { echo -e "${CYAN}${BOLD}▶${RESET}  $*"; }
info() { echo -e "${DIM}$*${RESET}"; }

banner() {
  echo ""
  echo -e "${MAGENTA}${BOLD}  ╔══════════════════════════════════════════════════════════╗${RESET}"
  echo -e "${MAGENTA}${BOLD}  ║${RESET}  ${CYAN}${BOLD}🜂 Scream-Code${RESET}  ${DIM}·${RESET}  ${BOLD}跨平台一键安装${RESET}              ${MAGENTA}${BOLD}║${RESET}"
  echo -e "${MAGENTA}${BOLD}  ╚══════════════════════════════════════════════════════════╝${RESET}"
  echo -e "${DIM}     $ROOT${RESET}"
  echo ""
}

# ── 权限检测 ──────────────────────────────────────────────
_is_root() {
  [ "$(id -u)" -eq 0 ]
}

_has_sudo() {
  command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null
}

_can_write_dir() {
  [ -w "$1" ] 2>/dev/null
}

# 检测最佳 PATH 安装位置
_detect_path_target() {
  local targets=("/usr/local/bin" "/opt/local/bin" "$HOME/.local/bin")
  for d in "${targets[@]}"; do
    if [ -d "$d" ] && _can_write_dir "$d"; then
      echo "$d"
      return 0
    fi
  done
  # 都不可写时，创建用户目录
  local user_bin="$HOME/.local/bin"
  mkdir -p "$user_bin" 2>/dev/null || true
  echo "$user_bin"
}

# 尝试用 sudo 执行命令
_try_sudo() {
  if _is_root; then
    "$@"
  elif _has_sudo; then
    sudo "$@"
  else
    return 1
  fi
}

banner

# ── 1. Python & pip ───────────────────────────────────────
step "🐍 检查 Python 3 环境…"
if ! command -v python3 >/dev/null 2>&1; then
  die "未找到 python3。请先安装 Python ${BOLD}3.10+${RESET}：
  • macOS: ${CYAN}brew install python@3.12${RESET}
  • Debian/Ubuntu: ${CYAN}sudo apt install python3 python3-venv python3-pip${RESET}
  • 官网: ${CYAN}https://www.python.org/downloads/${RESET}"
fi

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  die "需要 Python ${BOLD}3.10+${RESET}，当前为：${BOLD}$(python3 --version 2>&1)${RESET}"
fi
ok "Python 就绪：${BOLD}$(python3 --version 2>&1)${RESET}"

step "📎 检查 pip（python3 -m pip）…"
if ! python3 -m pip --version >/dev/null 2>&1; then
  die "无法执行 ${BOLD}python3 -m pip${RESET}。请安装 pip：
  • ${CYAN}python3 -m ensurepip --upgrade${RESET}
  • 或 ${CYAN}sudo apt install python3-pip${RESET}"
fi
ok "pip 可用：${DIM}$(python3 -m pip --version 2>&1 | head -1)${RESET}"

[[ -f "$ROOT/requirements.txt" ]] || die "未找到 ${BOLD}requirements.txt${RESET}，请在仓库根目录运行本脚本。"
[[ -f "$ROOT/setup.py" ]] || die "未找到 ${BOLD}setup.py${RESET}，请在仓库根目录运行本脚本。"

# ── 虚拟环境（规避 PEP 668「外部管理环境」、不污染系统 Python）──
VENV="$ROOT/.venv"
PY="$VENV/bin/python3"
PIP="$VENV/bin/pip"

step "🔧 准备项目专用环境 ${DIM}(.venv)${RESET}…"
if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV" || die "无法创建虚拟环境：${BOLD}$VENV${RESET}"
  ok "已创建 .venv"
else
  ok "已存在 .venv，将复用并升级依赖"
fi

[[ -x "$PY" && -x "$PIP" ]] || die "虚拟环境异常：缺少 ${BOLD}$PY${RESET}"

# ── 2. pip install -e . ───────────────────────────────────
echo ""
echo -e "${BLUE}${BOLD}📦 正在安装 Scream-Code 依赖…${RESET}"
echo -e "${DIM}   （实际为可编辑安装至本仓库 .venv，便于 scream 命令与依赖隔离）${RESET}"
"$PIP" install -q --upgrade pip setuptools wheel || die "pip / setuptools 升级失败"
"$PIP" install -q -r "$ROOT/requirements.txt" || die "安装 requirements.txt 失败"
"$PIP" install -q -e "$ROOT" || die "editable 安装失败（pip install -e .）"
ok "Scream-Code 已安装"

# ── 3. 写入启动包装器 ─────────────────────────────────────
# pip install -e . 生成的入口依赖 editable-install finder，在 Python 3.14+
# 下从 PATH 调用时可能无法正确解析 src 包。这里使用 PYTHONPATH 兜底包装器，
# 确保任意 cwd 都能直接执行 scream / scream-config。
# __main__ 块已适配：无参数时自动调用 cli_entry() 启动 TUI。
cat >"$VENV/bin/scream" <<EOF
#!/usr/bin/env bash
set -euo pipefail
ROOT="$ROOT"
export PYTHONPATH="\$ROOT\${PYTHONPATH:+:\$PYTHONPATH}"
exec "\$ROOT/.venv/bin/python3" -m src.main "\$@"
EOF
chmod +x "$VENV/bin/scream"

cat >"$VENV/bin/scream-config" <<EOF
#!/usr/bin/env bash
set -euo pipefail
ROOT="$ROOT"
export PYTHONPATH="\$ROOT\${PYTHONPATH:+:\$PYTHONPATH}"
exec "\$ROOT/.venv/bin/python3" -m src.main config "\$@"
EOF
chmod +x "$VENV/bin/scream-config"
ok "已写入启动包装器（scream / scream-config）"

# ── 4. 注册到系统 PATH ────────────────────────────────────
echo ""
step "🔗 注册 scream 到系统 PATH…"

PATH_TARGET="$(_detect_path_target)"
SCREAM_LINK="$PATH_TARGET/scream"
SCREAM_CONFIG_LINK="$PATH_TARGET/scream-config"

_install_to_path() {
  local src="$1"
  local dst="$2"
  if [ -L "$dst" ] || [ -f "$dst" ]; then
    rm -f "$dst" 2>/dev/null || _try_sudo rm -f "$dst" 2>/dev/null || true
  fi
  # 写入 PATH 包装器（直接调用 venv 中的入口）
  local wrapper
  wrapper="#!/usr/bin/env bash\nset -euo pipefail\nexec \"$src\" \"\$@\"\n"
  if _can_write_dir "$PATH_TARGET"; then
    printf '%b' "$wrapper" > "$dst"
    chmod +x "$dst"
  else
    if _has_sudo; then
      printf '%b' "$wrapper" | sudo tee "$dst" >/dev/null
      sudo chmod +x "$dst"
    else
      return 1
    fi
  fi
}

if _install_to_path "$VENV/bin/scream" "$SCREAM_LINK" && \
   _install_to_path "$VENV/bin/scream-config" "$SCREAM_CONFIG_LINK"; then
  ok "已注册到 ${BOLD}$PATH_TARGET${RESET}"
  info "   可以直接在终端输入 ${CYAN}scream${RESET} 启动了"
else
  warn "无法写入 ${BOLD}$PATH_TARGET${RESET}"
  echo -e "   ${YELLOW}请手动将以下目录加入 PATH：${RESET}"
  echo -e "   ${CYAN}export PATH=\"$VENV/bin:\$PATH\"${RESET}"
  echo -e "   ${DIM}（可添加到 ~/.bashrc 或 ~/.zshrc）${RESET}"
fi

# 如果安装在用户目录，提示 source
if [[ "$PATH_TARGET" == "$HOME"* ]]; then
  # 检查是否已在 PATH 中
  if [[ ":$PATH:" != *":$PATH_TARGET:"* ]]; then
    warn "$PATH_TARGET 不在当前 PATH 中"
    echo -e "   请执行以下命令使其生效："
    echo -e "   ${CYAN}export PATH=\"$PATH_TARGET:\$PATH\"${RESET}"
    echo -e "   ${DIM}（建议添加到 ~/.bashrc 或 ~/.zshrc）${RESET}"
  fi
fi

# ── 5. Playwright Chromium ────────────────────────────────
echo ""
echo -e "${BLUE}${BOLD}👁️ 正在初始化视觉引擎内核 (Playwright)…${RESET}"
if "$PY" -m playwright install chromium; then
  ok "Chromium 浏览器内核已就绪（/look 网页快照等能力）"
else
  warn "Playwright Chromium 安装未完全成功，可稍后手动执行："
  echo -e "   ${CYAN}$PY -m playwright install chromium${RESET}"
fi

# ── 6. 用户目录 ───────────────────────────────────────────
echo ""
step "📁 创建用户配置与技能目录…"
: "${HOME:?未设置 HOME，无法创建用户配置目录}"
mkdir -p "${HOME}/.scream/skills" "${HOME}/.scream/screenshots" || die "无法创建 ~/.scream 子目录"
ok "${DIM}~/.scream/skills${RESET} 与 ${DIM}~/.scream/screenshots${RESET} 已就绪"

# ── 7. 首次启动 ───────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}✅ 安装完成！正在启动 Scream-Code 首次配置向导…${RESET}"
echo -e "${DIM}   （若需配置 API Key，将随后进入交互；Ctrl+C 可中断）${RESET}"
echo ""

SCREAM_BIN="$VENV/bin/scream"
[[ -x "$SCREAM_BIN" ]] || die "未找到可执行文件：${BOLD}$SCREAM_BIN${RESET}"

echo -e "${DIM}────────────────────────────────────────${RESET}"
echo -e "${MAGENTA}${BOLD}        以下为 Scream 输出         ${RESET}"
echo -e "${DIM}────────────────────────────────────────${RESET}"
exec "$SCREAM_BIN"
