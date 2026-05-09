# Fluent-Agent

外语学习助手 —— AI 翻译 + 生词库 + 场景对话练习

## 项目目标

辅助外语学习，核心功能三合一：

1. **AI 翻译与生词提取** — 输入任意语言文本，自动翻译并提取 3-5 个重点生词（含地道例句）
2. **生词库管理** — SQLite 持久化存储，按掌握程度（0-5）追踪学习进度
3. **场景对话练习**（计划中）— 接入 GPT-SoVITS 语音合成，模拟真实对话

## 技术栈

| 层面 | 选型 | 说明 |
|------|------|------|
| 语言 | Python 3.10+ | |
| Web UI | Streamlit | 双 Tab 界面：单词大厅 + AI 翻译助手 |
| 数据库 | SQLite | 本地 `data/fluent_agent.db`，WAL 模式 |
| LLM 后端 | Ollama（本地）/ OpenAI 兼容接口 | 默认对接 DeepSeek API |
| TTS（计划） | GPT-SoVITS | 语音合成，场景对话 |

## 项目结构

```
fluent-agent/
├── app/
│   ├── __init__.py
│   ├── database.py        # SQLite 数据库层（vocabulary 表 + CRUD）
│   ├── llm_engine.py      # LLM 引擎（Ollama / OpenAI 兼容双后端）
│   ├── translate_tool.py  # 命令行翻译 + 生词入库交互流程
│   └── web_app.py         # Streamlit Web UI（主界面）
├── data/                  # SQLite 数据库文件目录（自动创建）
├── main.py                # 命令行入口（交互菜单）
├── start_web.bat          # Windows 一键启动脚本
└── requirements.txt       # Python 依赖
```

## 当前进度

### 已完成

- [x] **数据库层** (`app/database.py`)
  - `vocabulary` 表：id, word, translation, context, source, mastery(0-5), created_at, updated_at
  - 完整 CRUD：add / get_all / get_by_id / update_mastery / delete / search

- [x] **LLM 引擎** (`app/llm_engine.py`)
  - 双后端支持：Ollama 本地 API / OpenAI 兼容接口
  - `translate_and_extract(text)` → `{translation, words[{word, translation, example}]}`
  - 环境变量配置，`configure()` 运行时覆盖

- [x] **命令行工具** (`main.py` + `app/translate_tool.py`)
  - 交互菜单：AI 翻译、手动添加、查看/搜索/更新/删除生词
  - 翻译 → 展示结果 → 询问是否入库，全流程

- [x] **Web UI** (`app/web_app.py`)
  - Tab 1「📖 单词大厅」：数据表展示 + 掌握度筛选 + 行内编辑 + 删除
  - Tab 2「🤖 AI 翻译助手」：ChatGPT 式对话框 + 生词卡片 + 一键入库
  - Tab 3「⚙️ 设置」：LLM 后端切换 + 模型选择（预设 + 自定义）
  - 侧边栏：目标语言选择

### 待实现

- [ ] **Streamlit 配置持久化** — 当前 LLM 配置仅在 session 内生效，刷新后恢复默认；考虑写入配置文件或 SQLite
- [ ] **场景对话练习** — 第三个功能 Tab，AI 角色扮演 + 纠错反馈
- [ ] **GPT-SoVITS 集成** — TTS 语音播报，口语跟读
- [ ] **复习模式** — 根据掌握度和艾宾浩斯曲线推送生词复习
- [ ] **导入/导出** — 生词库 CSV / Anki 格式互转
- [ ] **多用户支持** — 不同目标语言的独立词库

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 LLM（二选一）

# 方式 A：DeepSeek API（推荐，开箱即用）
# 在 Web UI 设置页或环境变量中填入 API Key

# 方式 B：本地 Ollama
ollama serve
ollama pull llama3

# 3. 启动
# Web 界面（推荐）：
streamlit run app/web_app.py

# 或命令行：
python main.py
```

## LLM 配置

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FLUENT_AGENT_LLM_API` | `ollama` | `ollama` 或 `openai` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务地址 |
| `OLLAMA_MODEL` | `llama3` | Ollama 模型名 |
| `OPENAI_API_KEY` | (空) | OpenAI 兼容 API Key |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | 兼容接口地址 |
| `OPENAI_MODEL` | `gpt-4o-mini` | 模型名 |

### DeepSeek 示例

```bash
set FLUENT_AGENT_LLM_API=openai
set OPENAI_API_KEY=sk-your-key
set OPENAI_BASE_URL=https://api.deepseek.com
set OPENAI_MODEL=deepseek-chat
```

## 数据库 Schema

```sql
CREATE TABLE vocabulary (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    word        TEXT    NOT NULL,          -- 生词/短语
    translation TEXT    NOT NULL,          -- 释义
    context     TEXT    DEFAULT '',        -- 原文语境或例句
    source      TEXT    DEFAULT '',        -- 来源（书名/文章名）
    mastery     INTEGER DEFAULT 0 CHECK(mastery >= 0 AND mastery <= 5),
    created_at  TEXT    NOT NULL,          -- 创建时间 YYYY-MM-DD HH:MM:SS
    updated_at  TEXT    NOT NULL           -- 更新时间
);
```

## 开发约定

- Python 代码使用标准库类型注解（`dict`、`list[dict]` 等）
- 数据库操作每次调用独立获取连接，避免长连接
- LLM 响应解析有 3 层回退：直接 JSON → markdown 代码块提取 → 原始文本
- Streamlit session_state 用于跨 rerun 状态保持
- 函数在模块内按调用顺序定义（辅助函数在被调用之前）
