"""Command safety analysis — rule based, no dependencies.

Hy3 proposes the command; this module independently judges how dangerous it is
so the CLI can gate execution behind explicit confirmation for risky commands.
"""
from typing import Optional


# (compiled regex, human-readable reason, risk)
_DANGEROUS_PATTERNS = [
    (r"\brm\s+-rf?\b|\brm\s+-fr\b|\brm\b.*--recursive.*--force", "递归强制删除 (rm -rf)，可能不可逆地清除文件/目录", "high"),
    (r":\(\)\s*\{", "Fork 炸弹 (:(){ :|:& };)，会耗尽系统进程", "high"),
    (r"\bdd\b\s+if=", "dd 直接写磁盘/设备，误操作会破坏数据", "high"),
    (r"\bmkfs\b", "mkfs 会格式化并清空文件系统", "high"),
    (r">\s*/dev/sd|/dev/nvme|/dev/disk", "直接向块设备写入，可能破坏磁盘", "high"),
    (r"\b(chmod|chown)\s+-R\s+777\b", "递归开放 777 权限，存在安全隐患", "medium"),
    (r"\bsudo\b", "需要超级用户权限，请确认命令来源可信", "medium"),
    (r"\b(mv|cp)\s+.*\s+/\b", "移动到根/系统目录，请确认目标路径", "medium"),
    (r"\b(curl|wget)\b.*\|\s*(sudo\s+)?(ba)?sh\b", "下载后直接执行，存在代码注入风险", "high"),
    (r"\b(kill|pkill|killall)\b", "会终止进程，请确认目标 PID/名称", "medium"),
    (r"\btaskkill\b.*/F\b|\bStop-Process\b.*-Force\b", "会强制终止进程（可能丢失未保存数据），请确认目标", "medium"),
    (r"\bshutdown\b|\breboot\b|\bhalt\b|\bpoweroff\b", "会关闭或重启系统", "high"),
    (r"\bgit\b.*\b(push\s+--force|--force.*push|reset\s+--hard|clean\s+-f)\b",
     "危险的 Git 操作（强推 / 硬重置 / 强制清理），可能丢失提交", "high"),
    (r"\b(crontab\s+-r|userdel|groupdel)\b", "会删除计划任务或用户/组，可能破坏环境", "high"),
    (r"\b(truncate|shred)\b", "会清空/销毁文件内容", "medium"),
]


def analyze(command: str) -> dict:
    """Return {'risk': 'low'|'medium'|'high', 'safe_to_auto': bool, 'reasons': [...]}."""
    reasons: list[str] = []
    risk = "low"
    rank = {"low": 0, "medium": 1, "high": 2}
    for pattern, reason, level in _DANGEROUS_PATTERNS:
        if _match(pattern, command):
            reasons.append(reason)
            if rank[level] > rank[risk]:
                risk = level
    return {
        "risk": risk,
        "safe_to_auto": risk == "low",
        "reasons": reasons,
    }


def _match(pattern: str, command: str) -> bool:
    import re
    try:
        return re.search(pattern, command, re.IGNORECASE) is not None
    except re.error:
        return False


def describe(risk: str) -> str:
    return {
        "low": "低风险：只读或安全的常规操作",
        "medium": "中风险：会改变状态 / 需权限，请确认后再执行",
        "high": "高风险：破坏性 / 不可逆操作，必须显式确认",
    }.get(risk, risk)
