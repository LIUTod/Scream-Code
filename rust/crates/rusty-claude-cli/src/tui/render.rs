//! 欢迎界面：ASCII 使用单个含 `\n` 的静态字符串，按行切成 [`Line`]，再用 [`Paragraph`] 居中渲染。
//! 不做高度自适应计算，避免布局逻辑与「哑终端」职责混杂。

use ratatui::{
    prelude::*,
    style::Modifier,
    widgets::{Block, Paragraph},
};

/// `SCREAMCODE` FIGlet slant 多行 ASCII（与 `replLauncher._SLANT_LOGO_LINES` 一致）。
const SPLASH_ASCII: &str = r"   _____ __________  _________    __  _____________  ____  ______
  / ___// ____/ __ \/ ____/   |  /  |/  / ____/ __ \/ __ \/ ____/
  \__ \/ /   / /_/ / __/ / /| | / /|_/ / /   / / / / / / / __/
 ___/ / /___/ _, _/ /___/ ___ |/ /  / / /___/ /_/ / /_/ / /___
/____/\____/_/ |_/_____/_/  |_/_/  /_/\____/\____/_____/_____/";

pub const SPLASH_SUBTITLE: &str = ">>> 🚀scream code🚀 | 基于 Claude code 类学习为基础开发 <<<";

fn splash_text() -> Text<'static> {
    let accent = Color::Rgb(170, 210, 245);
    let mut lines: Vec<Line<'static>> = SPLASH_ASCII
        .lines()
        .map(|line| Line::from(Span::styled(line, Style::default().fg(accent))))
        .collect();
    lines.push(Line::default());
    lines.push(Line::from(Span::styled(
        SPLASH_SUBTITLE,
        Style::default()
            .fg(Color::DarkGray)
            .add_modifier(Modifier::DIM),
    )));
    Text::from(lines)
}

/// 有边框的对话区内静态居中欢迎图（仅 UI，业务状态由 Python）。
pub fn render_idle_splash(f: &mut Frame<'_>, chat_area: Rect, chat_block: Block<'_>, bg: Color) {
    let para = Paragraph::new(splash_text())
        .block(chat_block)
        .alignment(Alignment::Center)
        .style(Style::default().bg(bg));
    f.render_widget(para, chat_area);
}
