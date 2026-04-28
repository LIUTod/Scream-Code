from __future__ import annotations

import copy
import json
import logging
import os
import traceback
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from . import agent_cancel
from .constants.messages import MSG_TOOL_EXCEPTION
from .llm_providers import *  # noqa: F401,F403
from .llm_settings import LlmConnectionSettings
from .message_prune import prune_historical_messages

if TYPE_CHECKING:  # pragma: no cover
    from .mcp_manager import MCPClient

def chat_completion_stream(
    messages: list[dict[str, Any]],
    settings: LlmConnectionSettings,
    *,
    model: str | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> Iterator[StreamPart]:
    """按模型前缀路由（provider/model_id）严格分发到对应客户端。"""
    # 内存修剪：不修改调用方传入的 messages（深拷贝在 prune 内完成）
    api_messages = prune_historical_messages(messages)
    raw_model = (model or settings.model).strip() or settings.model
    route = parse_model_route(
        raw_model,
        default_provider=settings.default_provider or settings.api_protocol or 'openai',
    )
    _raise_if_missing_provider_key(settings, provider=route.provider)
    try:
        if route.provider == 'anthropic':
            yield from _chat_completion_stream_anthropic(
                api_messages, settings, use_model=route.model_id, tools=tools
            )
        elif route.provider in ('openai', 'deepseek'):
            yield from _chat_completion_stream_openai(
                api_messages, settings, use_model=route.model_id, tools=tools
            )
        else:
            raise LlmClientError(f'[LLM] 不支持的 provider 路由: {route.provider}')
    except Exception as exc:
        mapped = _map_llm_auth_exception(exc)
        if mapped is not None:
            raise mapped from exc
        if _is_timeout_or_network_exception(exc):
            raise LlmClientError(_LLM_TRANSPORT_FUSE_MSG) from exc
        raise


def iter_agent_executor_events(
    messages: list[dict[str, Any]],
    settings: LlmConnectionSettings,
    *,
    model: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    mcp_client: 'MCPClient | None' = None,
) -> Iterator[dict[str, Any]]:
    """
    **LLM Provider 侧唯一的多轮工具闭环**（本仓库对 claw-code 链路的 Python 镜像实现）。

    职责边界（不可下沉到 REPL / 通道）：

    - 按 ``api_protocol`` 流式调用 OpenAI 或 Anthropic；
    - 解析 ``tool_calls``，经 **ToolsRegistry**（与 ``tool-pool`` 展示的运行时工具面同源）执行并写回 ``messages``；
    - 向外产出 ``text_delta`` / ``tool_delta`` / ``api_tool_op`` / ``llm_error``，以及终结事件 ``executor_complete``。

    不负责：会话 transcript、路由摘要、Rich 渲染。调用方须传入已构造好的 ``messages``（含 system/user）。
    """
    from .tools_registry import get_tools_registry

    reg = get_tools_registry()
    use_tools = tools if tools is not None else get_openai_agent_tools()
    use_model = (model or settings.model).strip() or settings.model
    msgs = messages
    in_tok = 0
    out_tok = 0
    text_slices: list[str] = []
    local_tool_names = {
        str(row.get('name') or '').strip()
        for row in reg.list_tool_rows()
        if isinstance(row, dict)
    }

    cap = agent_tool_iteration_cap()
    n_iter = 0
    while cap is None or n_iter < cap:
        n_iter += 1
        if agent_cancel.agent_cancel_requested():
            yield {
                'type': 'executor_complete',
                'assistant_text': '用户已中断当前任务。',
                'input_tokens': in_tok,
                'output_tokens': out_tok,
                'conversation_messages': copy.deepcopy(msgs),
                'stop_reason': 'user_interrupt',
            }
            return

        acc = ToolCallAccumulator()
        round_buf: list[str] = []
        finish_reason: str | None = None
        round_in = 0
        round_out = 0
        stream_cancelled = False
        try:
            for part in chat_completion_stream(
                msgs, settings, model=use_model, tools=use_tools
            ):
                if agent_cancel.agent_cancel_requested():
                    stream_cancelled = True
                    break
                if part.text_delta:
                    round_buf.append(part.text_delta)
                    yield {'type': 'text_delta', 'text': part.text_delta}
                if part.tool_arguments_fragment:
                    yield {'type': 'tool_delta', 'fragment': part.tool_arguments_fragment}
                acc.consume(part)
                if part.finish_reason:
                    finish_reason = part.finish_reason
                if part.prompt_tokens is not None:
                    round_in = part.prompt_tokens
                if part.completion_tokens is not None:
                    round_out = part.completion_tokens
        except LlmClientError as exc:
            msg = str(exc)
            if msg == _LLM_TRANSPORT_FUSE_MSG:
                yield {'type': 'llm_error', 'output': msg}
            else:
                yield {'type': 'llm_error', 'output': f'[LLM] {msg}'}
            return
        except Exception as exc:  # pragma: no cover - 网络/供应商错误
            if _is_timeout_or_network_exception(exc):
                yield {'type': 'llm_error', 'output': _LLM_TRANSPORT_FUSE_MSG}
                return
            yield {'type': 'llm_error', 'output': f'[LLM] 请求异常: {exc}'}
            return

        in_tok += round_in
        out_tok += round_out

        if stream_cancelled:
            partial = ''.join(round_buf).strip()
            tail = (
                partial + '\n\n用户已中断当前任务。'
                if partial
                else '用户已中断当前任务。'
            )
            yield {
                'type': 'executor_complete',
                'assistant_text': tail,
                'input_tokens': in_tok,
                'output_tokens': out_tok,
                'conversation_messages': copy.deepcopy(msgs),
                'stop_reason': 'user_interrupt',
            }
            return

        assistant_round = ''.join(round_buf).strip()

        if finish_reason == 'tool_calls' and acc.has_tool_calls():
            if assistant_round:
                text_slices.append(assistant_round)
            tool_calls = acc.as_openai_tool_calls()
            assistant_msg: dict[str, Any] = {
                'role': 'assistant',
                'tool_calls': tool_calls,
            }
            if assistant_round:
                assistant_msg['content'] = assistant_round
            msgs.append(assistant_msg)
            interrupt_from_here: int | None = None
            for idx, tc in enumerate(tool_calls):
                fn = tc['function']['name']
                raw_args = tc['function']['arguments']
                parsed_args = _parse_tool_arguments(raw_args)
                progress_hint: str | None = None
                if mcp_client is not None and getattr(mcp_client, 'is_running', False) and fn not in local_tool_names:
                    progress_hint = _format_tool_call_progress_hint(fn, parsed_args)
                ev_tool: dict[str, Any] = {
                    'type': 'api_tool_op',
                    'tool_name': fn,
                    'arguments': raw_args,
                }
                if progress_hint is not None:
                    ev_tool['progress_hint'] = progress_hint
                yield ev_tool
                if agent_cancel.agent_cancel_requested():
                    interrupt_from_here = idx
                    break
                try:
                    if fn in local_tool_names:
                        result = reg.execute_tool(fn, raw_args)
                    elif mcp_client is not None and getattr(mcp_client, 'is_running', False):
                        from .mcp_manager import MCPClientError

                        args = parsed_args
                        try:
                            mcp_resp = mcp_client.call_tool(fn, args)
                            mcp_result = mcp_resp.get('result')
                            if isinstance(mcp_result, (dict, list)):
                                result = json.dumps(mcp_result, ensure_ascii=False)
                            elif mcp_result is None:
                                result = ''
                            else:
                                result = str(mcp_result)
                            if not result.strip():
                                result = '[MCP] 工具执行完成（无文本输出）'
                        except MCPClientError as exc:
                            msg = str(exc)
                            if _mcp_client_error_is_timeout(msg):
                                result = _MCP_BROWSER_TIMEOUT_MSG
                            else:
                                if _mcp_client_error_is_disconnect(msg):
                                    _log.warning(
                                        'MCP bridge disconnected while calling %s: %s',
                                        fn,
                                        msg,
                                    )
                                result = f'[MCP错误] {msg}'
                    else:
                        result = f'[错误] 未知工具: {fn}'
                except Exception as exc:
                    err = f'{type(exc).__name__}: {exc}'
                    trace = _short_exception_trace(exc)
                    result = MSG_TOOL_EXCEPTION.format(error_trace=err)
                    if trace:
                        result = f'{result}\n{trace}'
                msgs.append(
                    {
                        'role': 'tool',
                        'tool_call_id': tc['id'],
                        'content': result,
                    }
                )
            if interrupt_from_here is not None:
                for tc2 in tool_calls[interrupt_from_here:]:
                    msgs.append(
                        {
                            'role': 'tool',
                            'tool_call_id': tc2['id'],
                            'content': agent_cancel.INTERRUPT_TOOL_MESSAGE,
                        }
                    )
                continue

            continue

        if assistant_round:
            text_slices.append(assistant_round)
        llm_text = '\n\n'.join(text_slices).strip()
        yield {
            'type': 'executor_complete',
            'assistant_text': llm_text,
            'input_tokens': in_tok,
            'output_tokens': out_tok,
            'conversation_messages': copy.deepcopy(msgs),
            'stop_reason': 'completed',
        }
        return

    yield {
        'type': 'llm_error',
        'output': (
            '[LLM] 工具调用轮次超过配置上限（环境变量 '
            f'{_AGENT_TOOL_CAP_ENV}），请简化任务。'
        ),
    }


def chat_completion(
    messages: list[dict[str, Any]],
    settings: LlmConnectionSettings,
    *,
    model: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    mcp_client: 'MCPClient | None' = None,
) -> ChatCompletionResult:
    """非流式：消费 :func:`iter_agent_executor_events` 直至得到最终文本。"""
    for ev in iter_agent_executor_events(
        messages,
        settings,
        model=model,
        tools=tools if tools is not None else get_openai_agent_tools(),
        mcp_client=mcp_client,
    ):
        if ev['type'] == 'executor_complete':
            cm = ev.get('conversation_messages')
            return ChatCompletionResult(
                text=str(ev['assistant_text']).strip(),
                input_tokens=int(ev['input_tokens']),
                output_tokens=int(ev['output_tokens']),
                conversation_messages=cm if isinstance(cm, list) else None,
            )
        if ev['type'] == 'llm_error':
            return ChatCompletionResult(
                text=str(ev['output']),
                input_tokens=0,
                output_tokens=0,
                conversation_messages=None,
            )
    return ChatCompletionResult(
        text=f'[LLM] 工具调用轮次超过配置上限（{_AGENT_TOOL_CAP_ENV}），请简化任务。',
        input_tokens=0,
        output_tokens=0,
        conversation_messages=None,
    )
