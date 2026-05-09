"""Fluent-Agent —— 外语学习助手入口."""

from app.database import init_db, add_word, get_all_words, update_mastery, delete_word, search_words
from app.translate_tool import run_translate_flow


def print_word_list(words: list[dict]) -> None:
    if not words:
        print("  (暂无生词)")
        return
    print(f"  {'ID':<5} {'单词':<20} {'翻译':<20} {'掌握度':<8} {'来源':<12} {'添加时间'}")
    print("  " + "-" * 90)
    for w in words:
        print(
            f"  {w['id']:<5} {w['word']:<20} {w['translation']:<20} "
            f"{w['mastery']}/{'5':<5} {w['source']:<12} {w['created_at']}"
        )


def cmd_add() -> None:
    print("\n[添加生词]")
    word = input("  单词: ").strip()
    if not word:
        print("  单词不能为空，已取消。")
        return
    translation = input("  翻译: ").strip()
    if not translation:
        print("  翻译不能为空，已取消。")
        return
    context = input("  原文语境 (可选): ").strip()
    source = input("  来源 (可选，如书名/文章名): ").strip()
    raw = input("  掌握程度 (0-5, 默认0): ").strip()
    try:
        mastery = int(raw) if raw else 0
        mastery = max(0, min(5, mastery))
    except ValueError:
        mastery = 0

    word_id = add_word(word, translation, context, source, mastery)
    print(f"  已添加，ID={word_id}")


def cmd_list() -> None:
    print("\n[全部生词]")
    print_word_list(get_all_words())


def cmd_search() -> None:
    keyword = input("\n[搜索] 输入关键词: ").strip()
    if not keyword:
        return
    print_word_list(search_words(keyword))


def cmd_update() -> None:
    raw_id = input("\n[更新掌握度] 输入生词ID: ").strip()
    try:
        word_id = int(raw_id)
    except ValueError:
        print("  ID无效。")
        return
    raw = input("  新掌握度 (0-5): ").strip()
    try:
        mastery = int(raw)
        mastery = max(0, min(5, mastery))
    except ValueError:
        print("  数值无效。")
        return
    if update_mastery(word_id, mastery):
        print("  已更新。")
    else:
        print("  未找到该ID。")


def cmd_delete() -> None:
    raw_id = input("\n[删除生词] 输入生词ID: ").strip()
    try:
        word_id = int(raw_id)
    except ValueError:
        print("  ID无效。")
        return
    if delete_word(word_id):
        print("  已删除。")
    else:
        print("  未找到该ID。")


def main() -> None:
    init_db()
    print("=" * 50)
    print("  Fluent-Agent 外语学习助手")
    print("=" * 50)

    menu = {
        "1": ("AI 翻译+提取生词", lambda: run_translate_flow()),
        "2": ("手动添加生词", cmd_add),
        "3": ("查看全部生词", cmd_list),
        "4": ("搜索生词", cmd_search),
        "5": ("更新掌握度", cmd_update),
        "6": ("删除生词", cmd_delete),
        "0": ("退出", None),
    }

    while True:
        print("\n" + "=" * 50)
        for key, (label, _) in menu.items():
            print(f"  [{key}] {label}")
        choice = input("  请选择: ").strip()

        if choice == "0":
            print("  再见！")
            break
        if choice in menu:
            menu[choice][1]()
        else:
            print("  无效选项，请重试。")


if __name__ == "__main__":
    main()
