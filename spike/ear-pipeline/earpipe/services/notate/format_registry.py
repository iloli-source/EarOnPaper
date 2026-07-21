"""F-104 プラグイン型出力形式の登録簿(NF-045・Issue #101)。

採譜の出力層は「全形式をコアに直書き」ではなく、**登録簿に載った
``OutputFormat`` を介して形式を追加する**プラグイン設計を採る。コア
(pipeline)を改修せず、この登録簿に1エントリ追加するだけで新しい出力
形式を公開できる。実際のシリアライズは既存の各エクスポータ
(score/jianpu/leadsheet/guitarpro_export/vocal_synth_export/llm_export/
tab/engrave 等)が担い、本モジュールは**何をどの用途で出せるかのメタ情報**
のみを保持する。

先行研究(docs/research/upcoming/F-104-grok.md)からの反映:

- 「全形式対応」はチェックボックス機能ではなく lossy な現実を前提とした
  エクスポート・プラットフォーム問題。よって各形式は ``lossy`` フラグと
  ``lossy_note``(何が失われるか)を正直に持つ。lossy を隠さない。
- 記譜法(五線/タブ/簡譜/ABC/LilyPond)とファイル容器(MusicXML/MIDI/PDF)は
  役割が違う。両者を ``kind`` で分離し、混同(記譜が欲しいのに MIDI だけ、等)
  を避ける。
- コアに無い方言記譜を「対応済み」と誤認しない。各エントリの ``status`` で
  実装の成熟度を明示し、宣伝と実装の乖離を UI 層が扱えるようにする。

本モジュールは純粋なメタデータ登録簿であり、外部依存を一切追加しない。
"""

from dataclasses import dataclass
from typing import Literal

# 出力の分類(記譜法方言 vs ファイル容器 vs 演奏データ)。
# grok研究の「記譜法とファイル形式は役割が違う」を型で分離する。
FormatKind = Literal[
    "notation_container",  # 記譜交換用の容器(MusicXML等)。論理構造を運ぶ
    "performance",         # 演奏再現用(MIDI/UST等)。タイミング・音高を運ぶ
    "engraving",           # 配布・印刷用の組版出力(PDF/SVG)。レイアウトが正
    "notation_dialect",    # 地域/軽量記譜の方言(簡譜/タブ/ABC/LilyPond/リード)
    "tablature",           # 撥弦楽器タブ譜(GP5/タブPDF)
]

# 実装の成熟度。宣伝と実装の乖離(研究2.4/2.5)を隠さないための正直タグ。
FormatStatus = Literal[
    "stable",       # 既存エクスポータで実装・テスト済み
    "approx",       # テキスト近似等、厳密な組版ではない(限界あり)
    "experimental",  # 実装はあるが検証が薄い
]


@dataclass(frozen=True)
class OutputFormat:
    """単一の出力形式を記述する不変メタデータ(登録簿の1エントリ)。

    Attributes:
        key: 一意な機械可読キー(小文字英数と ``_``)。API/CLI の識別子。
        label: 人間可読の表示名。
        ext: 出力ファイル拡張子(先頭ドットなし。例 ``"musicxml"``)。
            テキスト系方言でファイルを持たない場合も代表拡張子を持つ。
        kind: 出力の分類(記譜容器/演奏/組版/方言/タブ)。
        lossy: 内部IRからの変換で情報欠落が起きうるか。
            研究の「MusicXMLは lossy intermediary」を踏まえ正直に持つ。
        lossy_note: lossy の場合に主に失われるものの短い説明(空文字可)。
        producer: 実際のシリアライズを担う既存エクスポータの識別子
            (配線の手掛かり。例 ``"score.write_musicxml"``)。
        status: 実装の成熟度(stable/approx/experimental)。
    """

    key: str
    label: str
    ext: str
    kind: FormatKind
    lossy: bool
    lossy_note: str
    producer: str
    status: FormatStatus


# プラグイン型出力層の登録簿(NF-045)。
# 新形式はここに1エントリ追加するだけで公開される(コア改修不要)。
# lossy_note は研究の失敗パターン(A:レイアウト損失 / B:記号損失 /
# C:リズム崩壊 / D:再生専用情報 / F:方言MIDI / G:記譜法方言)を反映した
# 「何が失われるか」の正直な明示。
FORMAT_REGISTRY: tuple[OutputFormat, ...] = (
    OutputFormat(
        key="musicxml",
        label="MusicXML",
        ext="musicxml",
        kind="notation_container",
        lossy=True,
        lossy_note="論理構造は保つが物理レイアウト・アーティキュレーション・"
        "強弱は実装差で欠落しうる(lossy intermediary)",
        producer="score.write_musicxml",
        status="stable",
    ),
    OutputFormat(
        key="midi",
        label="Standard MIDI",
        ext="mid",
        kind="performance",
        lossy=True,
        lossy_note="演奏タイミング・音高は保つが記譜記号・声部・"
        "スペリングは失われる(演奏用であり記譜用ではない)",
        producer="score.write_midi",
        status="stable",
    ),
    OutputFormat(
        key="midi_raw",
        label="Raw MIDI (unquantized)",
        ext="mid",
        kind="performance",
        lossy=True,
        lossy_note="実タイミングを保持するが量子化前のため小節・拍構造を持たない",
        producer="score.write_midi_raw",
        status="stable",
    ),
    OutputFormat(
        key="pdf",
        label="Engraved PDF",
        ext="pdf",
        kind="engraving",
        lossy=True,
        lossy_note="配布用の最終組版。再編集用の論理情報は保持しない(画面表示が正)",
        producer="engrave.write_pdf",
        status="stable",
    ),
    OutputFormat(
        key="tab_pdf",
        label="Guitar Tablature PDF",
        ext="pdf",
        kind="tablature",
        lossy=True,
        lossy_note="フレット位置は保つが運指の別解・微細な奏法表現は正規化される",
        producer="tab.write_tab_pdf",
        status="stable",
    ),
    OutputFormat(
        key="jianpu",
        label="Jianpu (簡譜/数字譜)",
        ext="txt",
        kind="notation_dialect",
        lossy=True,
        lossy_note="テキスト近似であり厳密な簡譜組版ではない(音価は近似)",
        producer="jianpu.to_jianpu",
        status="approx",
    ),
    OutputFormat(
        key="leadsheet",
        label="Lead Sheet (コード+メロディ)",
        ext="txt",
        kind="notation_dialect",
        lossy=True,
        lossy_note="コード進行と旋律骨格のみ。内声・細かい記譜記号は落ちる",
        producer="leadsheet.to_leadsheet",
        status="approx",
    ),
    OutputFormat(
        key="gp5",
        label="Guitar Pro 5",
        ext="gp5",
        kind="tablature",
        lossy=True,
        lossy_note="タブ/フレットは保つがベンド・ポルタメント等の連続変化は近似"
        "(研究2.3のGP MIDI往復失敗に留意)",
        producer="guitarpro_export.write_guitarpro",
        status="stable",
    ),
    OutputFormat(
        key="ust",
        label="UTAU Sequence (UST)",
        ext="ust",
        kind="performance",
        lossy=True,
        lossy_note="単声のみ。歌詞・ビブラート/スクープは統合・近似される",
        producer="vocal_synth_export.to_ust",
        status="approx",
    ),
    OutputFormat(
        key="abc",
        label="ABC Notation",
        ext="abc",
        kind="notation_dialect",
        lossy=True,
        lossy_note="軽量テキスト記譜。レイアウト・複雑な記号は表現しない"
        "(巨大XMLの対極としての軽量表現)",
        producer="llm_export.to_llm_text",
        status="approx",
    ),
    OutputFormat(
        key="lilypond",
        label="LilyPond",
        ext="ly",
        kind="notation_dialect",
        lossy=True,
        lossy_note="組版言語ソース。内部IRの一部記号はソースに落とし込む際に近似",
        producer="engrave.render_svg_pages",
        status="experimental",
    ),
)


def available_formats() -> list[OutputFormat]:
    """公開中の全出力形式を登録順で返す。

    返るリストは登録簿の防御的コピー(新規list)であり、呼び出し側が
    変更してもモジュール状態(``FORMAT_REGISTRY``)は不変(coding-style:
    immutability)。

    Returns:
        ``OutputFormat`` のリスト(``FORMAT_REGISTRY`` と同順)。
    """
    return list(FORMAT_REGISTRY)


def get_format(key: str) -> OutputFormat:
    """キーから出力形式メタデータを取得する。

    Args:
        key: 取得する形式の一意キー(例 ``"musicxml"``)。

    Returns:
        該当する ``OutputFormat``。

    Raises:
        KeyError: ``key`` に対応する形式が登録されていない場合。
            利用可能キー一覧をメッセージに含める(早期・明示的失敗)。
    """
    for fmt in FORMAT_REGISTRY:
        if fmt.key == key:
            return fmt
    known = ", ".join(f.key for f in FORMAT_REGISTRY)
    raise KeyError(f"未登録の出力形式キー: {key!r}(利用可能: {known})")
