"""Core orchestration: natural language -> Hy3 -> safety -> (optional) execute.

This module wires together the Hy3 client and the safety analyzer and is the
single place that decides what gets shown and what (if anything) gets run.
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from .client import Hy3Client, Hy3Error
from .safety import analyze, describe
from .ui import render_result, confirm, banner, RISK_COLOR, _c, BOLD, RESET


def _run_command(cmd: str, os_hint: str) -> int:
    """Execute a command cross-platform.

    On Windows, Hy3 emits PowerShell-flavored commands (Get-ChildItem,
    netstat pipelines, etc.). Running those through cmd.exe (the default for
    subprocess shell=True) fails, so we route them through powershell instead.
    """
    if os_hint == "windows":
        with tempfile.NamedTemporaryFile(
            "w", suffix=".ps1", delete=False, encoding="utf-8"
        ) as f:
            f.write(cmd)
            tmp = f.name
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", tmp],
                check=False,
            )
            return proc.returncode
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    proc = subprocess.run(cmd, shell=True)
    return proc.returncode


def _load_history(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _append_history(path: str, prompt: str, result: dict) -> None:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"prompt": prompt, "result": result}, ensure_ascii=False) + "\n")
    except OSError:
        # History is best-effort; never break the main flow if it can't be written.
        pass


def translate(client: Hy3Client, prompt: str, os_hint: str,
              history_path: str, explain_only: bool = False,
              auto: bool = False, mock: bool = False) -> Optional[dict]:
    """Full pipeline for a single NL request. Returns the parsed result."""
    print(banner())
    try:
        result = client.natural_language_to_command(prompt, os_hint)
    except Hy3Error as e:
        print(_c(f"✗ Hy3 调用失败: {e}", RISK_COLOR["high"]))
        return None
    except Exception as e:  # malformed JSON etc.
        print(_c(f"✗ 无法解析 Hy3 返回: {e}", RISK_COLOR["high"]))
        return None

    risk = analyze(result.get("command", ""))
    risk["describe"] = describe(risk["risk"])
    render_result(prompt, result, risk, os_hint, mock=mock)
    _append_history(history_path, prompt, result)

    if explain_only:
        return result

    cmd = result.get("command", "")
    if risk["risk"] == "high":
        # -y 只跳过中低风险确认，高风险必须显式输入 y
        if not auto and not confirm("⚠ 高风险命令，确认执行？(需输入 y)"):
            print(_c("已取消执行。", RISK_COLOR["medium"]))
            return result
    elif not risk["safe_to_auto"] and not auto:
        if not confirm("确认执行该命令？"):
            print(_c("已取消执行。", RISK_COLOR["medium"]))
            return result

    print(_c("▶ 执行:", BOLD) + " " + cmd)
    try:
        rc = _run_command(cmd, os_hint)
        if rc != 0:
            print(_c(f"↳ 进程退出码: {rc}", RISK_COLOR["medium"]))
    except KeyboardInterrupt:
        print(_c("\n已中断。", RISK_COLOR["medium"]))
    return result


def repl(client: Hy3Client, os_hint: str, history_path: str, mock: bool = False) -> None:
    """Interactive multi-turn mode — showcases Hy3 keeping conversation context."""
    print(banner())
    print(_c("交互模式：输入自然语言，回车生成命令；输入 exit/quit 退出。", BOLD))
    history: list[dict] = []
    while True:
        try:
            prompt = input(_c("\nhy3> ", BOLD + "36")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not prompt:
            continue
        if prompt.lower() in ("exit", "quit", "q"):
            break
        try:
            result = client.natural_language_to_command(prompt, os_hint, history=history)
            risk = analyze(result.get("command", ""))
            risk["describe"] = describe(risk["risk"])
            render_result(prompt, result, risk, os_hint, mock=mock)
            history.append({"role": "user", "content": prompt})
            history.append({"role": "assistant", "content": json.dumps(result, ensure_ascii=False)})
            _append_history(history_path, prompt, result)
        except Exception as e:
            print(_c(f"✗ 出错: {e}", RISK_COLOR["high"]))
