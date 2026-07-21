"""解析ヒント入力(F-009・#106): テンポ・キー・拍子・チューニング・カポの事前指定。

背景(X実務調査 docs/research/upcoming/F-009-grok.md より):
採譜の自動推定は失敗モードが多い。キーは同一曲でもツール間で不一致(Rekordbox/
Serato/Mixed In Key で3通り)、テンポは half/double 誤検出(体感140BPMが79BPMに
落ちる)やジャンル過学習、A=440決め打ちは基準音ずれで全体が半音側にずれる、カポ/
変則チューニングは「聴こえた音高」と「奏法表記」が衝突する。これらの領域では、
人間の事前知識をヒントとして与えることで「精度向上」というより誤った探索の
**拘束(誤推定の切断)**として効く、というのが実務の収束点である。

このモジュールの役割は狭い。音声解析はしない。ユーザーが与えたヒント値で、
既定の解析パラメータ辞書を上書きした新しい辞書を返すだけの純関数を提供する。
ヒントの取り込み口(既定 vs ユーザー指定の合成規則)を1箇所に集約することで、
テンポ/キー/拍子/チューニング/カポの扱いをパイプライン全体で一貫させる。

重要な設計原則(研究の失敗例を反映):

1. ヒントは強制ではなく補助である。None のフィールドは「指定なし」を意味し、
   既定値を維持する(推定に委ねる)。値が入っているフィールドだけを上書きする。
   自動推定を潰さないため、明示指定のみを尊重する。

2. 誤ったヒントは精度を悪化させうる(研究 3.3「自動キーをヒントにすると全ノートが
   半音/モード単位でズレる連鎖失敗」)。ヒントは信頼できる人間知識にのみ用いるべきで、
   自動推定結果を無検証でヒントとして再投入してはならない。本モジュールは値の
   「もっともらしさ」までは判定できない(音楽的正誤は音源依存)ため、範囲の妥当性
   (拍子の分子分母>0、A4 Hz>0 等)のみ境界検証し、意味的正しさは呼び出し側の責務とする。

3. カポは「音高の正誤」ではなく「記譜系の選択」の問題(研究 2.10/3.10)。ここでは
   カポ値(フレット数)を素通しで既定へ渡すのみで、sounding pitch/tab 表記の変換は
   下流(notate/tab)の責務。ここで音高を書き換えることはしない。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisHints:
    """解析ヒント: 各項目は None なら「指定なし(既定/自動推定に委ねる)」を意味する。

    フィールドはすべて任意(既定 None)。ユーザーが確信を持てる項目だけを埋め、
    残りは None のままにする使い方を想定する。値は「補助」であって「強制」ではない
    (モジュール docstring 原則1)。

    Attributes:
        tempo_bpm: テンポ(四分音符=1拍のBPM)。half/double 誤検出を人手で切るための指定。
            正の値のみ有効。
        key_tonic_pc: 主音のピッチクラス(0=C, 1=C#, ... 11=B)。キー検出のツール間
            不一致を切断するための確定値。0-11 の範囲のみ有効。
        time_sig: 拍子 (分子, 分母)。例 (4, 4), (3, 4), (7, 8)。4/4 前提を疑うための指定。
            分子・分母とも正の整数のみ有効。
        tuning_offset_cents: A=440 基準からのチューニングずれ(cents)。A≠440 の録音で
            全体が半音側にずれるのを防ぐ。0.0 も「基準ちょうど」という有効な指定。
        capo: カポ位置(フレット数, 0=カポなし)。記譜系(実音/タブ)選択のための情報で、
            音高そのものは書き換えない。0 以上の整数のみ有効。
    """

    tempo_bpm: float | None = None
    key_tonic_pc: int | None = None
    time_sig: tuple[int, int] | None = None
    tuning_offset_cents: float | None = None
    capo: int | None = None

    def __post_init__(self) -> None:
        """境界検証: 与えられた(None でない)値が物理的にありえない場合のみ弾く。

        意味的な正誤(そのキーが本当に合っているか等)は音源依存であり判定できないため
        検証しない。ここで見るのは「そもそも数値として不正」なケースだけ
        (負のBPM、範囲外のピッチクラス、非正の拍子、負のカポ)。
        """
        if self.tempo_bpm is not None and self.tempo_bpm <= 0:
            raise ValueError(f"tempo_bpm は正の値が必要です: {self.tempo_bpm}")
        if self.key_tonic_pc is not None and not (0 <= self.key_tonic_pc <= 11):
            raise ValueError(
                f"key_tonic_pc は 0-11 のピッチクラスが必要です: {self.key_tonic_pc}"
            )
        if self.time_sig is not None:
            num, den = self.time_sig
            if num <= 0 or den <= 0:
                raise ValueError(f"time_sig は正の (分子, 分母) が必要です: {self.time_sig}")
        if self.capo is not None and self.capo < 0:
            raise ValueError(f"capo は 0 以上のフレット数が必要です: {self.capo}")


# ヒントのフィールド名 → 既定辞書側のキー名の対応表。
# パイプラインの解析パラメータ辞書とヒントの語彙を1箇所で結びつける。
_HINT_TO_DEFAULT_KEY: dict[str, str] = {
    "tempo_bpm": "tempo_bpm",
    "key_tonic_pc": "key_tonic_pc",
    "time_sig": "time_sig",
    "tuning_offset_cents": "tuning_offset_cents",
    "capo": "capo",
}


def apply_hints(hints: AnalysisHints, defaults: dict) -> dict:
    """ヒントで既定の解析パラメータ辞書を上書きした新しい辞書を返す(純関数)。

    上書き規則(モジュール docstring 原則1):
      - hints のフィールドが None でない場合のみ、対応する既定キーを上書きする。
      - None のフィールドは「指定なし」なので既定値をそのまま維持する
        (既定に該当キーが無ければ、上書きもしないので追加もされない)。
      - defaults は変更しない(immutable 原則)。新しい dict を返す。

    ヒントは補助であり強制ではない。誤ったヒントは推定を悪化させうる(研究 3.3)ため、
    ここで受け取るのは信頼できる人間知識であることを呼び出し側が保証する。本関数は
    値の意味的正誤は判定せず、AnalysisHints の境界検証(生成時 __post_init__)のみに依存する。

    Args:
        hints: 適用するヒント。None フィールドは既定を維持する。
        defaults: 既定の解析パラメータ辞書(破壊しない)。

    Returns:
        ヒントを反映した新しい辞書(defaults の浅いコピー + 指定フィールドの上書き)。
    """
    merged = dict(defaults)  # 浅いコピー: defaults を破壊しない(immutable原則)
    for field_name, default_key in _HINT_TO_DEFAULT_KEY.items():
        value = getattr(hints, field_name)
        if value is not None:
            merged[default_key] = value
    return merged
