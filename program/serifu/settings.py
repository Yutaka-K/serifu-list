"""設定.ini を読み込む部分。"""
from __future__ import annotations

import configparser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

YES_WORDS = {"はい", "yes", "y", "true", "1", "on", "する", "含める", "付ける", "○"}
NO_WORDS = {"いいえ", "no", "n", "false", "0", "off", "しない", "含めない", "付けない", "×"}


class SettingsError(Exception):
    """設定ファイルの書き方がおかしいときのエラー。"""


@dataclass
class Settings:
    script_format: str = "4コマ"
    panels_per_unit: int = 4
    max_chars: int = 30
    check_se_length: bool = False
    text_include_se: bool = False
    text_show_speaker: bool = False
    text_show_empty_panels: bool = False
    kind_names: Dict[str, str] = field(
        default_factory=lambda: {"心": "心の声", "モ": "モノローグ", "寝言": "寝言"}
    )
    se_speakers: List[str] = field(default_factory=lambda: ["SE", "効果音"])


def _to_bool(value: str, key: str) -> bool:
    v = value.strip().lower()
    if v in YES_WORDS:
        return True
    if v in NO_WORDS:
        return False
    raise SettingsError(f"設定「{key}」には「はい」か「いいえ」を書いてください（今は「{value}」になっています）。")


def _to_int(value: str, key: str) -> int:
    import unicodedata

    v = unicodedata.normalize("NFKC", value).strip()
    try:
        n = int(v)
    except ValueError:
        raise SettingsError(f"設定「{key}」には数字を書いてください（今は「{value}」になっています）。") from None
    if n < 0:
        raise SettingsError(f"設定「{key}」には0以上の数字を書いてください。")
    return n


def load_settings(path: Path) -> Settings:
    """設定ファイルを読む。ファイルがなければ初期設定を使う。"""
    s = Settings()
    if not path.exists():
        print(f"※ 設定ファイル「{path.name}」が見つからないので、初期設定で動かします。")
        return s

    cp = configparser.ConfigParser(comment_prefixes=(";", "#"), inline_comment_prefixes=None)
    cp.optionxform = str  # 項目名の大文字・小文字をそのままにする
    try:
        # メモ帳で保存したときの BOM 付き UTF-8 や、古い Shift_JIS にも対応
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            text = path.read_text(encoding="cp932")
        cp.read_string(text)
    except configparser.Error as e:
        raise SettingsError(f"設定ファイルの書き方が読めません：{e}") from None

    if cp.has_section("設定"):
        sec = cp["設定"]
        if "台本の形式" in sec:
            s.script_format = sec["台本の形式"].strip()
        if "1本あたりのコマ数" in sec:
            s.panels_per_unit = _to_int(sec["1本あたりのコマ数"], "1本あたりのコマ数")
        if "文字数の上限" in sec:
            s.max_chars = _to_int(sec["文字数の上限"], "文字数の上限")
        bools = {
            "効果音も文字数チェックする": "check_se_length",
            "テキストに効果音を含める": "text_include_se",
            "テキストに話者名を付ける": "text_show_speaker",
            "テキストに台詞なしのコマも書く": "text_show_empty_panels",
        }
        for key, attr in bools.items():
            if key in sec:
                setattr(s, attr, _to_bool(sec[key], key))

    if cp.has_section("種類の略号"):
        names = {k.strip(): v.strip() for k, v in cp["種類の略号"].items() if k.strip()}
        if names:
            s.kind_names = names

    if cp.has_section("効果音の話者名") and "名前" in cp["効果音の話者名"]:
        raw = cp["効果音の話者名"]["名前"]
        for sep in [",", "，", "/", "／", " ", "　"]:
            raw = raw.replace(sep, "、")
        names = [n.strip() for n in raw.split("、") if n.strip()]
        if names:
            s.se_speakers = names

    return s
