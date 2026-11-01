"""セリフ一覧作成ツールの本体。

使い方（ふだんは「セリフ一覧作成.bat」から動かします）：
    python program/run.py                 … 「入力」フォルダの台本（.md）をすべて処理
    python program/run.py 台本.md ...      … 指定した台本だけを処理
"""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # ツールのフォルダ
sys.path.insert(0, str(Path(__file__).resolve().parent))

from serifu.checks import run_checks  # noqa: E402
from serifu.parsers import get_parser  # noqa: E402
from serifu.settings import SettingsError, load_settings  # noqa: E402

INPUT_DIR = ROOT / "入力"
OUTPUT_DIR = ROOT / "出力"
SETTINGS_FILE = ROOT / "設定.ini"


def read_script_text(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp932"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    raise ValueError("文字コードが読めません。台本を「UTF-8」で保存し直してください。")


def collect_files(args) -> list:
    """処理する台本ファイルの一覧を作る。"""
    files = []
    if args:
        for a in args:
            p = Path(a)
            if p.is_dir():
                found = sorted(p.glob("*.md"))
                if not found:
                    print(f"※ フォルダ「{p.name}」の中に .md ファイルがありません。")
                files.extend(found)
            elif not p.exists():
                print(f"※ ファイル「{a}」が見つかりません。とばします。")
            elif p.suffix.lower() != ".md":
                print(f"※「{p.name}」は .md ファイルではないので、とばします。")
            else:
                files.append(p)
    else:
        INPUT_DIR.mkdir(exist_ok=True)
        files = sorted(INPUT_DIR.glob("*.md"))
        if not files:
            print("「入力」フォルダに台本（.md ファイル）がありません。")
            print(f"  入力フォルダの場所：{INPUT_DIR}")
            print("  台本を入れてから、もう一度実行してください。")
    return files


def process(path: Path, settings, out_dir: Path) -> int:
    """台本1つを処理して、警告の件数を返す。"""
    from serifu.writers import write_excel, write_problems, write_text

    print(f"■ {path.name}")
    text = read_script_text(path)
    parser = get_parser(settings.script_format)
    script = parser(text, path, settings)
    problems = sorted(script.problems, key=lambda p: p.line_no or 0) + run_checks(script, settings)

    out_dir.mkdir(parents=True, exist_ok=True)
    xlsx = out_dir / f"{script.name}_セリフ一覧.xlsx"
    txt = out_dir / f"{script.name}_セリフ一覧.txt"
    warn = out_dir / f"{script.name}_警告.txt"
    for target, writer in ((xlsx, lambda: write_excel(script, problems, xlsx)),
                           (txt, lambda: write_text(script, settings, txt)),
                           (warn, lambda: write_problems(script, problems, warn))):
        try:
            writer()
        except PermissionError:
            raise PermissionError(
                f"「{target.name}」に書き込めません。Excel やメモ帳で開いたままになっていませんか？"
                "閉じてから、もう一度実行してください。"
            ) from None

    n_panels = sum(len(u.panels) for u in script.units)
    all_lines = [l for _, _, l in script.all_lines()]
    n_se = sum(1 for l in all_lines if l.is_se)
    print(f"  読み取り結果：{len(script.units)}本・{n_panels}コマ・"
          f"台詞 {len(all_lines) - n_se}件・効果音 {n_se}件")
    print(f"  出力しました：{xlsx.name}／{txt.name}／{warn.name}")
    if problems:
        print(f"  ▲ 警告が {len(problems)} 件あります：")
        for p in problems:
            print("    ・" + p.to_text().replace("\n", "\n    "))
    else:
        print("  ◎ 警告はありません。")
    print()
    return len(problems)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="漫画の台本（Markdown）から写植用のセリフ一覧を作ります。")
    ap.add_argument("files", nargs="*", help="処理する台本ファイル（省略すると「入力」フォルダの全部）")
    ap.add_argument("--out", help="出力先のフォルダ（省略すると「出力」フォルダ）")
    ap.add_argument("--settings", help="設定ファイル（省略すると「設定.ini」）")
    args = ap.parse_args(argv)

    try:
        import openpyxl  # noqa: F401
    except ImportError:
        print("【エラー】Excel を作るためのライブラリ（openpyxl）が入っていません。")
        print("  先に「初回セットアップ.bat」をダブルクリックして実行してください。")
        return 1

    try:
        settings = load_settings(Path(args.settings) if args.settings else SETTINGS_FILE)
        get_parser(settings.script_format)
    except (SettingsError, ValueError) as e:
        print(f"【エラー】設定.ini の内容に問題があります：\n  {e}")
        return 1

    print("=" * 50)
    print(" セリフ一覧作成ツール")
    print("=" * 50)
    print(f"設定：文字数の上限 {settings.max_chars}文字／1本 {settings.panels_per_unit}コマ／"
          f"テキストに効果音を{'含める' if settings.text_include_se else '含めない'}")
    print()

    files = collect_files(args.files)
    if not files:
        return 1

    out_dir = Path(args.out) if args.out else OUTPUT_DIR
    ok, failed, warn_total = 0, 0, 0
    for f in files:
        try:
            warn_total += process(f, settings, out_dir)
            ok += 1
        except Exception as e:  # 1つ失敗しても、ほかの台本は続けて処理する
            failed += 1
            print(f"  【エラー】この台本は処理できませんでした：{e}")
            if not isinstance(e, (PermissionError, ValueError)):
                print("  ---- くわしい情報（困ったときはこの部分を見せてください） ----")
                print("  " + traceback.format_exc().replace("\n", "\n  "))
            print()

    print("=" * 50)
    print(f"完了：{ok}件の台本を処理しました。", end="")
    if failed:
        print(f"（{failed}件はエラーで処理できませんでした）", end="")
    print()
    print(f"警告：合計 {warn_total} 件")
    print(f"結果は「{out_dir}」フォルダにあります。")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        code = main()
    except KeyboardInterrupt:
        print("\n中断しました。")
        code = 1
    except Exception:
        print("【エラー】思わぬエラーが起きました。")
        print("---- くわしい情報（困ったときはこの部分を見せてください） ----")
        traceback.print_exc()
        code = 1
    sys.exit(code)
