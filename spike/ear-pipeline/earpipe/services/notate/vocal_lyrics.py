"""F-020 歌声採譜・歌詞同期 — 音節→音符割当(メリスマ含む・Issue #96)。

`align_lyrics(notes, syllables)` は歌詞の音節列を音符列へ「順次」割り当て、
余った音符を直前音節の伸ばし(メリスマ)として明示的に保持する。返すのは
音符ごとの割当レコード list[dict]{note_index, syllable, melisma}。

設計方針(先行研究 F-020-grok / F-020-codex の失敗例を保守的に反映):
- 「1 syllable = 1 note」は成立しない(codex 1.2 / grok 3.8)。1音節が複数音符に
  伸びるメリスマを第一級構造として保持する。よって割当は「音節を音符へ順に流し、
  音符が余ったら直前音節の melisma 継続」とし、音節を音符数へ機械的に潰さない。
- 「word/syllable boundary ⇒ note boundary」は成立するが逆は成立しないという
  非対称制約(ROSVOT・codex 1.2)を素直にコード化する。すなわち各音節は必ず
  「新しい音符境界」で始まり(melisma=False)、同一音節内の追加音符は
  melisma=True(継続)として区別する。音符境界が音節境界を含意しない
  (=1音節が複数音符)ケースだけを許し、逆(1音符に複数音節の凝縮)は
  この順次モデルでは表現しない — その限界は本 docstring 末尾に明記。
- 完全自動の一発確定を主張しない(grok 9章「勝ち筋はフル自動でなく手直しループ」)。
  本関数は forced alignment(音響同期)を行わず、音符列の「順序」だけを根拠に
  音節を流し込む純ヒューリスティックである。同期誤差(AlER・codex 1.4)は評価せず、
  結果は人手修正の下書きとして扱う前提。
- 音節数 > 音符数(音符不足)でも黙って音節を捨てない。割り当てられなかった
  余剰音節は unassigned_syllables として返り値のメタには残せないが(戻り値は
  音符単位の list 契約)、本モジュールは `count_unassigned` を別途提供し、
  呼び出し側が取りこぼしを検知できるようにする(grok BP6「手動編集口を残す」)。

限界(正直な記録・過大主張しない):
- 音響同期をしない。実際の歌唱タイミング(onset_sec/母音伸縮・休符・間奏・掛け声、
  codex 1.3)とは無関係に、音符 list の並び順のみで割り当てる。長尺のドリフト
  (grok 3.4 / itshanrw の3分問題)や間奏での境界ずれは本モジュールでは検知不能。
- 「1音符に複数音節が凝縮」(grok 3.8 の逆メリスマ)は表現しない。1音符=最大1音節。
- 音節分割そのものは行わない。呼び出し側が音節単位で syllables を渡す前提
  (英語の音節境界・日本語モーラ・中国語音節などの言語依存分割は上流責務)。
- メリスマ/非メリスマの「本当の」境界(codex 1.1 のビブラート vs 意図的音高変化)は
  判定しない。ここでは「音節が尽きた後の音符はすべて直前音節のメリスマ」という
  最も保守的な規則に倒す。過剰メリスマ素材(grok 失敗カタログ11)で音符が爆発しても
  音節を無理に増やさない。
- AMNLT の Alignment Error Rate(codex 1.4 / 文献15)相当の評価は本モジュール範囲外。
"""

from __future__ import annotations

from earpipe.contracts import QuantizedNote

# メリスマ継続音符に割り当てる音節文字列(直前音節の伸ばしであることを表す代理表記)。
# 空文字ではなく明示トークンにすることで、下流(記譜/歌詞下敷き)が「新規音節ではない
# 継続部」であることを melisma フラグと二重に判別できる。
MELISMA_CONTINUATION = "-"


def _clean_syllables(syllables: list[str]) -> list[str]:
    """音節列を正規化する。

    先行研究(grok 3.6 / 3.9)より「悪い転写・空白・空音節」が実務の常態。
    None・非文字列を弾き、前後空白を除去し、除去後に空になった要素は
    「割り当てるべき実体がない」ものとして落とす。順序は保持(不変・新list)。
    """
    cleaned: list[str] = []
    for item in syllables:
        if not isinstance(item, str):
            continue
        stripped = item.strip()
        if stripped == "":
            continue
        cleaned.append(stripped)
    return cleaned


def align_lyrics(
    notes: list[QuantizedNote],
    syllables: list[str],
) -> list[dict]:
    """音節を音符へ順次割り当て、余剰音符をメリスマとして返す。

    音符 list の並び順を旋律順(=歌唱順)とみなし、先頭から音節を1つずつ
    割り当てる。音節が尽きた後の残り音符は、直前に割り当てた音節の伸ばし
    (メリスマ)として melisma=True で継続させる。音符より前に音節が尽きても
    音節を捨てず、音符の続く限りメリスマで吸収する。

    Args:
        notes: 量子化済み音符列(QuantizedNote)。並び順を旋律順として信頼する
            (onset_sec は NaN 既定でソート根拠に使えない。contracts.py 参照)。
        syllables: 音節文字列の列。空白・空音節は除去し、実体のある音節のみ扱う。
            音節分割自体は行わない(上流責務)。

    Returns:
        音符と同数の割当レコード list[dict]。各要素は:
          - note_index (int): notes 内のインデックス(0起点)
          - syllable (str): 割り当てた音節。メリスマ継続音符は MELISMA_CONTINUATION
          - melisma (bool): True=直前音節の継続(メリスマ)、False=新規音節の頭
        音節が1つも無い(または全て空)の場合、全音符 syllable="" / melisma=False。
        notes が空なら空 list を返す。
    """
    clean = _clean_syllables(syllables)

    records: list[dict] = []
    syllable_cursor = 0
    last_syllable: str | None = None

    for note_index in range(len(notes)):
        if syllable_cursor < len(clean):
            # まだ割り当てる音節が残っている: 新しい音節の頭(境界)。
            current = clean[syllable_cursor]
            records.append(
                {"note_index": note_index, "syllable": current, "melisma": False}
            )
            last_syllable = current
            syllable_cursor += 1
        elif last_syllable is not None:
            # 音節は尽きたが音符が残る: 直前音節のメリスマ継続。
            records.append(
                {
                    "note_index": note_index,
                    "syllable": MELISMA_CONTINUATION,
                    "melisma": True,
                }
            )
        else:
            # 音節が最初から皆無(空 or 全空白): 歌詞なしとして空割当。
            records.append(
                {"note_index": note_index, "syllable": "", "melisma": False}
            )

    return records


def count_unassigned(
    notes: list[QuantizedNote],
    syllables: list[str],
) -> int:
    """割り当てきれなかった余剰音節数を返す(音符不足の検知)。

    音節数 > 音符数のとき、`align_lyrics` は音符数を超える音節を出力に含められない。
    取りこぼしを呼び出し側が検知できるよう、あふれた音節数を別途返す
    (grok BP6「手動編集口・取りこぼし可視化を常に残す」)。空白・空音節は
    除去後にカウントする。0 なら全音節が割当済み。
    """
    clean = _clean_syllables(syllables)
    overflow = len(clean) - len(notes)
    return overflow if overflow > 0 else 0
