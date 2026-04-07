#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remotion 技能包
描述: 通过 React 代码创建视频动画的框架
官方: https://www.remotion.dev
"""

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "remotion",
        "description": "Remotion - 用 React/TypeScript 代码创建视频动画的框架。支持导出 MP4/WebM/GIF、数据可视化动画等",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["guide", "example", "install", "hooks"],
                    "description": "操作类型"
                }
            }
        }
    }
}

# Remotion 核心特点
FEATURES = [
    "🎬 用 React/TypeScript 编写视频",
    "⚛️ 完全基于 React 组件化",
    "🎞️ 导出 MP4/WebM/GIF",
    "📊 支持数据可视化动画",
    "🎨 Tailwind CSS 样式支持",
]

# 安装命令
INSTALL_COMMANDS = [
    "npm init video@latest",
    "yarn create video"
]

# 常用 Hooks
HOOKS_REFERENCE = """
┌─────────────────────┬─────────────────────────────────┐
│ Hook                │ 用途                            │
├─────────────────────┼─────────────────────────────────┤
│ useVideoConfig()    │ 获取 fps, 帧数, 时长等配置      │
│ useCurrentFrame()   │ 获取当前帧数                    │
│ useTime()           │ 获取当前时间（秒）              │
│ AbsoluteFill        │ 填充整个画布的容器组件         │
│ Sequence            │ 序列组件，控制播放顺序          │
│ interpolate()       │ 插值函数，创建平滑动画          │
└─────────────────────┴─────────────────────────────────┘
"""

# 示例代码
EXAMPLE_CODE = '''
import { Composition } from 'remotion';
import { HelloWorld } from './HelloWorld';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="HelloWorld"
      component={HelloWorld}
      durationInFrames={150}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};

// HelloWorld/Title.tsx
import { useVideoConfig, useCurrentFrame } from 'remotion';

export const Title: React.FC<{ title: string }> = ({ title }) => {
  const frame = useCurrentFrame();
  const opacity = frame < 30 ? frame / 30 : 1;
  
  return <div style={{ fontSize: '120px', opacity }}>{title}</div>;
};
'''

# 渲染命令
RENDER_COMMANDS = [
    "npm start          # 本地预览",
    "npm run build      # 构建",
    "npx remotion render HelloWorld out.mp4  # 渲染视频"
]


def execute(**kwargs) -> str:
    """执行技能"""
    action = kwargs.get("action", "guide")
    
    if action == "guide":
        return _get_guide()
    elif action == "example":
        return EXAMPLE_CODE
    elif action == "install":
        return "\n".join(INSTALL_COMMANDS)
    elif action == "hooks":
        return HOOKS_REFERENCE
    else:
        return _get_guide()


def _get_guide() -> str:
    return f"""
╔════════════════════════════════════════════════════════════╗
║              Remotion 技能使用指南                          ║
╠════════════════════════════════════════════════════════════╣
║  用 React/TypeScript 代码创建视频动画                       ║
║  官方: https://www.remotion.dev                             ║
╠════════════════════════════════════════════════════════════╣
║  功能特性:                                                  ║
{"".join(f"║    {f}                                             ║" for f in FEATURES)}
╠════════════════════════════════════════════════════════════╣
║  安装命令:                                                  ║
{"".join(f"║    {cmd}                                           ║" for cmd in INSTALL_COMMANDS)}
╠════════════════════════════════════════════════════════════╣
║  常用 Hooks:                                                ║
{HOOKS_REFERENCE}
╠════════════════════════════════════════════════════════════╣
║  渲染命令:                                                  ║
{"".join(f"║    {cmd}                                           ║" for cmd in RENDER_COMMANDS)}
╚════════════════════════════════════════════════════════════╝

📌 常用操作:
   remotion action="example"   # 查看示例代码
   remotion action="install"   # 查看安装命令
   remotion action="hooks"     # 查看常用 Hooks
"""
