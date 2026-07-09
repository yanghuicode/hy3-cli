#!/usr/bin/env python3
"""Hy3-CLI — natural language → shell command, powered by Hy3.

Usage examples
--------------
  hy3cli "找出当前目录下最近7天修改、大于100MB的文件"
  hy3cli --explain "查看占用 8080 端口的进程"
  hy3cli exec "docker ps"
  hy3cli chat                 # interactive multi-turn mode
"""
import argparse
import sys

from . import __version__
from .config import get_config
from .client import Hy3Client
from .assistant import translate, repl
from .ui import banner, _c, BOLD, RESET, CYAN, DIM


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hy3cli",
        description="自然语言转 shell 命令的终端助手，由 Hy3 驱动。",
    )
    p.add_argument("--version", action="version", version=f"hy3cli {__version__}")
    p.add_argument("-m", "--model", help="覆盖 HY3_MODEL")
    p.add_argument("-k", "--api-key", help="覆盖 HY3_API_KEY")
    p.add_argument("-b", "--base-url", help="覆盖 HY3_BASE_URL")
    p.add_argument("--os", dest="os_hint", help="覆盖目标系统 (linux/macos/windows)")
    p.add_argument("--mock", action="store_true", help="强制使用 mock 模式（无需 key）")
    p.add_argument("--explain", action="store_true", help="只展示命令与解释，不执行")
    p.add_argument("-y", "--yes", action="store_true", help="低风险命令直接执行，跳过确认")
    p.add_argument("prompt", nargs="*", help="自然语言描述（默认子命令 translate）")
    return p


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    # Make output robust on Windows (GBK console) and elsewhere.
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    # Lightweight subcommand handling: chat / exec / version / translate(default)
    # Scan all tokens (flags may appear before the subcommand).
    sub = None
    for tok in argv:
        if tok in ("chat", "exec", "version"):
            sub = tok
            break
    if sub == "version":
        print(f"hy3cli {__version__}")
        return 0

    cfg = get_config()
    parser = build_parser()
    # Strip the subcommand token so the remaining args parse cleanly.
    rest = list(argv)
    if sub is not None and sub in rest:
        rest.remove(sub)
    args = parser.parse_args(rest)

    mock = args.mock or cfg["mock"]
    client = Hy3Client(
        base_url=args.base_url or cfg["base_url"],
        api_key=args.api_key or cfg["api_key"],
        model=args.model or cfg["model"],
        temperature=cfg["temperature"],
        timeout=cfg["timeout"],
        max_tokens=cfg["max_tokens"],
        retries=cfg["retries"],
        mock=mock,
    )
    os_hint = args.os_hint or cfg["os_hint"]

    if sub == "chat":
        repl(client, os_hint, cfg["history_file"], mock=mock)
        return 0

    prompt = " ".join(args.prompt).strip()
    if not prompt:
        if sub == "exec":
            print(_c("✗ exec 需要一个命令参数。", "31"))
            return 2
        # No prompt: drop into chat for convenience
        print(_c("未提供描述，进入交互模式 (chat)。", DIM))
        repl(client, os_hint, cfg["history_file"], mock=mock)
        return 0

    if sub == "exec":
        from .safety import analyze, describe
        from .ui import render_result
        from .assistant import _run_command
        result = {"command": prompt, "explanation": "用户直接指定的命令。",
                  "risk_level": "low", "caveats": []}
        risk = analyze(prompt)
        risk["describe"] = describe(risk["risk"])
        render_result("(直接执行)", result, risk, os_hint, mock=mock)
        if not risk["safe_to_auto"] and not args.yes:
            from .ui import confirm
            if not confirm("确认执行？"):
                print(_c("已取消。", "33"))
                return 0
        rc = _run_command(prompt, os_hint)
        if rc != 0:
            print(_c(f"↳ 进程退出码: {rc}", "33"))
        return 0

    translate(client, prompt, os_hint, cfg["history_file"],
              explain_only=args.explain, auto=args.yes, mock=mock)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
