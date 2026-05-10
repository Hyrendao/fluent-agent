# Fluent-Agent

外语学习助手 —— AI 翻译 + 生词库 + 场景对话（语音输入/输出）

## 项目目标

辅助外语学习，核心功能三合一：

1. **AI 翻译与生词提取** — 输入任意语言文本，自动翻译并提取 3-5 个重点生词（含地道例句）
2. **生词库管理** — SQLite 持久化存储，按掌握程度（0-5）追踪学习进度
3. **场景对话练习** — AI 角色扮演 + 语法纠错 + 语音输入（STT）+ 语音输出（TTS）

## 技术栈

| 层面 | 选型 | 说明 |
|------|------|------|
| 语言 | Python 3.10+ | |
| Web UI | Streamlit 1.57+ | 四 Tab 界面：单词大厅 + AI 翻译助手 + 场景对话 + 设置 |
| 数据库 | SQLite | 本地 `data/fluent_agent.db`，WAL 模式 |
| LLM 后端 | Ollama（本地）/ OpenAI 兼容接口 | 推荐 DeepSeek API 或本地 gemma3:4b |
| TTS | Edge-TTS（默认）/ GPT-SoVITS（计划） | Microsoft 免费神经网络语音，支持 en/ja/zh/ko/fr/de/es |
| STT | Google Speech Recognition | 浏览器录音 → Python 端转录，支持多语言 |

## 项目结构

```
fluent-agent/
├── app/
│   ├── __init__.py
│   ├── database.py        # SQLite 数据库层（vocabulary 表 + CRUD）
│   ├── llm_engine.py      # LLM 引擎（翻译 + 场景对话 + XML 解析）
│   ├── tts_engine.py      # TTS 引擎（Edge-TTS + GPT-SoVITS 双后端）
│   └── web_app.py         # Streamlit Web UI（主界面）
├── data/                  # SQLite 数据库文件目录（自动创建）
├── main.py                # 命令行入口（交互菜单）
├── .env                   # LLM 配置文件（不进入版本控制）
├── start_web.bat          # Windows 一键启动脚本
└── requirements.txt       # Python 依赖
```

## 功能总览

### 单词大厅
- 生词数据表展示，按掌握度（0-5）筛选
- 行内编辑掌握度、一键删除
- 所有数据持久化到 SQLite

### AI 翻译助手
- ChatGPT 式对话框，输入文本自动翻译
- AI 提取 3-5 个重点生词，含翻译 + 地道例句
- 生词卡片一键存入词库

### 场景对话
- 6 个预设场景：咖啡店、医院、面试、酒店、机场、自由对话
- AI 扮演角色，用目标语言自然对话（B1-B2 难度）
- 语法纠错反馈（原文 → 修正 → 解释）
- **语音输入**：点击麦克风录音，Google STT 自动转录
- **语音输出**：Edge-TTS 朗读 AI 回复，支持自动播放
- 同时支持文字输入作为 fallback

### 设置
- LLM 后端切换（OpenAI 兼容 / Ollama）
- 模型预设选择 + 自定义模型名
- API Key、Base URL 配置
- TTS 后端切换 + 多语言音色配置

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 LLM（创建 .env 文件）

# 方式 A：DeepSeek API（推荐，开箱即用）
# 创建 .env 文件，内容见下方模板

# 方式 B：本地 Ollama
ollama serve           # 先启动 Ollama 服务
ollama pull gemma3:4b  # 下载模型

# 3. 启动
streamlit run app/web_app.py
```

## .env 配置模板

```bash
# LLM — DeepSeek API（推荐）
FLUENT_AGENT_LLM_API=openai
OPENAI_API_KEY=sk-your-deepseek-key-here
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat

# LLM — 本地 Ollama
# FLUENT_AGENT_LLM_API=ollama
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=gemma3:4b

# TTS — Edge-TTS（默认，免费在线）
FLUENT_AGENT_TTS_API=edge-tts
EDGE_TTS_VOICE_EN=en-US-AriaNeural
EDGE_TTS_VOICE_JA=ja-JP-NanamiNeural
EDGE_TTS_VOICE_ZH=zh-CN-XiaoxiaoNeural

# TTS — GPT-SoVITS（本地音色克隆，需先启动 API）
# FLUENT_AGENT_TTS_API=gpt-sovits
# GPT_SOVITS_URL=http://localhost:9880
# GPT_SOVITS_REF_AUDIO=E:\work\GPT-SoVITS-Work\录音.wav
# GPT_SOVITS_PROMPT_LANG=zh
```

## 环境变量参考

### LLM

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FLUENT_AGENT_LLM_API` | `ollama` | `ollama` 或 `openai` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务地址 |
| `OLLAMA_MODEL` | `llama3` | Ollama 模型名 |
| `OPENAI_API_KEY` | (空) | OpenAI 兼容 API Key |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | 兼容接口地址 |
| `OPENAI_MODEL` | `gpt-4o-mini` | 模型名 |
| `FLUENT_AGENT_TIMEOUT` | `300` | 请求超时（秒） |

### TTS

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FLUENT_AGENT_TTS_API` | `edge-tts` | `edge-tts` 或 `gpt-sovits` |
| `EDGE_TTS_VOICE_EN` | `en-US-AriaNeural` | 英语音色 |
| `EDGE_TTS_VOICE_JA` | `ja-JP-NanamiNeural` | 日语音色 |
| `EDGE_TTS_VOICE_ZH` | `zh-CN-XiaoxiaoNeural` | 中文音色 |
| `GPT_SOVITS_URL` | `http://localhost:9880` | GPT-SoVITS API 地址 |
| `GPT_SOVITS_REF_AUDIO` | — | 参考音频路径 |
| `GPT_SOVITS_PROMPT_LANG` | `zh` | 参考音频语言 |

## 模型选择建议

### 本地 Ollama

| 模型 | 参数量 | 推荐场景 | 说明 |
|------|--------|----------|------|
| gemma3:4b | 4.3B | 翻译 / 对话 | 轻量快速，RTX 4060 Ti 流畅运行 |
| gemma4:latest | 8.0B | 翻译 / 对话 | 更强能力，需 8GB+ 显存 |
| phi3:mini | 3.8B | 翻译 | 最轻量，CPU 也能跑 |

### 云端 API

| 服务 | 模型 | 说明 |
|------|------|------|
| DeepSeek | `deepseek-chat` | 性价比高，中文友好 |
| OpenAI | `gpt-4o-mini` | 快速便宜 |

> **注意**：推理模型（如 qwen3.5、DeepSeek R1）不适合翻译/对话 —— 大量 token 消耗在思考链上。本项目 LLM 引擎已做 `thinking` 字段回退处理，但仍建议用标准模型。

## 数据库 Schema

```sql
CREATE TABLE vocabulary (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    word        TEXT    NOT NULL,
    translation TEXT    NOT NULL,
    context     TEXT    DEFAULT '',
    source      TEXT    DEFAULT '',
    mastery     INTEGER DEFAULT 0 CHECK(mastery >= 0 AND mastery <= 5),
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);
```

## 开发约定

- Python 标准库类型注解（`dict`、`list[dict]` 等）
- 数据库操作每次调用独立获取连接，避免长连接
- LLM 场景对话响应使用 XML 格式解析（`<response>` / `<corrections>`），避免 JSON 转义问题
- LLM 翻译响应有 3 层回退：直接 JSON → markdown 代码块提取 → 原始文本
- Streamlit session_state 用于跨 rerun 状态保持
- 语音输入使用 `st.audio_input()` + `speech_recognition`，带 15 秒超时
- `.env` 不进入版本控制，通过 `python-dotenv` 在启动时自动加载
