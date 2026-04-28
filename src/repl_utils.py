from __future__ import annotations

import io
import itertools
import json
import os
import sys
import time
from contextlib import contextmanager
from typing import Any

def _tui_set_stream_label(label: str) -> None:
    """更新 Python TUI 底部固定状态块（无 tui_app 时静默）。"""
    try:
        from .tui_app import set_tui_stream_label

        set_tui_stream_label(label)
    except Exception:
        pass


def _tui_thinking_status_labels() -> tuple[str, str]:
    """
    返回 ``(短标签, 带省略号标签)``。
    启用模型深度思考时（见 ``llm_settings.is_model_deep_thinking_enabled``）使用「深度思考中…」。
    """
    from .llm_settings import is_model_deep_thinking_enabled

    if is_model_deep_thinking_enabled():
        return ('深度思考中', '深度思考中...')
    return ('思考中', '思考中...')


@contextmanager
def _safe_prompt_toolkit_exit_patch():
    """仅在流式并发回合期间屏蔽 prompt_toolkit 双重退出竞态。"""
    from prompt_toolkit.application.application import Application

    original_exit = Application.exit

    def _safe_app_exit(self, result=None, exception=None, style=''):
        if self.future is not None and self.future.done():
            return
        try:
            original_exit(self, result=result, exception=exception, style=style)
        except Exception as e:
            if 'Return value already set' in str(e):
                return
            raise

    Application.exit = _safe_app_exit
    try:
        yield
    finally:
        Application.exit = original_exit

# 引入活泼的 ASCII / 全角颜文字作为思考动画（与 _poll 内 Status.update 联动）
KAWAII_FRAMES = [
    '(>_<)',
    '(^_^;)',
    '(＠_＠;)',
    '(T_T)',
    '(-_-;)',
    '(~_~;)',
    '(*_*)',
    '(°_o)',
    '(•_•)',
    '(@_@)',
    '(╯°□°）╯',
]
_kawaii_cycle = itertools.cycle(KAWAII_FRAMES)

# Slant 风格 ASCII（用户指定，勿改字符结构）
_SLANT_LOGO_LINES = (
    '   _____                                 ____      __     ',
    '  / ___/_____________  ____ _____ ___   / ____/___/ /__   ',
    '  \\__ \\/ ___/ ___/ _ \\/ __ `/ __ `__ \\ / /   / __  / _ \\  ',
    ' ___/ / /__/ /  /  __/ /_/ / / / / / // /___/ /_/ /  __/  ',
    '/____/\\___/_/   \\___/\\__,_/_/ /_/ /_/ \\____/\\__,_/\\___/   ',
)


def build_repl_banner() -> str:
    return (
        '当前为「仅说明」模式（例如使用了 `repl --no-llm`）。'
        '要进入可对话的交互循环并调用大模型，请执行不带 `--no-llm` 的 `python3 -m src.main repl`'
        '（密钥见 llm_config.json / .env）。也可使用 `summary` 或 `config`。'
    )


def _logo_plain() -> str:
    return '\n'.join(_SLANT_LOGO_LINES)


# 记忆水位（仅 REPL 展示层；不截断请求、不改写历史）
REPL_MEMORY_WARN_TOTAL_TOKENS = 2_000_000
REPL_MEMORY_WARN_USER_TURNS = 200
REPL_MEMORY_WARN_REPEAT_TOKEN_DELTA = 200_000
REPL_MEMORY_WARN_REPEAT_TURN_DELTA = 40
# 兼容旧名：默认 token 阈值
TOKEN_WARNING_THRESHOLD = REPL_MEMORY_WARN_TOTAL_TOKENS
# session_id -> (上次预警时的累计 tokens, 上次预警时的用户轮次数)
_REPL_MEMORY_WARN_LAST: dict[str, tuple[int, int]] = {}


_CONTEXT_FILE_TOOL_NAMES = frozenset(
    {
        'read_local_file',
        'write_local_file',
        'read_file',
        'write_file',
        'cat',
        'patch',
        'apply_patch',
        'open_file',
    }
)

# 高危工具：命中后需要用户审批（Human-in-the-loop）。
_SENSITIVE_TOOLS = frozenset(
    {
        'execute_mac_bash',
        'run_bash_command',
        'execute_shell',
        'write_local_file',
        'write_file',
        'patch',
        'apply_patch',
    }
)


def _ensure_active_context_files(engine: Any) -> set[str]:
    cur = getattr(engine, 'active_context_files', None)
    if isinstance(cur, set):
        return cur
    s: set[str] = set()
    try:
        setattr(engine, 'active_context_files', s)
    except Exception:
        pass
    return s


def _normalize_context_path(raw: str) -> str:
    t = (raw or '').strip()
    if not t:
        return ''
    p = t.replace('\\', '/')
    if p.startswith('~'):
        p = os.path.expanduser(p)
    if os.path.isabs(p):
        try:
            rel = os.path.relpath(p, os.getcwd())
            if not rel.startswith('..'):
                p = rel
        except Exception:
            pass
    return p.replace('\\', '/')


def _extract_context_paths_from_args(tool_name: str, raw_args: str) -> list[str]:
    if tool_name not in _CONTEXT_FILE_TOOL_NAMES:
        return []
    out: list[str] = []
    try:
        args = json.loads(raw_args or '{}')
    except json.JSONDecodeError:
        args = {}
    if not isinstance(args, dict):
        return out
    for key in ('file_path', 'path', 'target_file', 'source_file'):
        v = args.get(key)
        if isinstance(v, str):
            n = _normalize_context_path(v)
            if n:
                out.append(n)
    paths = args.get('paths')
    if isinstance(paths, list):
        for p in paths:
            if isinstance(p, str):
                n = _normalize_context_path(p)
                if n:
                    out.append(n)
    # 去重并保持顺序
    seen: set[str] = set()
    uniq: list[str] = []
    for p in out:
        if p in seen:
            continue
        seen.add(p)
        uniq.append(p)
    return uniq


def _track_active_context_files(engine: Any, tool_name: str, raw_args: str) -> None:
    files = _ensure_active_context_files(engine)
    for p in _extract_context_paths_from_args(tool_name, raw_args):
        files.add(p)


_DIFFABLE_WRITE_TOOL_NAMES = frozenset({'write_local_file', 'write_file'})


def _pick_first_file_path_from_args(raw_args: str) -> str:
    try:
        args = json.loads(raw_args or '{}')
    except json.JSONDecodeError:
        return ''
    if not isinstance(args, dict):
        return ''
    for key in ('file_path', 'path', 'target_file'):
        v = args.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ''


def _extract_new_content_from_args(raw_args: str) -> str:
    try:
        args = json.loads(raw_args or '{}')
    except json.JSONDecodeError:
        return ''
    if not isinstance(args, dict):
        return ''
    v = args.get('content')
    return v if isinstance(v, str) else ''


def _safe_json_object(raw_args: str) -> dict[str, Any]:
    try:
        obj = json.loads(raw_args or '{}')
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _read_old_file_content_for_diff(raw_path: str) -> tuple[str, str]:
    shown = _normalize_context_path(raw_path)
    p = raw_path
    if p.startswith('~'):
        p = os.path.expanduser(p)
    abs_path = p if os.path.isabs(p) else os.path.join(os.getcwd(), p)
    try:
        from pathlib import Path

        old = Path(abs_path).read_text(encoding='utf-8', errors='replace')
    except OSError:
        old = ''
    return shown or p, old


def _ensure_stdio_utf8() -> None:
    """
    将标准流尽量设为 UTF-8，避免区域设置为 C/latin-1 时中文在 prompt_toolkit 中显示为乱码。
    """
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconf = getattr(stream, 'reconfigure', None)
        if not callable(reconf):
            continue
        try:
            reconf(encoding='utf-8', errors='replace')
        except (OSError, ValueError, TypeError, io.UnsupportedOperation):
            pass


def _repl_terminal_soft_reset(console: Any | None) -> None:
    """
    Rich（Live / Status）与 prompt_toolkit 交替使用后，部分终端会残留光标或模式状态，
    导致下一行输入错位或 UTF-8 字符显示异常；在每回合结束后做一次轻量恢复。
    """
    if console is not None:
        try:
            show = getattr(console, 'show_cursor', None)
            if callable(show):
                show(True)
        except Exception:
            pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except Exception:
            pass


def clear_all_repl_token_warnings() -> None:
    """供 ``/new`` 等硬重置：清空记忆水位预警的会话缓存（展示层）。"""
    _REPL_MEMORY_WARN_LAST.clear()


def _try_persist_repl_session(engine: Any) -> None:
    """每回合结束后写入 ``.port_sessions/``，便于关闭终端后自动续聊。"""
    try:
        engine.persist_session()
    except OSError:
        pass


def repl_stdin_flush_pending_if_tty() -> None:
    """
    丢弃内核里已为 stdin 排队、但本进程尚未读取的字节。

    在**成功从磁盘恢复会话之后**、首次 ``prompt``/``input`` 之前调用，可避免终端或宿主
    误注入的上行（例如残留换行）被当成用户主动提交的第一句话，从而意外触发 LLM 回合。
    非 TTY（管道/重定向）下不操作。
    """
    if not sys.stdin.isatty():
        return
    try:
        import termios
    except ImportError:
        return
    try:
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except (OSError, AttributeError):
        pass


def _repl_engine_autoresume(console: Any | None, *, use_rich: bool) -> Any:
    """
    若 ``.port_sessions/`` 下存在最近修改的会话 JSON，则 ``from_saved_session`` 恢复；否则空会话。
    不改变 ``session_store`` 的读写格式，仅组合现有 API。
    """
    from .query_engine import QueryEnginePort
    from .session_store import most_recent_saved_session_id

    sid = most_recent_saved_session_id()
    if not sid:
        return QueryEnginePort.from_workspace()
    try:
        eng = QueryEnginePort.from_saved_session(sid)
    except (OSError, FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return QueryEnginePort.from_workspace()
    repl_stdin_flush_pending_if_tty()
    if use_rich and console is not None:
        console.print(
            f'[dim]已自动恢复上次会话记忆 (ID: {sid})，如需开启全新对话请输出 /new[/dim]'
        )
    else:
        print(
            f'已自动恢复上次会话记忆 (ID: {sid})；全新对话请输入 /new',
            flush=True,
        )
    return eng


def _safe_close_generator(gen: Any) -> None:
    """关闭事件生成器时吞掉各类异常，避免二次堆栈污染终端。"""
    if gen is None:
        return
    try:
        gen.close()
    except BaseException:
        pass


def _token_warning_threshold_for_engine(engine: Any) -> int:
    """优先读取 ``engine.config.token_warning_threshold``（若为正整数），否则默认 ``REPL_MEMORY_WARN_TOTAL_TOKENS``。"""
    cfg = getattr(engine, 'config', None)
    if cfg is None:
        return REPL_MEMORY_WARN_TOTAL_TOKENS
    raw = getattr(cfg, 'token_warning_threshold', None)
    if isinstance(raw, int) and raw > 0:
        return raw
    return REPL_MEMORY_WARN_TOTAL_TOKENS


def _maybe_print_repl_memory_load_warning(
    console: Any | None, engine: Any, *, use_rich: bool
) -> None:
    """
    记忆水位预警：仅 ``console.print``，不截断、不改写 engine。
    在流式回合正常结束后调用。首次在「累计 tokens ≥ 阈值」或「用户轮次 ≥ 阈值」时提示；
    之后仅当 tokens 再增 ``REPL_MEMORY_WARN_REPEAT_TOKEN_DELTA`` 或轮次再增
    ``REPL_MEMORY_WARN_REPEAT_TURN_DELTA`` 时重复提示。token 与轮次均回落至阈值以下时重置。
    """
    try:
        u = getattr(engine, 'total_usage', None)
        if u is None:
            return
        inp = int(getattr(u, 'input_tokens', 0))
        outp = int(getattr(u, 'output_tokens', 0))
        current_tokens = inp + outp
    except (TypeError, ValueError):
        return

    msgs = getattr(engine, 'mutable_messages', None) or []
    try:
        user_turns = len(msgs)
    except TypeError:
        user_turns = 0

    token_th = _token_warning_threshold_for_engine(engine)
    turn_th = REPL_MEMORY_WARN_USER_TURNS
    sid = str(getattr(engine, 'session_id', '') or '') or str(id(engine))

    below_tokens = current_tokens < token_th
    below_turns = user_turns < turn_th
    if below_tokens and below_turns:
        _REPL_MEMORY_WARN_LAST.pop(sid, None)
        return

    prev = _REPL_MEMORY_WARN_LAST.get(sid)
    if prev is None:
        should_warn = True
    else:
        last_tok, last_turn = prev
        should_warn = (
            current_tokens - last_tok >= REPL_MEMORY_WARN_REPEAT_TOKEN_DELTA
            or user_turns - last_turn >= REPL_MEMORY_WARN_REPEAT_TURN_DELTA
        )

    if not should_warn:
        return

    _REPL_MEMORY_WARN_LAST[sid] = (current_tokens, user_turns)

    from .repl_ui_render import build_token_warning_panel, format_token_warning_plain

    if use_rich and console is not None:
        console.print()
        console.print(build_token_warning_panel(current_tokens, token_th))
        return

    print(format_token_warning_plain(current_tokens, token_th), end='', flush=True)


def _print_graceful_interrupt(console: Any | None, *, use_rich: bool) -> None:
    """
    Ctrl+C 后的统一提示：保留已输出内容，REPL 不退出，会话对象不丢弃。
    """
    primary = '⏸ 已手动中断'
    hint = (
        '当前已输出内容已保留。可直接输入下一句继续；本轮若未跑完则不会写入完整对话历史。'
        '输入 exit 退出。'
    )
    if use_rich and console is not None:
        console.print(f'[bold yellow]{primary}[/bold yellow]')
        console.print(f'[dim]{hint}[/dim]')
        return
    print(f'\n{primary}。{hint}', flush=True)


def print_project_memory_loaded_notice() -> None:
    """Logo 之后调用：若工作区根下存在可用的项目记忆文件，打印一行绿色提示。"""
    from .project_memory import project_memory_workspace_root, read_first_available_project_memory

    name, _ = read_first_available_project_memory(project_memory_workspace_root())
    if not name:
        return
    msg = f'[+] 已加载项目记忆文档: {name}'
    try:
        from rich.console import Console

        Console().print(f'[bold green]{msg}[/bold green]')
    except ImportError:
        if sys.stdout.isatty():
            print(f'\033[1;32m{msg}\033[0m', flush=True)
        else:
            print(msg, flush=True)


def print_startup_banner(*, ensure_config: bool = True, compact: bool = False) -> None:
    if ensure_config:
        try:
            from . import model_manager

            model_manager.ensure_default_config_file()
        except OSError:
            pass

    try:
        from rich.align import Align
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
    except ImportError:
        print(_logo_plain())
        print()
        return

    console = Console()
    if compact:
        compact_text = Text.from_markup(
            '[bold cyan]SCREAM CODE[/bold cyan]\n'
            '[dim]Model Config Center[/dim]'
        )
        panel = Panel(
            Align.center(compact_text),
            border_style='bold cyan',
            padding=(0, 1),
            expand=True,
        )
    else:
        logo_lines = list(_SLANT_LOGO_LINES)
        max_logo_width = max(len(line) for line in logo_lines)
        # 预留 Panel 左右边框与 padding，避免窄终端时被硬截断。
        available = max(20, console.width - 6)
        if available >= max_logo_width:
            art = Text(_logo_plain(), style='bold cyan')
            panel = Panel.fit(
                Align.center(art),
                border_style='bold cyan',
                padding=(1, 2),
            )
        else:
            compact_text = Text.from_markup(
                '[bold cyan]SCREAM CODE[/bold cyan]\n'
                '[dim]Neural CLI[/dim]'
            )
            panel = Panel(
                Align.center(compact_text),
                border_style='bold cyan',
                padding=(0, 1),
                expand=True,
            )
    console.print(panel)
    console.print()


def print_repl_llm_driver_banner(*, console: Any | None) -> None:
    """REPL + --llm：Logo 之后展示当前激活模型或黄色未配置警告。"""
    try:
        from . import model_manager
    except ImportError:
        return

    model_manager.ensure_default_config_file()
    raw = model_manager.read_persisted_config_raw()
    profile = model_manager.get_active_profile(raw) if raw else None

    if console is None:
        if profile is None:
            print('⚠️ 当前无激活的大模型，请配置后再使用！')
        else:
            proto = profile.api_protocol if profile.api_protocol in ('openai', 'anthropic') else 'openai'
            print(
                f'协议: {proto} | 模型: {profile.model_name} | 状态: 已就绪'
            )
        print()
        return

    from rich.markup import escape
    from rich.panel import Panel
    from rich.text import Text

    if profile is None:
        body = Text.from_markup(
            '[bold yellow]⚠️ 当前无激活的大模型，请配置后再使用！[/bold yellow]'
        )
        console.print(Panel(body, border_style='yellow', expand=True, padding=(0, 2)))
    else:
        proto = profile.api_protocol if profile.api_protocol in ('openai', 'anthropic') else 'openai'
        inner = (
            f'[bold green]协议: {escape(proto)} | '
            f'模型: {escape(profile.model_name)} | '
            f'状态: 已就绪[/bold green]'
        )
        body = Text.from_markup(inner)
        console.print(Panel(body, border_style='bold green', expand=True, padding=(0, 2)))
    console.print()


def _print_assistant_output(console: object, text: str) -> None:
    from .repl_ui_render import final_assistant_markdown_panel

    stripped = text.strip()
    if not stripped:
        return
    # Live（transient）清场后，仅此一份完整 Panel 写入 scrollback
    console.print(final_assistant_markdown_panel(stripped))
    console.print()


def _print_assistant_error(console: object, message: str) -> None:
    from rich.text import Text

    from .repl_ui_render import assistant_panel

    console.print(assistant_panel(Text(message, style='bold red')))
    console.print()


def _dedupe_assistant_scrollback_echoes(text: str) -> str:
    """
    折叠展示层偶发的「同段自我介绍 / 同句」重影：相邻完全相同的段落或文本行只保留一份。
    不影响有意重复的结构化列表（仅合并**连续**相同块）。
    """
    raw = (text or '').strip()
    if not raw:
        return raw
    paras = [p.strip() for p in raw.split('\n\n') if p.strip()]
    merged_p: list[str] = []
    for p in paras:
        if merged_p and p == merged_p[-1]:
            continue
        merged_p.append(p)
    t2 = '\n\n'.join(merged_p)
    lines = t2.splitlines()
    out_ln: list[str] = []
    for ln in lines:
        s = ln.strip()
        if s and out_ln and s == out_ln[-1].strip():
            continue
        out_ln.append(ln)
    return '\n'.join(out_ln).strip()


__all__ = [name for name in globals() if not name.startswith("__")]
