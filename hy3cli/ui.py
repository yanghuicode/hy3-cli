"""Terminal rendering helpers (ANSI, no dependencies)."""
from typing import Optional

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
BLUE = "\033[34m"

RISK_COLOR = {"low": GREEN, "medium": YELLOW, "high": RED}


def _c(text: str, color: str) -> str:
    return f"{color}{text}{RESET}"


def banner() -> str:
    return (
        _c("⚡ Hy3-CLI", BOLD + CYAN)
        + _c("  — natural language → shell, powered by Hy3", DIM)
    )


def render_result(prompt: str, result: dict, risk: dict,
                  os_hint: str, mock: bool = False) -> None:
    cmd = result.get("command", "")
    explanation = result.get("explanation", "")
    caveats = result.get("caveats", []) or []
    risk_level = risk.get("risk", "low")
    color = RISK_COLOR.get(risk_level, GREEN)

    print()
    print(_c("┌─ 请求", DIM))
    print(_c("│ ", DIM) + prompt)
    print(_c("└─", DIM))
    print()
    print(_c("💡 Hy3 生成的命令", BOLD))
    print(_c("  $ ", GREEN + BOLD) + cmd)
    print()
    print(_c("说明: ", CYAN) + explanation)
    print(_c("目标系统: ", CYAN) + os_hint)
    if mock:
        print(_c("⚠ 当前为 MOCK 模式（未配置 HY3_API_KEY），输出为占位示例。", YELLOW))
    print()
    print(_c("风险等级: ", BOLD) + _c(risk_level.upper(), color) + _c("  " + risk.get("describe", ""), DIM))
    if risk.get("reasons"):
        for r in risk["reasons"]:
            print(_c("  • ", RED) + r)
    if caveats:
        print(_c("注意: ", YELLOW))
        for c in caveats:
            print(_c("  • ", YELLOW) + c)
    print()


def confirm(prompt_text: str, default_no: bool = True) -> bool:
    suffix = " [y/N] " if default_no else " [Y/n] "
    try:
        ans = input(_c(prompt_text, BOLD) + suffix).strip().lower()
    except EOFError:
        return False
    if default_no:
        return ans in ("y", "yes")
    return ans not in ("n", "no")
