<img width="1267" height="411" alt="1111" src="https://github.com/user-attachments/assets/a5e50df1-af96-4582-b543-c072fa90f5bb" />

# Scream Code

> 一个中文友好、Local-First 的 AI Agent终端助手。
>
> 目标不是"聊天更花哨"，而是让 AI 在你的机器上接管真实生产力链路。

Scream Code 面向开发者、知识工作者以及零基础开发者，提供：

- **本地优先**：会话、记忆、技能、工具执行全部在你可控的工作区与主机环境
- **中文优先**：交互文案、命令语义、错误提示对中文工作流做过深度适配
- **双通道网关**：终端 TUI 主通道 + 飞书长连接侧车子通道，兼顾本地效率与移动协作
- **可扩展架构**：`SkillsRegistry`（斜杠技能）与 `ToolsRegistry`（LLM 工具）分层解耦

---

## 目录

- [快速开始](#快速开始)
- [安装指南](#安装指南)
  - [macOS / Linux](#macos--linux)
  - [Windows](#windows)
  - [通用安装入口（推荐）](#通用安装入口推荐)
- [模型配置](#模型配置)
  - [配置向导](#配置向导)
  - [多模型管理](#多模型管理)
  - [环境变量方式（快速）](#环境变量方式快速)
- [斜杠命令详解](#斜杠命令详解)
  - [核心命令](#核心命令)
  - [会话与上下文](#会话与上下文)
  - [记忆系统](#记忆系统)
  - [视觉能力](#视觉能力)
  - [系统与运维](#系统与运维)
  - [团队模式](#团队模式)
  - [飞书侧车](#飞书侧车)
- [架构概览](#架构概览)
- [可扩展性](#可扩展性)
- [配置与安全边界](#配置与安全边界)
- [常见问题 FAQ](#常见问题-faq)
- [研发与验证](#研发与验证)
- [许可证](#许可证)

---

## 快速开始

### 环境要求

- Python **3.10+**
- Git
- 可选：Docker（启用沙箱时需要）

### 一键安装（推荐）

```bash
# macOS / Linux
python3 -c "$(curl -fsSL https://raw.githubusercontent.com/yourname/scream-code/main/install.py)"

# 或先克隆仓库再安装
git clone <仓库地址>
cd Scream-Code
python3 install.py
```

安装完成后直接运行：

```bash
scream
```

常用入口：

| 命令 | 说明 |
|------|------|
| `scream` | 进入主交互 |
| `scream config` | 配置模型与密钥 |
| `scream help` | 查看 CLI 帮助 |

---

## 安装指南

### macOS / Linux

**方法 1：一键安装脚本（推荐）**

```bash
git clone <仓库地址>
cd Scream-Code
chmod +x install.sh
./install.sh
```

安装脚本会自动完成：

1. 检查 Python 3.10+ 环境
2. 创建虚拟环境 `.venv`（隔离项目依赖）
3. 安装所有 Python 依赖（`requirements.txt`）
4. 可编辑安装 `scream` 命令入口
5. 安装 Playwright Chromium（视觉能力）
6. 初始化用户目录 `~/.scream/`
7. **自动注册 PATH**（将 `scream` 加入系统命令）

> **权限说明**：脚本会尝试将 `scream` 注册到系统 PATH。若当前用户无写入 `/usr/local/bin` 权限，会自动降级到 `~/.local/bin` 并提示你手动 source 配置文件。

**方法 2：手动安装**

```bash
git clone <仓库地址>
cd Scream-Code
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
python3 -m playwright install chromium
mkdir -p ~/.scream/skills ~/.scream/screenshots
```

**方法 3：macOS Zsh 全局命令（仅注册 shell 别名）**

如果你已经手动安装好了依赖，只想快速注册全局命令：

```bash
python3 install_mac.py
source ~/.zshrc
```

---

### Windows

**方法 1：PowerShell 一键安装（推荐）**

```powershell
# 以管理员身份运行 PowerShell，然后执行：
git clone <仓库地址>
cd Scream-Code
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

> **权限说明**：安装脚本需要管理员权限来将 `scream` 注册到系统 PATH。若未以管理员运行，脚本会自动提示并尝试请求 UAC 提升。

**方法 2：手动安装**

```powershell
git clone <仓库地址>
cd Scream-Code
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
python -m playwright install chromium
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.scream\skills"
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.scream\screenshots"
```

---

### 通用安装入口（推荐）

我们提供了一个跨平台的 `install.py`，它会自动检测你的操作系统并调用对应的安装逻辑：

```bash
# 在所有平台（macOS / Linux / Windows）都可以使用
python3 install.py
```

`install.py` 的特性：

- 自动检测操作系统类型
- 自动检测是否需要管理员权限并提示
- 统一的输出格式和进度展示
- 安装失败时提供清晰的修复指引

---

## 模型配置

Scream Code 支持多模型配置，你可以同时维护多个 LLM 提供商的配置并在它们之间快速切换。

### 配置文件位置

- `~/.scream/llm_config.json`：模型列表与当前激活项
- `~/.scream/.env`：API 密钥等敏感配置（自动从环境变量读取）

### 配置向导

首次启动时会自动进入配置向导，你也可以随时运行：

```bash
scream config
```

配置向导交互流程：

1. **选择协议**：OpenAI 兼容 或 Anthropic 兼容
2. **填写连接信息**：
   - 配置别名（如"公司Claude"、"个人OpenAI"）
   - Base URL（如 `https://api.anthropic.com` 或你的中转地址）
   - 模型名称（推荐格式：`provider/model_id`，如 `anthropic/claude-3-5-sonnet-20240620`）
3. **输入 API Key**：向导会自动生成环境变量名并写入 `~/.scream/.env`

### 多模型管理

配置向导主菜单功能：

| 功能 | 说明 |
|------|------|
| 切换当前模型 | 在已配置的多个模型间切换 |
| 添加新模型 | 新增一个模型配置 |
| 修改已有模型 | 编辑现有配置的 URL、模型名、密钥 |
| 删除已有模型 | 移除不需要的配置（双重确认） |
| 切换系统操作权限 | 切换"沙箱模式"与"全局越狱" |
| 查看当前状态 | 显示当前激活模型与配置详情 |

### 支持的模型提供商

| 提供商 | 协议 | 典型 Base URL | 模型名示例 |
|--------|------|---------------|----------|
| OpenAI | `openai` | `https://api.openai.com/v1` | `gpt-4o` |
| Anthropic | `anthropic` | `https://api.anthropic.com` | `claude-3-5-sonnet-20240620` |
| DeepSeek | `openai` | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 中转/代理 | `openai` | 你的中转地址 | 任意 |

> **自动推断**：模型名若带 `claude-` 前缀会自动识别为 Anthropic 协议，带 `gpt-`/`o1`/`o3`/`deepseek-` 前缀会自动识别为 OpenAI 协议。

### 环境变量方式（快速）

如果你不想用配置向导，可以直接设置环境变量：

```bash
# 写入 ~/.scream/.env
echo "OPENAI_API_KEY=sk-xxx" >> ~/.scream/.env
echo "BASE_URL=https://api.openai.com/v1" >> ~/.scream/.env
echo "MODEL=gpt-4o" >> ~/.scream/.env
```

或一次性启动：

```bash
OPENAI_API_KEY=sk-xxx BASE_URL=https://api.openai.com/v1 MODEL=gpt-4o scream
```

### 系统操作权限

配置向导中可以切换"沙箱模式"与"全局越狱"：

- **沙箱模式（默认）**：文件读写与 bash 执行限制在当前工作区，更安全
- **全局越狱**：工具可访问任意路径，bash 在用户主目录下执行，功能更强大但需谨慎

---

## 斜杠命令详解

在 TUI 交互中，输入 `/` 可触发斜杠命令补全。按分类说明如下：

### 核心命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `/help` | 显示所有可用命令（别名 `/?`） | `/help` |
| `/clear` | 清屏（不清空会话历史） | `/clear` |
| `/exit` | 退出 Scream Code | `/exit` |
| `/quit` | 同 `/exit` | `/quit` |

### 会话与上下文

| 命令 | 说明 | 示例 |
|------|------|------|
| `/new` | 硬重置会话（新建 session，历史保留在磁盘） | `/new` |
| `/flush` | 清空当前对话上下文并重置 token 累计 | `/flush` |
| `/stop` | 中断当前正在进行的生成/工具链 | `/stop` |
| `/sessions` | 查看本地保存的会话列表 | `/sessions` |
| `/load <id>` | 加载指定会话继续对话 | `/load abc123` |
| `/summary` | 生成当前项目与会话摘要，可选择写入长期记忆 | `/summary` |
| `/memo` | 提炼当前对话核心内容并保存到长期记忆 | `/memo 团队偏好：默认先写测试` |

> **会话持久化**：所有会话自动落盘到本地 SQLite，可随时 `/load` 恢复。

### 记忆系统

| 命令 | 说明 | 示例 |
|------|------|------|
| `/memory list` | 列出所有长期记忆条目 | `/memory list` |
| `/memory set <key> <value>` | 设置一条长期记忆 | `/memory set code_style 统一ruff` |
| `/memory drop <key>` | 删除一条长期记忆 | `/memory drop code_style` |

> **记忆注入**：长期记忆内容会自动注入系统提示，形成"项目级个性化行为"。例如设置了 `code_style` 记忆后，AI 在写代码时会自动遵循该风格。

### 视觉能力

| 命令 | 说明 | 示例 |
|------|------|------|
| `/look <url> [说明]` | 获取网页视觉快照并分析 | `/look https://example.com 检查可访问性` |

> **依赖**：`/look` 需要 Playwright Chromium 已安装。若未安装，会提示你运行 `python3 -m playwright install chromium`。

### 系统与运维

| 命令 | 说明 | 示例 |
|------|------|------|
| `/sandbox on\|off\|status` | Docker 沙箱开关/状态 | `/sandbox status` |
| `/diff` | Git 工作区变更摘要 | `/diff` |
| `/mcp` | MCP（Model Context Protocol）管理 | `/mcp status` |
| `/audit` | 项目对齐度审查 | `/audit` |
| `/report` | 运行环境体检报告 | `/report` |
| `/doctor` | 运行环境与依赖诊断 | `/doctor` |
| `/status` | 当前运行状态总览 | `/status` |
| `/cost` | Token 消耗与费用估算 | `/cost` |
| `/config` | 当前模型配置 JSON 展示 | `/config` |
| `/skills` | 已挂载技能列表 | `/skills` |
| `/subsystems` | 顶层子系统视图 | `/subsystems` |
| `/graph` | Bootstrap + Command 依赖图谱 | `/graph` |

**`/mcp` 子命令**：

| 子命令 | 说明 |
|--------|------|
| `/mcp status` | 查看 MCP 服务器状态 |
| `/mcp restart` | 重启 MCP 服务器 |
| `/mcp tools` | 列出 MCP 可用工具 |
| `/mcp browser` | 切换浏览器模式 |

### 团队模式

| 命令 | 说明 | 示例 |
|------|------|------|
| `/team` | 切换多 Agent 团队模式（开/关） | `/team` |
| `$team <prompt>` | 单条消息走团队模式（不切换全局设置） | `$team 先评审再改` |

> **团队模式工作流**：Analyst（分析）→ Planner（规划）→ Coder（编码）→ Reviewer（审查），单条消息触发多 Agent 协作。

### 飞书侧车

| 命令 | 说明 | 示例 |
|------|------|------|
| `/feishu config <AppID> <AppSecret>` | 配置飞书凭据 | `/feishu config cli_xxx xxx` |
| `/feishu start` | 启动飞书侧车 | `/feishu start` |
| `/feishu stop` | 停止飞书侧车 | `/feishu stop` |
| `/feishu status` | 查看侧车状态 | `/feishu status` |
| `/feishu delete` | 清理飞书会话与缓存 | `/feishu delete` |
| `/feishu log` | 查看侧车日志 | `/feishu log` |

> **双通道架构**：飞书会话与主会话隔离（`feishu_` 前缀），附件通过 `[FEISHU_FILE:路径]` 标签转发。

---

## 架构概览

Scream Code 采用三层架构设计：

```
┌─────────────────────────────────────────────────────┐
│                    显示层 (Display)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │  TUI REPL   │  │  飞书侧车   │  │  CLI 入口   │  │
│  │ replLauncher│  │feishu_ws_bot│  │   main.py   │  │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘  │
└─────────┼────────────────┼──────────────────────────┘
          │                │
┌─────────▼────────────────▼──────────────────────────┐
│                 适配/扩展层 (Adapter)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │SkillsRegistry│  │ToolsRegistry│  │  MCP管理器  │  │
│  │  斜杠技能    │  │  LLM 工具   │  │ mcp_manager │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────┬────────────────┬──────────────────────────┘
          │                │
┌─────────▼────────────────▼──────────────────────────┐
│                  镜像内核 (Mirror Kernel)              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │QueryEngine  │  │  LLM 客户端  │  │  会话存储   │  │
│  │  会话编排    │  │ llm_client  │  │session_store│  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────┘
```

核心模块说明：

| 文件 | 职责 |
|------|------|
| `src/main.py` | CLI 入口与命令路由 |
| `src/replLauncher.py` | TUI 主循环、REPL、审批机制 |
| `src/query_engine.py` | 会话管理、模型交互、工具编排 |
| `src/llm_client.py` | LLM API 调用与流式处理 |
| `src/llm_providers.py` | 多提供商适配（OpenAI/Anthropic/DeepSeek） |
| `src/skills_registry.py` | 斜杠技能注册与分发 |
| `src/tools_registry.py` | LLM 工具注册与执行治理 |
| `src/session_store.py` | 会话持久化、索引与隔离 |
| `src/memory_store.py` | SQLite 长期记忆存储 |
| `src/mcp_manager.py` | MCP 服务器生命周期管理 |
| `bots/feishu_ws_bot.py` | 飞书 WebSocket 侧车 |

---

## 可扩展性

### 自定义斜杠技能

将技能文件放入 `~/.scream/skills/`，重启后自动加载（覆盖同名内置技能）。

技能文件模板：

```python
from src.skills_registry import skill

@skill("/mycommand", "我的自定义命令", category="Custom")
def handle_mycommand(args: str, context: dict):
    """args 为用户输入的命令参数，context 包含当前会话信息"""
    return {"type": "text", "content": f"收到参数: {args}"}
```

### 自定义 LLM 工具

将工具模块放到项目根 `skills/*.py`，导出 `TOOL_SCHEMA` 和 `execute(**kwargs)`：

```python
TOOL_SCHEMA = {
    "name": "my_tool",
    "description": "工具描述",
    "parameters": {
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "输入参数"}
        },
        "required": ["input"]
    }
}

def execute(input: str) -> str:
    return f"处理结果: {input}"
```

工具会被 `ToolsRegistry` 自动发现并注册。

---

## 配置与安全边界

### 高危操作审批机制

Scream Code 默认启用 **Human-in-the-loop (HITL)** 审批：当 Agent 尝试执行写文件、打补丁、运行脚本等高危工具时，终端会弹出审批卡片，要求你手动确认。

审批选项：

- `y` / `yes`：批准本次操作
- `n` / `no`：拒绝本次操作
- `a` / `all`：批准本次及后续所有同类操作

### 自动放行白名单

在**项目根目录**创建 `.claw.json` 可配置自动放行：

```json
{
  "auto_approve_tools": ["write_local_file", "patch"]
}
```

配置后，命中的工具将跳过人工审批；未在白名单中的高危工具仍会继续拦截。

### 仓库忽略策略

仓库默认忽略敏感/运行态目录，避免误提交密钥和缓存：

```gitignore
.env
/.scream_cache/
*.db
```

### 飞书侧车缓存

- 入站：`.scream_cache/feishu_inbox/`
- 出站：`.scream_cache/feishu_outbox/`
- PID：`.scream_cache/feishu_sidecar.pid`

---

## 常见问题 FAQ

### Q1: 安装时提示权限不足怎么办？

**macOS/Linux**：脚本会自动降级到用户级 PATH（`~/.local/bin`）。你也可以手动提权：

```bash
sudo ./install.sh
```

**Windows**：请以管理员身份运行 PowerShell，或脚本会自动提示 UAC 提升。

### Q2: 安装后提示 "scream: command not found"？

安装脚本已尝试注册 PATH，但可能需要重启终端或手动 source：

```bash
# macOS/Linux (bash/zsh)
source ~/.bashrc  # 或 source ~/.zshrc

# 如果仍未生效，检查 ~/.local/bin 是否在 PATH 中
export PATH="$HOME/.local/bin:$PATH"
```

Windows 请重启 PowerShell 或命令提示符。

### Q3: 如何配置多个模型并快速切换？

```bash
scream config
# 选择"添加新模型"添加多个配置
# 选择"切换当前模型"在不同模型间切换
```

### Q4: API Key 存储安全吗？

API Key 存储在 `~/.scream/.env` 中（用户主目录，非仓库内），不会被 Git 追踪。项目根目录的 `.env` 仅作为兼容性回退。

### Q5: `/look` 命令报错怎么办？

通常是因为 Playwright Chromium 未安装：

```bash
# macOS/Linux
python3 -m playwright install chromium

# Windows
python -m playwright install chromium
```

### Q6: 如何完全卸载？

```bash
# 删除用户配置
rm -rf ~/.scream

# 删除 PATH 注册（如果安装时写入了 /usr/local/bin）
sudo rm -f /usr/local/bin/scream /usr/local/bin/scream-config

# 删除仓库
rm -rf /path/to/Scream-Code
```

### Q7: 支持哪些模型？

任何兼容 OpenAI 或 Anthropic API 格式的模型都可以接入，包括：

- OpenAI GPT-4/GPT-4o/GPT-3.5
- Anthropic Claude 3/3.5/4 系列
- DeepSeek V3/R1
- 各类 OpenAI 兼容中转服务

### Q8: 团队模式有什么用？

团队模式将单条用户消息分发给多个专业化 Agent 协作处理：

1. **Analyst**：分析问题本质
2. **Planner**：制定执行计划
3. **Coder**：执行具体编码
4. **Reviewer**：审查结果质量

适合复杂任务，如"重构整个模块"、"设计新架构"等。

### Q9: 如何自定义系统提示？

通过长期记忆系统：

```
/memory set system_persona 你是一位资深Python工程师，偏好类型注解和函数式编程
```

设置后，该记忆会自动注入每条对话的系统提示中。

### Q10: 审批弹窗卡住了怎么办？

如果审批提示未正常弹出或卡住：

1. 尝试按 `Enter` 键刷新
2. 使用 `/stop` 中断当前操作
3. 如果频繁卡住，考虑在 `.claw.json` 中添加常用工具到白名单

---

## 研发与验证

```bash
# 运行测试
python3 -m pytest tests/ -q

# 语法检查
python3 -m py_compile src/*.py
```

---

## 许可证

MIT License。详见 `LICENSE`。

---

**Scream Code 核心理念**：让 AI 真正成为你本地生产系统的一部分，而不是浏览器里的临时聊天窗口。
