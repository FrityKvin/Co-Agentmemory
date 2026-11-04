---
name: co-agentmemory
description: >-
  接入一个与厂商无关的 AgentMemory + Obsidian 共享记忆体系。适用于多 Agent
  接入、长期上下文、handoff、项目连续性和记忆治理。
metadata:
  short-description: 用 AgentMemory 和 Obsidian 共享 Agent 上下文
---

# Co-Agentmemory

当 agent 加入共享的 AgentMemory + Obsidian 工作区时使用本 Skill。系统由两层和三档
写入组成，写入前先判断信息类型，让记忆保持简洁，让项目文档保留细节。

## 系统模型

- **AgentMemory**：机器可读和可检索层，用于跨会话状态、决策、指针、handoff 和例行观察。
- **Obsidian**：人类可读层，用于项目文档、会议记录、Daily、决策和审计历史。
- **本地 profile**：保存 agent、环境、Vault 和服务地址，不保存 AgentMemory secret。

服务地址和 Vault 路径由使用者配置。首次接入前阅读
[`references/configuration.md`](references/configuration.md)。

## 写入契约

| 层级 | 内容 | 位置 |
|---|---|---|
| Memory | 长期状态、决策、指针、handoff | AgentMemory + Obsidian 中的简短当前状态 |
| Project | 计划、排查过程、设计依据、长报告 | Obsidian 项目目录 |
| Routine | 工作过程中发生了什么 | Obsidian 日期日志 + AgentMemory observation |

AgentMemory 是索引，不是整段对话的仓库。写入应简短、事实化、方便检索；完整解释放在
项目目录，并在记忆中保留必要指针。

优先使用脚本写入：

```bash
python3 scripts/write_log.py \
  --actor "$CO_MEMORY_ACTOR_ID" \
  --project "project-slug" \
  --action "描述已完成的动作" \
  --status success

python3 scripts/write_handoff.py \
  --from "$CO_MEMORY_ACTOR_ID" \
  --to "next-agent" \
  --project "project-slug" \
  --summary "当前状态" \
  --next "下一步动作"
```

AgentMemory 写入失败时脚本会保留可重试的 outbox，默认返回非零状态。网络恢复后执行
`python3 scripts/doctor.py --flush-outbox`。只有明确接受暂时单层状态时才使用
`--allow-pending`。

## 身份与项目

- `actor_id` 表示写入记录的运行时或 Bot。单体运行时可以使用 `codex`，多 Bot 平台可以使用
  `platform.bot`。
- `project_id` 表示当前工作，使用稳定的小写 slug，例如 `research-notes`。
- `runtime_id`、`environment_id`、`actor_id`、`project_id`、`session_id` 是不同字段，不能混用。
- 显示名可以改变，稳定标识应保持不变。

## Session 开始时

在存在时读取 `Agent_Comemory/00_Index/` 和 `Agent_Comemory/01_Shared/` 中的索引与写入协议，
然后只读取当前任务相关的 slots 和项目上下文：`user_preferences`、`tool_guidelines`、
`project_context`、`guidance`、`pending_items`。

先做定向检索，再打开少量 Obsidian 文件。继续旧任务、处理回滚、修改共享基础设施，或用户明确
提到之前的工作时，应主动读取其他 agent 的记录。

## Obsidian 规则

推荐的 agent 工作区：

```text
Agent_Comemory/
├── 00_Index/
├── 01_Shared/
├── 02_Agents/<actor-id>.md
├── 02_Projects/<project-id>/
├── 03_Logs/YYYY/YYYY-MM/YYYY-MM-DD.md
├── 04_Decisions/
├── 05_Handoffs/YYYY/YYYY-MM/
└── 09_Archive/<project-id>/
```

推荐的个人 Wiki：

```text
Personal_Wiki/
├── 01_Daily/YYYY/YYYY-MM-DD.md
├── 02_Inbox/
├── 03_People/
├── 04_Meetings/
├── 05_Projects/
├── 06_Investments/
├── 07_Links/
├── 08_Knowledge/
└── 09_Archive/
```

Daily 每天一个文件，放在年份目录下。已经发生且日期明确的现实事件，如果更新了会议、人物、
项目或投资文档，应在对应日期的 Daily 中追加一条简短链接。日期不确定时进入 Inbox，不猜日期。
agent 的操作过程写入 `Agent_Comemory/03_Logs/`。

项目明确归档后，移动到对应的 `09_Archive/`，保留历史提及和日志，更新当前索引、待办和导航链接。
重新打开项目时先写明确的 decision。

## 安全

不要把 API key、密码、token、cookie、私钥或完整凭据写入 AgentMemory、Obsidian、日志、handoff、
profile 或 commit。`AGENTMEMORY_SECRET` 通过运行时环境注入。

## 参考文档

- [配置](references/configuration.md)
- [MCP 接入](references/mcp-onboarding.md)
- [Obsidian 协作](references/obsidian-collaboration.md)
- [AgentMemory 集成](references/agentmemory-integration.md)

