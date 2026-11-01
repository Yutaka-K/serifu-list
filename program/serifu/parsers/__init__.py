"""台本の読み取り部分（パーサー）のまとめ役。

台本の形式ごとに、読み取り用のファイルを1つ用意します。
  - yonkoma.py … 4コマ漫画の台本（「### 01「タイトル」」＋「コマ｜絵｜台詞・音」の表）

■ 新しい形式（例：ページ単位の台本）に対応したいとき
  1. このフォルダに新しいファイル（例：page.py）を作る
  2. その中に parse(text, path, settings) という関数を作り、
     models.py の Script（本＝ページ、コマ、台詞）を返すようにする
  3. 下の PARSERS に「"ページ": page.parse,」のように1行追加する
  4. 設定.ini の「台本の形式」を「ページ」にする
  チェックや Excel・テキストの出力は、そのまま使えます。
"""
from __future__ import annotations

from typing import Callable, Dict

from . import yonkoma

PARSERS: Dict[str, Callable] = {
    "4コマ": yonkoma.parse,
}


def get_parser(name: str) -> Callable:
    try:
        return PARSERS[name]
    except KeyError:
        choices = "、".join(f"「{k}」" for k in PARSERS)
        raise ValueError(
            f"設定「台本の形式」の「{name}」には対応していません。使えるのは {choices} です。"
        ) from None
