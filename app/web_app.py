"""Fluent-Agent Web UI —— Streamlit 双 Tab 界面."""

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中（streamlit run 时必需）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from app.database import add_word, delete_word, get_all_words, init_db, update_mastery
from app.llm_engine import configure, translate_and_extract

# ── 页面初始化 ────────────────────────────────────────────────────

st.set_page_config(
    page_title="Fluent-Agent 外语学习助手",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

# 首次加载时应用默认配置
if "settings_api" not in st.session_state:
    configure(
        api="openai",
        openai_api_key="sk-380b5c4ba2d641c2bd9595042c104ca9",
        openai_base_url="https://api.deepseek.com",
        openai_model="deepseek-chat",
    )


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

tab_vocab, tab_translate, tab_settings = st.tabs(
    ["📖 单词大厅", "🤖 AI 翻译助手", "⚙️ 设置"]
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
#  Tab 3: 设置
# ══════════════════════════════════════════════════════════════════

with tab_settings:
    st.subheader("🤖 模型配置")

    # 初始化设置 session state
    if "settings_api" not in st.session_state:
        st.session_state.settings_api = "openai"
        st.session_state.settings_model = "deepseek-chat"
        st.session_state.settings_base_url = "https://api.deepseek.com"
        st.session_state.settings_api_key = "sk-380b5c4ba2d641c2bd9595042c104ca9"

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
            default_key = "sk-380b5c4ba2d641c2bd9595042c104ca9"
        else:
            model_presets = {
                "Llama 3": "llama3",
                "Llama 3.1": "llama3.1",
                "Qwen 2.5": "qwen2.5",
                "Mistral": "mistral",
                "自定义": "__custom__",
            }
            default_base = "http://localhost:11434"
            default_key = ""

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
                st.session_state.settings_api_key = api_key
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

    st.code(
        f"API  : {llm_config['api']}\n"
        f"Model: {llm_config.get('openai_model') or llm_config.get('ollama_model')}\n"
        f"URL  : {llm_config.get('openai_base_url') or llm_config.get('ollama_base_url')}",
        language=None,
    )


# ── 直接运行入口 ──────────────────────────────────────────────────

if __name__ == "__main__":
    # streamlit run 时会自动启动，此处仅作为备用说明
    pass
