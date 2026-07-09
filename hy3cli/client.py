"""Hy3 API client — OpenAI-compatible chat completions, zero dependencies.

Hy3 is called exclusively through its HTTP API (no fine-tuning / local
inference). When no API key is present the client transparently falls back to
a built-in mock so the whole flow can be developed and demoed offline.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
import socket
from typing import Optional

SYSTEM_PROMPT = """\
You are Hy3-CLI, a senior DevOps / SRE assistant. Your job is to convert a
natural-language request into a single, correct, and as-safe-as-possible shell
command for the user's operating system.

Output rules (STRICT):
- Reply with ONLY a JSON object. No prose, no markdown code fences.
- JSON schema:
{
  "command": "<the shell command as a single string>",
  "explanation": "<one or two sentences: what it does and the key flags>",
  "risk_level": "low" | "medium" | "high",
  "caveats": ["<optional warning, e.g. destructive, needs sudo, requires network>"]
}
- Prefer one command; use && or | to chain when genuinely needed.
- Match the requested OS shell exactly (PowerShell on Windows, bash/zsh elsewhere).
- If the request is unsafe or ambiguous, still return the safest reasonable
  command, raise risk_level and list caveats. Never invent non-existent commands.
- Do not add explanatory text outside the JSON.
"""


class Hy3Error(RuntimeError):
    pass


def _strip_fences(text: str) -> str:
    """Extract JSON whether or not the model wrapped it in ``` fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
    return text


def _parse_json(text: str) -> dict:
    try:
        return json.loads(_strip_fences(text))
    except json.JSONDecodeError:
        # Fallback: grab the first balanced {...} block
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise Hy3Error("Hy3 did not return valid JSON")
        return json.loads(m.group(0))


# ---------------------------------------------------------------------------
# Mock mode: keyword-driven stand-in so the app runs without a network / key.
# ---------------------------------------------------------------------------
def _mock_command(prompt: str, os_hint: str) -> dict:
    p = prompt.lower()
    win = os_hint == "windows"

    if any(k in p for k in ["大文件", "large file", "大于", "size", "占用空间", "du "] ):
        if any(k in p for k in ["修改", "modified", "天", "day", "最近", "recent"]):
            if win:
                return {
                    "command": 'Get-ChildItem -Recurse -File | Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-7) -and $_.Length -gt 100MB } | Select-Object FullName, Length',
                    "explanation": "递归列出最近 7 天修改且大于 100MB 的文件（PowerShell）。",
                    "risk_level": "low",
                    "caveats": ["仅列举，不会删除或修改任何文件"],
                }
            return {
                "command": "find . -type f -mtime -7 -size +100M -print0 | xargs -0 ls -lh",
                "explanation": "查找当前目录下 7 天内修改、大于 100MB 的文件并以易读大小列出。",
                "risk_level": "low",
                "caveats": ["仅列举，不会删除或修改任何文件"],
            }

    if any(k in p for k in ["端口", "port", "8080", "占用", "监听"]):
        if win:
            return {
                "command": "Get-Process -Id (Get-NetTCPConnection -LocalPort 8080).OwningProcess",
                "explanation": "查看占用 8080 端口的进程信息（PowerShell）。",
                "risk_level": "medium",
                "caveats": ["杀进程前请确认 PID", "需要管理员权限查看部分系统进程"],
            }
        return {
            "command": "lsof -ti :8080 | xargs -r ps -p",
            "explanation": "列出占用 8080 端口的进程详情；如需结束可追加 | xargs kill。",
            "risk_level": "medium",
            "caveats": ["杀进程前请确认 PID", "kill 会终止目标进程"],
        }

    if any(k in p for k in ["git", "提交", "commit", "分支", "分支名", "branch"]):
        return {
            "command": 'git log --oneline --since="2 weeks ago" --pretty=format:"%h %s"',
            "explanation": "列出最近两周的提交（哈希 + 标题），便于整理成摘要。",
            "risk_level": "low",
            "caveats": ["纯只读，不会改变仓库状态"],
        }

    if any(k in p for k in ["docker", "容器", "container"]):
        return {
            "command": "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'",
            "explanation": "以表格形式列出正在运行的容器名称、状态与端口映射。",
            "risk_level": "low",
            "caveats": ["只读操作"],
        }

    if any(k in p for k in ["子目录", "目录大小", "directory size", "每个目录", "磁盘", "disk"]):
        if win:
            return {
                "command": "Get-ChildItem | ForEach-Object { $s = (Get-ChildItem $_ -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum; \"$($_.Name): $([math]::Round($s/1MB,2)) MB\" }",
                "explanation": "递归统计当前每个子目录的总大小（MB）。",
                "risk_level": "low",
                "caveats": ["只读统计"],
            }
        return {
            "command": "du -h --max-depth=1 | sort -h",
            "explanation": "统计当前目录下一级子目录大小并按人类可读格式排序。",
            "risk_level": "low",
            "caveats": ["只读统计"],
        }

    # Generic fallback
    return {
        "command": "echo '请换一种更具体的描述，例如：找出最近7天修改的大于100MB的文件'",
        "explanation": "未匹配到明确意图，给出一个提示命令而非猜测危险操作。",
        "risk_level": "low",
        "caveats": ["这是占位提示，不是真实命令"],
    }


class Hy3Client:
    def __init__(self, base_url: str, api_key: str, model: str,
                 temperature: float = 0.2, timeout: int = 120,
                 max_tokens: int = 4096, retries: int = 3, mock: bool = False):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.retries = retries
        self.mock = mock
        self.endpoint = f"{self.base_url}/chat/completions"

    # -- low level ---------------------------------------------------------
    def chat(self, messages: list[dict], temperature: Optional[float] = None) -> str:
        if self.mock or not self.api_key:
            # Use the last user message as the mock trigger.
            last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
            os_hint = ""
            for m in messages:
                if m["role"] == "system" and "OS:" in m["content"]:
                    os_hint = m["content"].split("OS:")[-1].strip().split()[0]
            return json.dumps(_mock_command(last_user, os_hint or "linux"), ensure_ascii=False)
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
            # Best-effort: ask reasoning-capable gateways to skip the thinking
            # stage. Honored by some Hy3 deployments; ignored (but harmless) by
            # others. A large max_tokens budget is the real safeguard.
            "chat_template_kwargs": {"enable_thinking": False},
        }
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        data = None
        last_err: Optional[Hy3Error] = None
        for attempt in range(self.retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                # 4xx (bad token, bad request) are permanent — don't retry.
                if e.code >= 500:
                    last_err = Hy3Error(f"Hy3 API HTTP {e.code}: {e.read().decode('utf-8', 'ignore')}")
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise Hy3Error(f"Hy3 API HTTP {e.code}: {e.read().decode('utf-8', 'ignore')}")
            except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
                # Transient network hiccups (e.g. WinError 10060) — retry.
                reason = getattr(e, "reason", e)
                last_err = Hy3Error(f"Hy3 API network error: {reason}")
                time.sleep(min(2 ** attempt, 8))
                continue
        if data is None:
            assert last_err is not None
            raise last_err
        try:
            msg = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as e:
            raise Hy3Error(f"Unexpected Hy3 response shape: {e}")
        # Prefer the final answer in `content`. If the reasoning budget
        # truncated it to null/empty, try to salvage a JSON object from the
        # reasoning trace as a last resort.
        content = msg.get("content")
        if not content or not content.strip():
            rc = msg.get("reasoning_content") or ""
            m = re.search(r"\{.*\}", rc, re.DOTALL)
            content = m.group(0) if m else None
        if not content or not content.strip():
            raise Hy3Error(
                "Hy3 returned empty content (reasoning budget may be exhausted). "
                "Try raising HY3_MAX_TOKENS."
            )
        return content

    # -- high level --------------------------------------------------------
    def natural_language_to_command(self, prompt: str, os_hint: str,
                                    history: Optional[list[dict]] = None) -> dict:
        system = SYSTEM_PROMPT + f"\n\nTarget OS: {os_hint}"
        messages = [{"role": "system", "content": system}]
        if history:
            messages.extend(history[-6:])
        messages.append({"role": "user", "content": prompt})
        raw = self.chat(messages)
        return _parse_json(raw)
