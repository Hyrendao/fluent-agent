"""AI 翻译 + 生词提取 + 入库流程."""

from app.database import add_word
from app.llm_engine import translate_and_extract


def run_translate_flow(source_text: str | None = None) -> None:
    """交互式翻译 → 展示结果 → 询问是否保存生词。"""
    if not source_text:
        source_text = input("\n  请输入要翻译的文本: ").strip()
    if not source_text:
        print("  文本为空，已取消。")
        return

    print("\n  ⏳ 正在调用 AI 翻译并提取生词...")
    try:
        result = translate_and_extract(source_text)
    except Exception as e:
        print(f"  ❌ AI 调用失败: {e}")
        return

    translation = result.get("translation", "")
    words = result.get("words", [])

    print(f"\n  📝 翻译结果:\n  {'─' * 40}\n  {translation}\n  {'─' * 40}")

    if not words:
        print("\n  (AI 未提取到生词)")
        return

    print(f"\n  📚 建议学习的生词 ({len(words)} 个):")
    for i, w in enumerate(words, 1):
        print(f"  [{i}] {w['word']}")
        print(f"      释义: {w['translation']}")
        print(f"      例句: {w['example']}")
        print()

    choice = input("  是否将以上生词存入数据库？(y/n): ").strip().lower()
    if choice not in ("y", "yes"):
        print("  已跳过保存。")
        return

    source = input("  来源标注 (可选): ").strip()
    saved = 0
    for w in words:
        try:
            add_word(
                word=w["word"],
                translation=w["translation"],
                context=w["example"],
                source=source,
                mastery=0,
            )
            saved += 1
        except Exception as e:
            print(f"  ⚠ 保存 '{w['word']}' 失败: {e}")

    print(f"  已保存 {saved}/{len(words)} 个生词。")
