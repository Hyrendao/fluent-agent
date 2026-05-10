"""Fluent-Agent Web UI —— Streamlit 双 Tab 界面."""

import concurrent.futures
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv

import speech_recognition as sr

# 确保项目根目录在 sys.path 中（streamlit run 时必需）
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))
load_dotenv(_project_root / ".env")

import streamlit as st
from app.database import add_word, delete_word, get_all_words, init_db, update_mastery
from app.llm_engine import configure, converse, translate_and_extract
from app.tts_engine import synthesize, configure as configure_tts

# ── 页面初始化 ────────────────────────────────────────────────────

st.set_page_config(
    page_title="Fluent-Agent 外语学习助手",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()


# ── 辅助函数 ──────────────────────────────────────────────────────

def _render_vocab_card(w: dict, source: str) -> None:
    """渲染单个生词卡片（HTML）。"""
    word = w.get("word", "")
    trans = w.get("translation", "")
    example = w.get("example", "")

    safe_word = word.replace("`", "'")
    safe_trans = trans.replace("`", "'")
    safe_example = example.replace("`", "'")

    card_html = f"""
    <div style="
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 8px;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        color: #1a1a1a;
    ">
        <div style="font-size: 1.2rem; font-weight: 700; margin-bottom: 4px;">
            {safe_word}
        </div>
        <div style="font-size: 0.9rem; color: #555; margin-bottom: 8px;">
            {safe_trans}
        </div>
        <div style="font-size: 0.8rem; color: #777; font-style: italic;
                    border-left: 3px solid #6c63ff; padding-left: 8px;">
            {safe_example}
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    # 保存按钮（每条独立 key）
    card_key = f"save_{hash(word + trans)}"
    if card_key not in st.session_state:
        st.session_state[card_key] = False

    if not st.session_state[card_key]:
        if st.button(f"💾 存入词库", key=f"btn_{card_key}", use_container_width=True):
            try:
                add_word(
                    word=word,
                    translation=trans,
                    context=example,
                    source=source,
                    mastery=0,
                )
                st.session_state[card_key] = True
                st.toast(f"✅ 「{word}」已存入词库！", icon="📚")
            except Exception as e:
                st.toast(f"保存失败: {e}", icon="❌")
    else:
        st.caption("✅ 已存入词库")


# ── 侧边栏（轻量导航） ────────────────────────────────────────────

with st.sidebar:
    st.title("📚 Fluent-Agent")
    st.caption("外语学习助手 v0.2")

    st.divider()

    target_lang = st.selectbox(
        "🌐 目标翻译语言",
        options=["zh", "en", "ja", "ko", "fr", "de", "es"],
        index=0,
        help="AI 翻译的目标语言",
    )

    st.divider()
    st.caption("💡 在「设置」中切换 LLM 模型")

# ── 主界面标题 ────────────────────────────────────────────────────

st.title("📚 Fluent-Agent")
st.caption("外语学习助手 —— 翻译 + 生词库 + 场景对话")

# ── Tab 布局 ──────────────────────────────────────────────────────

tab_vocab, tab_translate, tab_conversation, tab_settings = st.tabs(
    ["📖 单词大厅", "🤖 AI 翻译助手", "💬 场景对话", "⚙️ 设置"]
)

# ══════════════════════════════════════════════════════════════════
#  Tab 1: 单词大厅
# ══════════════════════════════════════════════════════════════════

with tab_vocab:
    # 加载全部数据
    words = get_all_words()

    # 筛选栏
    col_filter, col_count, col_refresh = st.columns([2, 1, 1])
    with col_filter:
        mastery_filter = st.selectbox(
            "按掌握程度筛选",
            options=["全部"] + list(range(6)),
            index=0,
            key="mastery_filter",
        )
    with col_count:
        st.caption("")  # spacer
    with col_refresh:
        if st.button("🔄 刷新", use_container_width=True):
            st.rerun()

    # 过滤
    if mastery_filter != "全部":
        words = [w for w in words if w["mastery"] == int(mastery_filter)]

    st.divider()

    if not words:
        st.info("暂无生词记录，去「AI 翻译助手」添加吧！")
    else:
        st.caption(f"共 {len(words)} 个生词")

        for i, w in enumerate(words):
            col_word, col_trans, col_ctx, col_src, col_mastery, col_act = st.columns(
                [2, 1.5, 2.5, 1.5, 1, 1]
            )

            with col_word:
                st.markdown(f"**{w['word']}**")
            with col_trans:
                st.text(w["translation"])
            with col_ctx:
                ctx = (w["context"] or "")[:60]
                st.caption(ctx if ctx else "—")
            with col_src:
                st.caption(w["source"] or "—")
            with col_mastery:
                new_m = st.number_input(
                    "掌握度",
                    min_value=0,
                    max_value=5,
                    value=int(w["mastery"]),
                    key=f"m_{w['id']}",
                    label_visibility="collapsed",
                )
                if new_m != int(w["mastery"]):
                    update_mastery(w["id"], new_m)
                    st.rerun()
            with col_act:
                if st.button("🗑", key=f"del_{w['id']}", help="删除"):
                    delete_word(w["id"])
                    st.rerun()

            st.divider()

# ══════════════════════════════════════════════════════════════════
#  Tab 2: AI 翻译助手
# ══════════════════════════════════════════════════════════════════

with tab_translate:
    # 初始化 session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # 对话历史
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            # 用户消息
            with st.chat_message("user"):
                st.write(msg["text"])

            # AI 回复
            with st.chat_message("assistant"):
                st.markdown("##### 📝 翻译")
                st.info(msg["translation"])

                if msg["words"]:
                    st.markdown("##### 📚 建议学习的生词")
                    # 生词卡片：每行最多 3 个
                    cols = st.columns(min(len(msg["words"]), 3))
                    for idx, w in enumerate(msg["words"]):
                        col_idx = idx % 3
                        if col_idx == 0 and idx > 0:
                            cols = st.columns(min(len(msg["words"]) - idx, 3))
                        with cols[col_idx]:
                            _render_vocab_card(w, msg.get("source", ""))
                else:
                    st.caption("(AI 未提取到生词)")

    # 输入区域
    if prompt := st.chat_input("输入要翻译的文本，支持任意语言…"):
        # 显示用户消息
        with chat_container:
            with st.chat_message("user"):
                st.write(prompt)

        # 调用 AI
        with st.status("🤔 AI 正在翻译并提取生词…", expanded=True) as status:
            try:
                result = translate_and_extract(prompt, target_lang=target_lang)
                status.update(label="✅ 完成", state="complete")
            except Exception as e:
                status.update(label=f"❌ 失败: {e}", state="error")
                result = {"translation": "", "words": []}

        translation = result.get("translation", "")
        words_list = result.get("words", [])

        # 保存到历史
        st.session_state.chat_history.append(
            {
                "text": prompt,
                "translation": translation,
                "words": words_list,
                "source": "",
            }
        )

        # 显示 AI 回复
        with chat_container:
            with st.chat_message("assistant"):
                st.markdown("##### 📝 翻译")
                st.info(translation)

                if words_list:
                    st.markdown("##### 📚 建议学习的生词")
                    cols = st.columns(min(len(words_list), 3))
                    for idx, w in enumerate(words_list):
                        col_idx = idx % 3
                        if col_idx == 0 and idx > 0:
                            cols = st.columns(min(len(words_list) - idx, 3))
                        with cols[col_idx]:
                            _render_vocab_card(w, "")


# ══════════════════════════════════════════════════════════════════
#  Tab 3: 场景对话
# ══════════════════════════════════════════════════════════════════

with tab_conversation:
    SCENARIOS: dict[str, dict[str, tuple[str, str]]] = {
        "☕ 咖啡店": {
            "en": ("barista", "You are a friendly barista at a cozy coffee shop."),
            "ja": ("バリスタ", "あなたは居心地の良いカフェのバリスタです。"),
        },
        "🏥 医院": {
            "en": ("doctor", "You are a doctor seeing a patient for a routine checkup."),
            "ja": ("医者", "あなたは定期検診で患者を診る医者です。"),
        },
        "💼 面试": {
            "en": ("interviewer", "You are a job interviewer for a marketing position."),
            "ja": ("面接官", "あなたはマーケティング職の採用面接官です。"),
        },
        "🏨 酒店": {
            "en": ("hotel receptionist", "You are a hotel receptionist checking in a guest."),
            "ja": ("ホテルスタッフ", "あなたはチェックイン対応をするホテルのフロントスタッフです。"),
        },
        "✈️ 机场": {
            "en": ("airline agent", "You are an airline check-in agent at the airport."),
            "ja": ("航空会社スタッフ", "あなたは空港のチェックインカウンタースタッフです。"),
        },
        "🗣️ 自由对话": {
            "en": ("language exchange partner", "You are a friendly language exchange partner. Chat naturally about any topic."),
            "ja": ("言語交換パートナー", "あなたはフレンドリーな言語交換パートナーです。自由に会話してください。"),
        },
    }

    # 初始化 conversation session state
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    if "conversation_started" not in st.session_state:
        st.session_state.conversation_started = False
    if "conversation_scenario" not in st.session_state:
        st.session_state.conversation_scenario = None
    if "conversation_role" not in st.session_state:
        st.session_state.conversation_role = ""
    if "conversation_prompt" not in st.session_state:
        st.session_state.conversation_prompt = ""
    if "_voice_key" not in st.session_state:
        st.session_state._voice_key = 0
    if "_tts_audio_bytes" not in st.session_state:
        st.session_state._tts_audio_bytes = None
    if "_last_processed" not in st.session_state:
        st.session_state._last_processed = ""

    # 语音识别语言映射
    WEB_SPEECH_LANG_MAP: dict[str, str] = {
        "en": "en-US",
        "ja": "ja-JP",
        "zh": "zh-CN",
        "ko": "ko-KR",
        "fr": "fr-FR",
        "de": "de-DE",
        "es": "es-ES",
    }

    # ── 场景选择 ──
    scenario_names = list(SCENARIOS.keys())

    col_scene, col_start, col_reset = st.columns([2, 1, 1])
    with col_scene:
        # Determine which language's scenarios to show
        lang_key = "en" if target_lang.startswith("en") else ("ja" if target_lang.startswith("ja") else "en")
        selected_scenario = st.selectbox(
            "选择对话场景",
            options=scenario_names,
            key="scenario_selector",
        )
    with col_start:
        st.caption("")
        if st.button("▶ 开始对话", use_container_width=True, type="primary"):
            if lang_key not in SCENARIOS[selected_scenario]:
                lang_key = "en"
            role, prompt = SCENARIOS[selected_scenario][lang_key]
            st.session_state.conversation_started = True
            st.session_state.conversation_scenario = selected_scenario
            st.session_state.conversation_role = role
            st.session_state.conversation_prompt = prompt
            st.session_state.conversation_history = []
            st.session_state.conversation_error = ""
            # Generate AI's opening line
            with st.status("🤖 AI 正在准备场景…", expanded=True) as status:
                try:
                    result = converse(
                        user_message="Hello! Let's start our conversation.",
                        role=role,
                        scenario=prompt,
                        target_lang=target_lang,
                        history=None,
                    )
                    status.update(label="✅ 准备就绪", state="complete")
                except Exception as e:
                    import traceback
                    detail = f"{type(e).__name__}: {e}"
                    status.update(label=f"❌ 失败: {detail}", state="error")
                    st.session_state.conversation_error = f"LLM 调用异常: {detail}\n\n```\n{traceback.format_exc()}\n```"
                    result = {"response": f"(AI error: {e})", "corrections": []}

            st.session_state.conversation_history.append(
                {
                    "role": "assistant",
                    "content": result["response"],
                    "corrections": result.get("corrections", []),
                }
            )
            try:
                st.session_state._tts_audio_bytes = synthesize(result["response"], lang=target_lang)
            except Exception:
                st.session_state._tts_audio_bytes = None
            st.session_state._voice_key += 1
            st.rerun()
    with col_reset:
        st.caption("")
        if st.button("🔄 重置", use_container_width=True):
            st.session_state.conversation_started = False
            st.session_state.conversation_history = []
            st.session_state._tts_audio_bytes = None
            st.session_state._last_processed = ""
            st.session_state._voice_key += 1
            st.rerun()

    # 显示上一次的错误详情（跨 rerun 持久化）
    if st.session_state.get("conversation_error"):
        st.error(st.session_state.conversation_error)
        # 不清除，让用户看到完整错误；点「开始对话」或「重置」时才清除

    if not st.session_state.conversation_started:
        st.info("选择一个场景，点击「开始对话」进入角色扮演练习")
        # 显示当前 LLM 配置状态
        from app.llm_engine import config as _llm_cfg
        if _llm_cfg["api"] == "openai":
            key_preview = _llm_cfg["openai_api_key"][:10] + "..." if len(_llm_cfg["openai_api_key"]) > 5 else "(未设置)"
            st.caption(f"当前 LLM: `{_llm_cfg['api']}` | 模型: `{_llm_cfg['openai_model']}` | Key: `{key_preview}` | URL: `{_llm_cfg['openai_base_url']}`")
        else:
            st.caption(f"当前 LLM: `{_llm_cfg['api']}` | 模型: `{_llm_cfg['ollama_model']}` | URL: `{_llm_cfg['ollama_base_url']}`")
    else:
        # ── 对话信息条 ──
        st.divider()
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.markdown(f"**场景**: {st.session_state.conversation_scenario}")
            st.markdown(f"**角色**: {st.session_state.conversation_role}")
        with col_info2:
            st.markdown(f"**目标语言**: {target_lang}")
            st.caption(f"已对话 {len(st.session_state.conversation_history)} 轮")

        st.divider()

        # ── 对话历史 ──
        chat_container = st.container()
        with chat_container:
            for idx, msg in enumerate(st.session_state.conversation_history):
                if msg["role"] == "assistant":
                    with st.chat_message("assistant"):
                        st.write(msg["content"])

                        # 纠错反馈
                        if msg.get("corrections"):
                            with st.expander("📝 纠错提示"):
                                for c in msg["corrections"]:
                                    st.markdown(
                                        f"- ~~{c['original']}~~ → **{c['corrected']}**"
                                    )
                                    if c.get("explanation"):
                                        st.caption(f"  {c['explanation']}")
                else:
                    with st.chat_message("user"):
                        st.write(msg["content"])

        # ── TTS 音频播放 ──
        tts_bytes = st.session_state.get("_tts_audio_bytes")
        if tts_bytes:
            st.audio(tts_bytes, format="audio/mp3", autoplay=True)

        # ── 语音输入（Streamlit 原生录音 + Google STT 转录） ──
        audio_bytes = st.audio_input("🎤 点击说话", key=f"audio_input_{st.session_state._voice_key}")

        # ── 文字输入（键盘 fallback） ──
        st.divider()
        text_input = st.chat_input(
            f"用{target_lang}输入你的回答…（也可点击上方 🎤 说话）",
            key="conversation_input",
        )

        # ── 转录音频输入 ──
        user_text = None
        if audio_bytes is not None:
            with st.status("🎙 正在识别语音…", expanded=True) as status:
                user_text = None
                try:
                    audio_data = audio_bytes.read()
                    suffix = ".wav"
                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                        f.write(audio_data)
                        temp_path = f.name

                    recognizer = sr.Recognizer()
                    with sr.AudioFile(temp_path) as source:
                        audio = recognizer.record(source)

                    lang_code = WEB_SPEECH_LANG_MAP.get(target_lang, "en-US")

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            recognizer.recognize_google,
                            audio,
                            language=lang_code,
                        )
                        try:
                            user_text = future.result(timeout=15)
                            status.update(label=f"✅ 识别: {user_text}", state="complete")
                        except concurrent.futures.TimeoutError:
                            status.update(
                                label="⚠ Google STT 超时 — 国内需开启 VPN 才能使用",
                                state="error",
                            )
                except sr.UnknownValueError:
                    status.update(label="⚠ 无法识别语音内容，请重试", state="error")
                except sr.RequestError as e:
                    status.update(label=f"⚠ Google STT 服务不可用（需联网）: {e}", state="error")
                except Exception as e:
                    status.update(label=f"❌ 识别失败: {e}", state="error")
                finally:
                    try:
                        Path(temp_path).unlink()
                    except Exception:
                        pass

        if text_input and text_input != st.session_state.get("_last_input"):
            user_text = text_input
            st.session_state._last_input = text_input

        # ── 处理用户输入 ──
        if user_text and user_text.strip() and user_text != st.session_state.get("_last_processed"):
            st.session_state._last_processed = user_text
            st.session_state.conversation_history.append(
                {"role": "user", "content": user_text}
            )

            llm_history = [
                {"role": str(h["role"]), "content": str(h["content"])}
                for h in st.session_state.conversation_history
            ]

            with st.status("🤖 AI 正在回复…", expanded=True) as status:
                try:
                    result = converse(
                        user_message=user_text,
                        role=st.session_state.conversation_role,
                        scenario=st.session_state.conversation_prompt,
                        target_lang=target_lang,
                        history=llm_history[:-1],
                    )
                    status.update(label="✅ 完成", state="complete")
                except Exception as e:
                    import traceback
                    detail = f"{type(e).__name__}: {e}"
                    status.update(label=f"❌ 失败: {detail}", state="error")
                    st.session_state.conversation_error = f"LLM 调用异常: {detail}\n\n```\n{traceback.format_exc()}\n```"
                    result = {"response": f"(AI error: {e})", "corrections": []}

            st.session_state.conversation_history.append(
                {
                    "role": "assistant",
                    "content": result["response"],
                    "corrections": result.get("corrections", []),
                }
            )
            try:
                st.session_state._tts_audio_bytes = synthesize(result["response"], lang=target_lang)
            except Exception:
                st.session_state._tts_audio_bytes = None
            st.session_state._voice_key += 1
            st.rerun()


# ══════════════════════════════════════════════════════════════════
#  Tab 4: 设置
# ══════════════════════════════════════════════════════════════════

with tab_settings:
    st.subheader("🤖 模型配置")

    from app.llm_engine import config as llm_config

    # 初始化设置 session state —— 从当前 LLM 配置读取
    if "settings_api" not in st.session_state:
        st.session_state.settings_api = llm_config["api"]
        st.session_state.settings_model = (
            llm_config["ollama_model"] if llm_config["api"] == "ollama"
            else llm_config["openai_model"]
        )
        st.session_state.settings_base_url = (
            llm_config["ollama_base_url"] if llm_config["api"] == "ollama"
            else llm_config["openai_base_url"]
        )
        st.session_state.settings_api_key = llm_config.get("openai_api_key", "")

    # ── 后端选择 ──
    col1, col2 = st.columns(2)
    with col1:
        api_choice = st.selectbox(
            "LLM 后端",
            options=["openai", "ollama"],
            index=0 if st.session_state.settings_api == "openai" else 1,
            key="settings_api_select",
        )
        st.session_state.settings_api = api_choice
    with col2:
        # 模型快捷选择
        if api_choice == "openai":
            model_presets = {
                "DeepSeek V3": "deepseek-chat",
                "DeepSeek R1": "deepseek-reasoner",
                "GPT-4o mini": "gpt-4o-mini",
                "GPT-4o": "gpt-4o",
                "自定义": "__custom__",
            }
            default_base = "https://api.deepseek.com"
        else:
            model_presets = {
                "gemma3 (4.3B) ✓": "gemma3:4b",
                "gemma4 (8.0B)": "gemma4:latest",
                "phi3 mini (3.8B)": "phi3:mini",
                "自定义": "__custom__",
            }
            st.caption("⚠ qwen3.5 是推理模型，不适合翻译，建议用 gemma3")
            default_base = "http://localhost:11434"

        # 切换后端时自动重置 base_url、api_key 和 model
        prev_api = st.session_state.get("_prev_settings_api", "")
        if prev_api and prev_api != api_choice:
            st.session_state.settings_base_url = default_base
            st.session_state.settings_base_url_input = default_base
            st.session_state.settings_model = list(model_presets.values())[0]
            st.session_state.settings_api_key = ""
            st.session_state.settings_api_key_input = ""
        st.session_state["_prev_settings_api"] = api_choice

        preset_labels = list(model_presets.keys())
        current_model = st.session_state.settings_model
        default_idx = 0
        for i, (label, m) in enumerate(model_presets.items()):
            if m == current_model:
                default_idx = i
                break

        selected_preset = st.selectbox(
            "模型选择",
            options=preset_labels,
            index=default_idx,
            key="model_preset",
        )
        if model_presets[selected_preset] != "__custom__":
            st.session_state.settings_model = model_presets[selected_preset]

    # ── 连接参数 ──
    st.markdown("**连接参数**")
    col_a, col_b = st.columns(2)
    with col_a:
        base_url = st.text_input(
            "Base URL",
            value=st.session_state.settings_base_url
            if st.session_state.settings_api == api_choice
            else default_base,
            key="settings_base_url_input",
            placeholder=default_base,
        )
        if base_url:
            st.session_state.settings_base_url = base_url
        else:
            st.session_state.settings_base_url = default_base
    with col_b:
        if api_choice == "openai":
            api_key = st.text_input(
                "API Key",
                type="password",
                value=st.session_state.settings_api_key,
                key="settings_api_key_input",
            )
            if api_key:
                st.session_state.settings_api_key = api_key.strip()
        else:
            st.text_input("API Key", value="(无需)", disabled=True)

    # 自定义模型名
    if selected_preset == "__custom__":
        custom_model = st.text_input(
            "自定义模型名",
            value=st.session_state.settings_model,
            key="custom_model_input",
        )
        if custom_model:
            st.session_state.settings_model = custom_model

    # ── 应用配置 ──
    st.divider()
    col_apply, col_status = st.columns([1, 3])
    with col_apply:
        if st.button("✅ 应用配置", use_container_width=True, type="primary"):
            if api_choice == "openai":
                configure(
                    api="openai",
                    openai_api_key=st.session_state.settings_api_key,
                    openai_base_url=st.session_state.settings_base_url,
                    openai_model=st.session_state.settings_model,
                )
            else:
                configure(
                    api="ollama",
                    ollama_base_url=st.session_state.settings_base_url,
                    ollama_model=st.session_state.settings_model,
                )
            st.session_state.settings_saved = True

    with col_status:
        if st.session_state.get("settings_saved"):
            st.success(
                f"已生效：`{st.session_state.settings_model}` @ {st.session_state.settings_base_url}"
            )

    # ── 当前生效配置摘要 ──
    st.divider()
    st.caption("📋 当前生效配置")
    from app.llm_engine import config as llm_config

    if llm_config["api"] == "openai":
        display_model = llm_config.get("openai_model", "")
        display_url = llm_config.get("openai_base_url", "")
    else:
        display_model = llm_config.get("ollama_model", "")
        display_url = llm_config.get("ollama_base_url", "")

    st.code(
        f"LLM API  : {llm_config['api']}\n"
        f"Model    : {display_model}\n"
        f"URL      : {display_url}",
        language=None,
    )

    # ── TTS 配置 ──
    st.divider()
    st.subheader("🔊 TTS 语音配置")

    from app.tts_engine import config as tts_config

    if "settings_tts_api" not in st.session_state:
        st.session_state.settings_tts_api = tts_config["api"]
        st.session_state.settings_tts_voice_en = tts_config["edge_tts_voice_en"]
        st.session_state.settings_tts_voice_ja = tts_config["edge_tts_voice_ja"]
        st.session_state.settings_tts_voice_zh = tts_config["edge_tts_voice_zh"]

    tts_api = st.selectbox(
        "TTS 后端",
        options=["edge-tts", "gpt-sovits"],
        index=0 if st.session_state.get("settings_tts_api", tts_config["api"]) == "edge-tts" else 1,
        key="settings_tts_api",
        help="Edge-TTS: 免费在线合成，发音地道。GPT-SoVITS: 本地自定义音色。",
    )

    if tts_api == "edge-tts":
        col_en, col_ja, col_zh = st.columns(3)
        with col_en:
            voice_en = st.text_input(
                "英语音色",
                value=st.session_state.settings_tts_voice_en,
                key="settings_tts_voice_en_input",
                help="默认 en-US-AriaNeural",
            )
            if voice_en:
                st.session_state.settings_tts_voice_en = voice_en.strip()
        with col_ja:
            voice_ja = st.text_input(
                "日语音色",
                value=st.session_state.settings_tts_voice_ja,
                key="settings_tts_voice_ja_input",
                help="默认 ja-JP-NanamiNeural",
            )
            if voice_ja:
                st.session_state.settings_tts_voice_ja = voice_ja.strip()
        with col_zh:
            voice_zh = st.text_input(
                "中文音色",
                value=st.session_state.settings_tts_voice_zh,
                key="settings_tts_voice_zh_input",
                help="默认 zh-CN-XiaoxiaoNeural",
            )
            if voice_zh:
                st.session_state.settings_tts_voice_zh = voice_zh.strip()
    else:
        st.info("GPT-SoVITS 需先在本地启动 API（python api_v2.py -a 127.0.0.1 -p 9880）")

    if st.button("✅ 应用 TTS 配置", use_container_width=True, type="primary"):
        configure_tts(
            api=st.session_state.settings_tts_api,
            edge_tts_voice_en=st.session_state.settings_tts_voice_en,
            edge_tts_voice_ja=st.session_state.settings_tts_voice_ja,
            edge_tts_voice_zh=st.session_state.settings_tts_voice_zh,
        )
        st.session_state.settings_tts_saved = True

    if st.session_state.get("settings_tts_saved"):
        st.success(f"TTS 已生效：`{st.session_state.settings_tts_api}`")


# ── 直接运行入口 ──────────────────────────────────────────────────

if __name__ == "__main__":
    # streamlit run 时会自动启动，此处仅作为备用说明
    pass
