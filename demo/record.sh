#!/usr/bin/env bash
# 录制 hy3-cli 的端到端演示（asciinema），并可选转为 GIF。
# 用法：
#   1) 先准备 .env（填好 HY3_API_KEY 等）
#   2) 安装录制工具： pip install asciinema  (以及可选 gif 转换： pip install asciinema-gif 或 brew install asciinema)
#   3) 运行本脚本：  bash demo/record.sh
#
# 录制约 60~90 秒即可（满足 ≤2min 要求）。
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v asciinema >/dev/null 2>&1; then
  echo "请先安装 asciinema: pip install asciinema"
  exit 1
fi

OUT="demo/hy3cli-demo.cast"

# 用 asciinema 录制一段交互脚本（通过 type/echo 模拟用户输入）
asciinema rec "$OUT" --quiet -c "bash demo/demo_session.sh"

echo "✅ 已生成 $OUT"
echo "转 GIF（可选）: asciinema gif $OUT demo/hy3cli-demo.gif"
