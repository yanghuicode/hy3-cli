#!/usr/bin/env bash
# 被 demo/record.sh 调用，作为 asciinema 录制的“剧本”。
# 注意：演示命令均为只读/列举类，安全可执行；高风险命令请人工在真实终端演示。
set +e

echo "==================================================="
echo "  Hy3-CLI 端到端演示 (powered by Hy3)"
echo "==================================================="
echo
echo ">>> Demo 1: 文件检索（低风险，直接执行）"
python3 -m hy3cli -y "找出当前目录下最近7天修改、大于100MB的文件"
echo
echo ">>> Demo 2: 端口排查（中风险，确认后执行）"
printf 'y\n' | python3 -m hy3cli "查看占用 8080 端口的进程并杀掉"
echo
echo ">>> Demo 3 (可选): 交互模式 chat"
echo "（交互模式请手动录制，或去掉下面注释）"
# printf 'docker ps\nexit\n' | python3 -m hy3cli chat
echo
echo "==================================================="
echo "  演示结束"
echo "==================================================="
