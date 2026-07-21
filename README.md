# Hy3-CLI

> 自然语言 → shell 命令的终端助手，**由 Hy3 大模型驱动**。


零依赖（仅 Python 标准库），支持 OpenAI 兼容的 Hy3 API，内置 **mock 离线模式**，开箱即可演示。

---

## ✨ 它能做什么

- 把一句中文/英文自然语言，变成**正确、带解释、标注风险等级**的 shell 命令。
- **安全门禁**：自动识别 `rm -rf`、`dd`、`mkfs`、fork 炸弹、危险 Git 操作等，高风险命令必须二次确认。
- **交互模式（chat）**：多轮对话，Hy3 保留上下文，适合连续运维任务。
- **跨平台**：自动适配 Linux/macOS（bash/zsh）与 Windows（PowerShell）。
- **可审计**：每次请求记录到本地历史文件。

---

## 🧩 Hy3 在系统中承担的角色

本应用**全程通过 Hy3 的 HTTP API 调用模型**，没有任何训练 / 微调 / 本地推理部署。

```
用户自然语言
     │
     ▼
hy3cli (Python CLI，标准库实现)
     │  构造 system prompt + 用户请求（含目标 OS 提示）
     ▼
Hy3 /chat/completions  ──►  返回 JSON {command, explanation, risk_level, caveats}
     │
     ▼
安全分析模块(规则)  ──►  风险等级 + 提示
     │
     ▼
终端渲染 + 确认执行（高风险需显式确认）
```

- **Hy3 负责「理解 + 生成」**：把自然语言意图翻译成单条 shell 命令，并给出解释、风险初判与注意事项。
- **本地代码负责「安全 + 交互 + 执行」**：独立的安全门禁、确认流程、跨平台适配与历史记录，弥补纯生成模型在「是否该执行」上的决策。

> 即使在无 key 的 **mock 模式**下，整体交互链路也完全可跑通，便于离线开发与评审。

---

## 🚀 快速开始

### 1. 准备

```bash
# 需要 Python 3.8+
python3 --version

# 复制并填写你的 Hy3 接入信息
cp .env.example .env
# 编辑 .env：填入 HY3_API_KEY / HY3_BASE_URL / HY3_MODEL
```

> 不填 `HY3_API_KEY` 会自动进入 mock 模式，可直接体验交互。

> ⚙️ **关于推理模型**：默认的 `hunyuan-3.0-free` 是推理型模型，会在给出最终 JSON 前
> 消耗大量 token 进行「思考」。因此必须给足 `HY3_MAX_TOKENS`（默认 4096），否则最终答案会被
> 截断为空。客户端已内置**重试**（默认 3 次，退避补偿）以应对公网 endpoint 的偶发抖动。
> 若你的 Hy3 部署走的是非推理模型，可适当调小 `HY3_MAX_TOKENS` 以降低延迟。

### 2. 运行（两种方式）

```bash
# 方式 A：直接以模块运行（无需安装）
python3 -m hy3cli "找出当前目录下最近7天修改、大于100MB的文件"

# 方式 B：安装为命令（可选，需网络）
pip install -e .
hy3cli "查看占用 8080 端口的进程"
```

### 3. 常用命令

```bash
# 只解释、不执行
hy3cli --explain "递归统计每个子目录的大小"

# 交互模式（多轮）
hy3cli chat

# 直接执行一条已确认命令（仍会过安全门禁）
hy3cli exec "docker ps"

# 强制 mock 模式（无 key 演示）
hy3cli --mock "查看占用 8080 端口的进程"
```

---

## 🎬 两个端到端 Demo 流程

> 录制脚本见 `demo/record.sh`，按说明即可产出 ≤2min 的 asciinema 录像 / GIF。

**Demo 1 — 文件检索（低风险）**
```
$ hy3cli "找出当前目录下最近7天修改、大于100MB的文件"
→ Hy3 生成命令 → 低风险 → 解释 + 风险标注
# 真实输出（Windows / PowerShell）：
$ Get-ChildItem -Path . -Recurse -File | Where-Object {
    $_.LastWriteTime -ge (Get-Date).AddDays(-7) -and $_.Length -gt 100MB }
```

**Demo 2 — 端口排查（中风险，带确认 + 安全提示）**
```
$ hy3cli "查看占用 8080 端口的进程并杀掉"
→ Hy3 生成命令 → 中风险(含 Stop-Process -Force) → 提示确认 PID → 执行
# 真实输出（Windows / PowerShell）：
$ Get-NetTCPConnection -LocalPort 8080 ... | ForEach-Object { Stop-Process -Id $_ -Force }
```

> ✅ **已用真实 Hy3 验证**：上述两条命令及 `chat` 多轮模式，均通过真实 `hunyuan-3.0-free`
> 模型跑通。完整终端输出见 [`demo/real-session.txt`](./demo/real-session.txt)。

仓库内 `demo/demo_prompts.txt` 给出可直接复用的演示脚本。

---

## 🤝 与 CodeBuddy / WorkBuddy 的协作记录

本仓库为「vibe-coded」作品，下列模块由 **CodeBuddy / WorkBuddy（基于 Hy3）** 协助生成或重构：

- `hy3cli/client.py`：Hy3 OpenAI 兼容客户端、JSON 解析与 mock 模式（初版由 CodeBuddy 生成，后由 WorkBuddy 接入真实 `hunyuan-3.0-free` 推理模型——补了 `max_tokens` 预算、`chat_template_kwargs` 关闭思考、空内容回退 `reasoning_content` 提取，以及瞬时网络错误的**重试**）。
- `hy3cli/safety.py`：危险命令规则集（由 WorkBuddy 建议并整理，本次新增 `taskkill /F`、`Stop-Process -Force` 中风险规则）。
- `hy3cli/assistant.py`：NL→命令主流程与交互模式（由 CodeBuddy 协助搭建骨架；本次由 WorkBuddy 修复 Windows 执行器——PowerShell 命令改经 `powershell -File` 路由，使模型生成的 PowerShell cmdlet 能在 Windows 上真正执行）。
- `README.md` 与 `demo/record.sh`：由 WorkBuddy 撰写。

其余配置、测试与调试由作者完成。

---

## 📦 项目结构

```
hy3-cli/
├── hy3cli/
│   ├── __init__.py      # 版本信息
│   ├── __main__.py      # CLI 入口 (argparse)
│   ├── config.py        # 配置 / .env 加载
│   ├── client.py        # Hy3 客户端 (OpenAI 兼容 + mock)
│   ├── safety.py        # 命令安全分析
│   ├── assistant.py     # 核心编排：NL→Hy3→安全→执行
│   └── ui.py            # 终端渲染
├── tests/               # 单元测试
├── demo/                # 演示录制脚本
├── .env.example
└── README.md
```

---

## 🔒 安全说明

- 本工具**默认不自动执行高风险命令**，需显式输入 `y` 确认。
- 模型生成存在不确定性，执行前请务必阅读「说明 / 风险等级 / 注意」。
- API Key 仅通过环境变量 / `.env` 提供，且 `.env` 已被 git 忽略，不会入库。

---

## 📄 License

MIT — 详见 [LICENSE](./LICENSE)。

---

## 🐦 提交说明（rhinobird2026）

本应用作为独立仓库开发，向 `Tencent-Hunyuan/Hy3` 的 `rhinobird2026` 分支提 PR 时，
请在 PR 中附上：项目说明（即本 README）+ 仓库链接 + 两个 demo 的视频/GIF。
