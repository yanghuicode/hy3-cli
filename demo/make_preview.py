#!/usr/bin/env python3
"""Generate an animated SVG "terminal recording" preview of hy3-cli.

This is an OFFLINE stand-in for the required demo video/GIF. It replays the two
end-to-end demo flows using the same text the mock mode produces, with a CSS
typing/fade-in animation so the flow is visible without a screen recorder.
The real <=2min video should be recorded on the user's machine via demo/record.sh.
"""
import os

TRANSCRIPT = [
    ("h", "⚡ Hy3-CLI  — natural language → shell, powered by Hy3"),
    ("u", "$ hy3cli \"找出当前目录下最近7天修改、大于100MB的文件\""),
    ("a", ""),
    ("a", "💡 Hy3 生成的命令"),
    ("c", "$ find . -type f -mtime -7 -size +100M -print0 | xargs -0 ls -lh"),
    ("a", "说明: 查找当前目录下 7 天内修改、大于 100MB 的文件并以易读大小列出。"),
    ("a", "风险等级: LOW   低风险：只读或安全的常规操作"),
    ("a", "注意: • 仅列举，不会删除或修改任何文件"),
    ("u", "$ hy3cli \"查看占用 8080 端口的进程并杀掉\""),
    ("a", ""),
    ("a", "💡 Hy3 生成的命令"),
    ("c", "$ lsof -ti :8080 | xargs -r ps -p"),
    ("a", "说明: 列出占用 8080 端口的进程详情；如需结束可追加 | xargs kill。"),
    ("a", "风险等级: MEDIUM   中风险：会改变状态 / 需权限，请确认后再执行"),
    ("a", "注意: • 杀进程前请确认 PID   • kill 会终止目标进程"),
    ("h", "✅ 两个端到端流程跑通（真实视频请用 demo/record.sh 录制）"),
]

COLORS = {
    "h": "#58a6ff",  # header / hint
    "u": "#7ee787",  # user prompt
    "a": "#c9d1d9",  # assistant text
    "c": "#ffa657",  # command
}

WIDTH, HEIGHT = 780, 460
X0, Y0, LH = 24, 70, 22


def build():
    lines = []
    y = Y0
    delay = 0.0
    step = 0.55
    for kind, text in TRANSCRIPT:
        color = COLORS.get(kind, "#c9d1d9")
        # optional line wrap for long commands
        rows = wrap(text, 86)
        for i, row in enumerate(rows):
            begin = f"{delay:.2f}s"
            lines.append(
                f'  <text x="{X0}" y="{y}" fill="{color}" class="ln" '
                f'style="animation-delay:{begin}">{escape(row)}</text>'
            )
            y += LH
            if i == 0:
                delay += step
        delay += step * 0.4
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" font-family="Consolas, 'Courier New', monospace" font-size="13">
  <style>
    .ln {{ opacity:0; animation: fade 0.35s ease forwards; }}
    @keyframes fade {{ from {{ opacity:0; }} to {{ opacity:1; }} }}
  </style>
  <rect width="{WIDTH}" height="{HEIGHT}" fill="#0d1117" rx="10"/>
  <rect width="{WIDTH}" height="34" fill="#161b22" rx="10"/>
  <circle cx="20" cy="17" r="6" fill="#ff5f56"/>
  <circle cx="40" cy="17" r="6" fill="#ffbd2e"/>
  <circle cx="60" cy="17" r="6" fill="#27c93f"/>
  <text x="300" y="21" fill="#8b949e" font-size="12">hy3-cli — demo preview (mock)</text>
{os.linesep.join(lines)}
</svg>'''
    return svg


def wrap(text, n):
    if len(text) <= n:
        return [text]
    out, cur = [], ""
    for ch in text:
        cur += ch
        if len(cur) >= n and ch == " ":
            out.append(cur)
            cur = "  "
    out.append(cur)
    return out


def escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview.svg")
    with open(out, "w", encoding="utf-8") as f:
        f.write(build())
    print("wrote", out)
