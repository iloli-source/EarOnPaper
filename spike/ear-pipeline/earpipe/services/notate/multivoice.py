"""F-019 多声部一括採譜の声部分離(skyline+下声のヒューリスティック分割)。

量子化済み音符列を、音高と時間的連続性にもとづき小編成(2〜3声部)へ分割する。
上声(skyline=各時刻の最高音)を第1声部の骨格とし、残りの同時発音を音高順・
連続性優先で下声へ割り当てる。真の音源分離・音源同定はしない=これは
「編集可能な下書き」を作るための粗い記譜補助であって、混合バンド音源から
正しいフルスコアを確実に生成するものではない。

本モジュールは music21 非依存で、QuantizedNote の格子側フィールド
(start_beats/dur_beats/midi)のみを用いる純算術で完結する
(重依存追加禁止・テスト容易・軽量。scale_cleanse.py / density.py と同方針)。

設計方針(先行研究 F-019-grok.md / F-019-codex.md の失敗例を回帰対策として反映):
- 過大主張しない(grok §5.1 / codex §9): 出力は「声部分けの下書き」であって
  完成スコアではない。声部分離の独立検証済み成功例はほぼ存在しない
  (codex エグゼクティブサマリー)ため、本実装は「決定的で説明可能な粗い割当」に
  徹し、賢さではなく再現性・非破壊性・限界の明示を優先する。
- 同音衝突は分けない(codex §4.3 / grok 失敗4): 2楽器が同じ MIDI を同時に鳴らす
  場合、音声上そもそも2音へ分ける証拠が無い(Melodyne の単一blob問題)。本実装も
  同一 start_beats・同一 midi の重複は1音に統合し、幻の声部を捏造しない。
- 声部間ジャンプ最小化(grok 失敗C「メロディが楽器間を飛ぶ」への緩和): 各声部は
  直近に割り当てた音との音高差が小さい音を優先して引き継ぎ、声部内の連続性を保つ。
  ただし音色情報は無い(codex §4.4)ため、同レジスタの交差では誤りうる(限界)。
- skyline を上声の代理に(grok/codex とも「skyline は主旋律の粗い代理」): 内声主題や
  バスが主役の曲では上声保護が誤る。これは単一 pitch 軸の原理的限界であり、
  本実装では「上声=最高音」と割り切って明示する。
- 非破壊・不変(density.py と同じ): 入力音符インスタンスは改変せず、声部ごとの
  新規 list へ振り分けるのみ。timing/pitch/duration は一切変えない。

限界(正直な記録・過大主張しない):
- max_voices は 2〜3 のみ対応(小編成限定)。4声部以上・フルオーケストラは対象外。
  同時発音が max_voices を超える塊は、超過分を最寄り声部へ畳み込む(声部内で
  複数音=和音になりうる)。これは「フルスコアの正しい声部割当」ではない。
- 音色・楽器同定はしない(codex §4.3/§4.4)。violin/viola のような近縁楽器の
  分別は原理的に不可能。声部=音高帯であって楽器ではない。
- 時間的連続性は「直前に割当てた音との音高近接」の貪欲法であり、真の声部進行解析
  (voice leading)ではない。声部交差・跳躍の多い書法では誤る(grok 失敗C)。
- 旋律順は start_beats を信頼する(onset_sec は NaN 既定でソート根拠に使えない。
  contracts.py 参照)。同 start_beats 内は midi 降順(高音=上声)で安定化する。
- ベロシティ・強弱・アーティキュレーションは扱わない(grok 失敗5・codex §7)。
"""

from __future__ import annotations

from math import isnan

from earpipe.contracts import QuantizedNote

# 同一開始時刻とみなす start_beats の許容誤差(量子化後の浮動小数誤差吸収)。
# density.py の _BEAT_EPS と同じ精度で time-slice をキー化する。
_BEAT_EPS = 1e-6

# 対応する声部数の下限・上限(小編成限定・研究の失敗例反映)。
_MIN_VOICES = 2
_MAX_VOICES_SUPPORTED = 3

# 声部割当で「連続」とみなさない大跳躍のペナルティ基準(半音)。
# これ以上離れると連続性ボーナスを与えない(声部交差の誤引き継ぎ緩和)。
_LARGE_LEAP_SEMITONES = 12

# 空(未使用)声部を新規に開くペナルティ(半音換算)。既存声部への連続を優先し、
# 単旋律が余分な下声へ散らばるのを防ぐ(grok 失敗C の直接対策)。この値以下の
# 音高差なら既存声部の継続が新規声部より安くなる。
_NEW_VOICE_PENALTY = 24


def _time_key(start_beats: float) -> int:
    """start_beats を同時発音判定用の安定な整数キーへ量子化する。

    浮動小数の start_beats を _BEAT_EPS 精度で丸め、同一時刻の音符を
    同じ time-slice に集める(density._skyline_indices と同じ手法)。
    """
    return round(float(start_beats) / _BEAT_EPS)


def _dedup_same_pitch(notes: list[QuantizedNote]) -> list[QuantizedNote]:
    """同一 time-slice・同一 midi の重複音を1音へ統合する(不変・新規 list)。

    codex §4.3(Melodyne 単一blob)/ grok 失敗4(同音ユニゾンが1音に潰れる)への
    正直な対応: 同じ高さの同時発音は音声上分離不能なので、幻の声部を捏造せず
    最初に現れた1音のみ残す。confidence 最大などの選別はせず、入力順の最初を
    採用して決定的にする(timing/pitch は改変しない)。
    """
    seen: set[tuple[int, int]] = set()
    out: list[QuantizedNote] = []
    for n in notes:
        key = (_time_key(n.start_beats), int(n.midi))
        if key in seen:
            continue
        seen.add(key)
        out.append(n)
    return out


def _group_by_onset(notes: list[QuantizedNote]) -> list[list[QuantizedNote]]:
    """同一 start_beats(同時発音)ごとに音符をまとめ、時刻昇順の塊列を返す。

    各塊内は midi 降順(高音が先=上声候補)で安定ソートする。塊の順序は
    start_beats 昇順。onset_sec は NaN 既定で使えないため start_beats を信頼する。
    """
    buckets: dict[int, list[QuantizedNote]] = {}
    order: list[int] = []
    for n in notes:
        key = _time_key(n.start_beats)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(n)
    order.sort()
    groups: list[list[QuantizedNote]] = []
    for key in order:
        chunk = sorted(
            buckets[key], key=lambda x: (-int(x.midi), float(x.start_beats))
        )
        groups.append(chunk)
    return groups


def _assign_chunk(
    chunk: list[QuantizedNote],
    last_midi: list[int | None],
    voices: list[list[QuantizedNote]],
    n_voices: int,
) -> None:
    """1つの同時発音塊を n_voices 個の声部へ割り当てる(voices を破壊的に更新)。

    上から順(高音優先)に音を取り、各音を「連続性(直前割当音との音高近接)が最良で
    かつ音高帯の整合が取れる」声部へ入れる貪欲法。voices[0] を最上声部(skyline)と
    し、原則として高い音ほど小さいインデックスの声部へ寄せる。

    max_voices を超える同時音は、超過分を最寄り声部へ畳み込む(声部内で和音化)。
    これは「正しい声部割当」ではなく下書きのための丸め(モジュール docstring の限界)。

    引数:
        chunk: 同一 start_beats の音符列(midi 降順で渡される想定)。
        last_midi: 各声部の直近割当 midi(未割当は None)。呼び出し側と共有し更新する。
        voices: 各声部の音符 list(この関数が append する)。
        n_voices: 使用する声部数(2 or 3)。
    """
    m = len(chunk)
    # 上声から順に、声部インデックスを音高順で割り当てる基準を作る。
    # まず「この塊で何声部を実際に使うか」を、同時音数と n_voices の小さい方に。
    active = min(m, n_voices)

    # 各声部に最大1音を割り当てる(超過は後段で畳み込む)。
    # 高い音 → 小さい声部インデックスへ、を基本方針にしつつ、直前の音高との連続性で微調整。
    assigned_voice: list[int] = []
    used: set[int] = set()

    for note in chunk:
        best_voice = None
        best_cost = None
        for v in range(n_voices):
            if v in used and len(assigned_voice) < active:
                # まだ空き声部があるなら、この塊内では1声部1音を優先(重複割当は後段)。
                continue
            # コスト: 直前割当音との音高差(連続性)。未割当声部は中庸コスト。
            prev = last_midi[v]
            if prev is None:
                # 未使用声部は「音高帯の期待位置」からの乖離で評価。
                # 上声(v=0)は高音を、下の声部ほど低音を期待する擬似基準。
                # 加えて空声部を新規に開くペナルティを課し、既存声部への連続
                # (grok 失敗C: 声部間ジャンプ回避)を優先する。単旋律が1声部に
                # 収まり、下声を捏造しないための下限保証でもある。
                expected = _expected_pitch_for_voice(v, n_voices, chunk)
                cost = abs(int(note.midi) - expected) + _NEW_VOICE_PENALTY
            else:
                cost = abs(int(note.midi) - prev)
                if cost > _LARGE_LEAP_SEMITONES:
                    cost += _LARGE_LEAP_SEMITONES  # 大跳躍は割高にして交差を抑制
            # 音高順の整合ボーナス: 高音は小さい声部インデックスを好む。
            cost += v * 0.001 * (int(note.midi))  # 弱いタイブレーク(高音ほど v 小を選好)
            if best_cost is None or cost < best_cost:
                best_cost = cost
                best_voice = v
        if best_voice is None:
            best_voice = n_voices - 1
        assigned_voice.append(best_voice)
        used.add(best_voice)

    # 割当を確定(声部内は timing 破壊なしで append、last_midi 更新)。
    for note, v in zip(chunk, assigned_voice):
        voices[v].append(note)
        last_midi[v] = int(note.midi)


def _expected_pitch_for_voice(
    voice_index: int, n_voices: int, chunk: list[QuantizedNote]
) -> int:
    """未割当声部の期待音高(声部帯の中心)を、この塊の音高範囲から擬似算出する。

    上声(index 0)は塊の最高音付近、最下声部は最低音付近を期待値にする。
    真の音域ではなく「高音は上声へ」という整列のための擬似基準(限界)。
    """
    midis = [int(n.midi) for n in chunk]
    hi = max(midis)
    lo = min(midis)
    if n_voices <= 1:
        return hi
    # voice_index=0 → hi、voice_index=n-1 → lo の線形補間。
    frac = voice_index / (n_voices - 1)
    return int(round(hi - frac * (hi - lo)))


def separate_voices(
    notes: list[QuantizedNote],
    max_voices: int = 3,
) -> list[list[QuantizedNote]]:
    """同時発音を音高・連続性で2〜3声部に分離する(skyline+下声・非破壊)。

    上声(voices[0])を各時刻の最高音(skyline)の骨格とし、残る同時音を音高順・
    時間連続性優先で下の声部へ割り当てる。声部内の音符は元インスタンスをそのまま
    引き継ぎ(timing/pitch/duration を一切改変しない=不変)、start_beats 昇順で返す。

    引数:
        notes: 量子化済み音符列。旋律順は start_beats を信頼する(onset_sec は
            NaN 既定でソート根拠に使えない。contracts.py 参照)。音符/ノイズの
            選別は上流(F-108分類等)の責務で、ここには音符のみ来る前提。
        max_voices: 声部数の上限。2 または 3 のみ(小編成限定)。範囲外は ValueError。
            同時発音がこれを超える塊は、超過分を最寄り声部へ畳み込む(声部内で和音化)。

    戻り値:
        声部ごとの音符 list の list(長さは 1〜max_voices)。voices[0] が最上声部
        (skyline)。実際に音が割り当たった声部のみ返す(末尾の空声部は含めない)。
        各声部内は start_beats 昇順。入力が空なら空 list を返す。

    例外:
        ValueError: max_voices が 2 または 3 以外のとき(静かに失敗しない)。

    設計の要点(過大主張しない・先行研究反映):
        これは「編集可能な声部分けの下書き」であって、混合バンド音源からの正しい
        フルスコア声部割当ではない(F-019-codex エグゼクティブサマリー: 声部分離の
        独立検証済み成功例はほぼゼロ)。音色・楽器同定をしないため、同レジスタの
        声部交差・近縁楽器(violin/viola 等)の分別では誤る(codex §4.3/§4.4)。
        同音ユニゾンは音声上分離不能なので幻の声部を作らず1音へ統合する(grok 失敗4)。
        割当は決定的で説明可能な貪欲法にとどめ、賢さより再現性・非破壊性・限界の
        明示を優先する(モジュール docstring の限界一覧を参照)。
    """
    if not (_MIN_VOICES <= int(max_voices) <= _MAX_VOICES_SUPPORTED):
        raise ValueError(
            f"max_voices は 2 または 3(小編成限定)。受領値: {max_voices!r}"
        )
    if not notes:
        return []

    n_voices = int(max_voices)

    # onset_sec は NaN 既定のため start_beats を旋律順の唯一の根拠にする。
    # NaN の start_beats は末尾へ寄せて決定的にする(異常入力でも落ちない)。
    def _sort_key(n: QuantizedNote) -> tuple[float, int]:
        sb = float(n.start_beats)
        if isnan(sb):
            return (float("inf"), -int(n.midi))
        return (sb, -int(n.midi))

    ordered = sorted(notes, key=_sort_key)

    # 同音ユニゾン(同時刻・同高)は1音へ統合(幻声部を作らない)。
    deduped = _dedup_same_pitch(ordered)

    groups = _group_by_onset(deduped)

    voices: list[list[QuantizedNote]] = [[] for _ in range(n_voices)]
    last_midi: list[int | None] = [None] * n_voices

    for chunk in groups:
        _assign_chunk(chunk, last_midi, voices, n_voices)

    # 各声部を start_beats 昇順に整える(塊は時刻昇順で処理済みだが明示的に安定化)。
    for v in range(n_voices):
        voices[v].sort(key=lambda x: (float(x.start_beats), -int(x.midi)))

    # 音が割り当たった声部のみ返す(末尾の空声部は落とす=正直な声部数)。
    return [v for v in voices if v]
