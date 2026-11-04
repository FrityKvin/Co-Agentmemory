# Co-Agentmemory

一个与厂商无关的开源 Skill，用 AgentMemory 和 Obsidian 在不同 AI agent
之间共享长期工作上下文。

[English](./README.md)

这套协议把两类信息放在合适的位置：AgentMemory 保存简短、可检索的机器记忆；
Obsidian 保存人类可读记录、项目细节和审计历史。Agent 使用稳定身份和项目 slug，
跨运行时继续工作。

仓库不包含托管服务、API key、默认 endpoint、个人路径或具体 Agent 的私有配置，
使用者需要在本地提供这些配置。

## 快速开始

1. 阅读 [`SKILL.zh-CN.md`](./SKILL.zh-CN.md) 或 [`SKILL.md`](./SKILL.md)。
2. 阅读 [`references/configuration.md`](./references/configuration.md)。
3. 使用目标客户端自己的配置注册 AgentMemory MCP。
4. 准备好 Obsidian Vault 后运行首次接入向导：

运行前先在已有 Vault 中创建 `Agent_Comemory/00_Index/README.md`。

```bash
python3 scripts/onboard.py \
  --runtime codex \
  --environment laptop \
  --vault /absolute/path/to/vault \
  --agentmemory-url https://memory.example.com
```

profile 只保存路径和身份，不保存凭据。`AGENTMEMORY_SECRET` 必须由运行时环境
注入，不能写进 profile 或仓库。

## 推荐 Vault 结构

```text
Vault/
├── Personal_Wiki/
│   ├── 01_Daily/YYYY/YYYY-MM-DD.md
│   ├── 02_Inbox/
│   ├── 03_People/
│   ├── 04_Meetings/
│   ├── 05_Projects/
│   ├── 06_Investments/
│   ├── 07_Links/
│   ├── 08_Knowledge/
│   └── 09_Archive/
└── Agent_Comemory/
    ├── 00_Index/
    ├── 01_Shared/
    ├── 02_Agents/
    ├── 02_Projects/
    ├── 03_Logs/YYYY/YYYY-MM/YYYY-MM-DD.md
    ├── 04_Decisions/
    ├── 05_Handoffs/YYYY/YYYY-MM/*.md
    └── 09_Archive/
```

`Personal_Wiki` 是推荐名称，不是强制名称。Vault 使用其他目录名时，在 profile
中设置 `personal_wiki_dir`，或设置 `CO_MEMORY_PERSONAL_WIKI_DIR`。

## 脚本

- `scripts/onboard.py`：创建不含凭据的本地身份 profile。
- `scripts/write_log.py`：将例行日志写入 Obsidian 和 AgentMemory。
- `scripts/write_handoff.py`：将交接写入两层。
- `scripts/doctor.py`：检查 Vault、AgentMemory 健康状态、MCP 桥接和待补写 outbox。

AgentMemory 暂时不可用时，脚本会保留 JSONL outbox；默认以非零状态提示双写未完成。
网络恢复后执行：

```bash
python3 scripts/doctor.py --flush-outbox
```

## 客户端配置

`agents/openai.yaml` 只有 OpenAI/Codex 风格客户端使用的界面元数据，不负责给其他
客户端配置 MCP。客户端无关的 stdio 接入方式见
[`references/mcp-onboarding.md`](./references/mcp-onboarding.md)。

## 开发验证

需要 Python 3.10 或更新版本，脚本仅使用标准库；Windows 环境若没有 IANA 时区数据，
需安装 `tzdata` 包。

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/*.py
```

## 许可证

MIT，见 [`LICENSE`](./LICENSE)。
