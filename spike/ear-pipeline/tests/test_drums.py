"""detect_drums(F-018 / Issue #84)のテスト。

学習なしの粗判定のため、厳密な kit 一致より「期待 kit or unknown を許容」
「戻り値スキーマの健全性」「confidence レンジ」「打点の順序・境界安全性」を検証する
(閾値と合成信号は密結合で脆いため)。AAA形式(Arrange-Act-Assert)。
"""

import numpy as np

from earpipe.services.ear.drums import detect_drums

_SR = 22050
_KITS = {"kick", "snare", "hihat", "tom", "cymbal", "unknown"}


def _click_at(t_sec: float, dur: float, sr: int, band: str) -> np.ndarray:
    """dur 秒の無音バッファの t_sec に、指定帯域の短い打撃を1発置いた波形を返す。

    band:
      - "low"  : ~60Hz の減衰正弦(kick 様の低音打撃)
      - "high" : 高域バンドノイズ(hihat/cymbal 様)
      - "noise": 広帯域ノイズ + 中低域(snare 様)
      - "mid"  : ~180Hz の減衰正弦(tom 様の中低域胴鳴り)
    """
    n = int(sr * dur)
    y = np.zeros(n, dtype=np.float64)
    start = int(t_sec * sr)
    hit_len = int(0.05 * sr)
    idx = np.arange(hit_len)
    env = np.exp(-idx / (0.01 * sr))  # 速い減衰(打撃の立ち上がり)
    rng = np.random.default_rng(0)

    if band == "low":
        tone = np.sin(2 * np.pi * 60.0 * idx / sr)
        hit = tone * env
    elif band == "mid":
        tone = np.sin(2 * np.pi * 180.0 * idx / sr)
        hit = tone * env
    elif band == "high":
        noise = rng.normal(0.0, 1.0, hit_len)
        # 高域強調: 1次差分で低域を削る
        noise = np.diff(noise, prepend=0.0)
        hit = noise * env
    else:  # "noise" (snare 様: 広帯域 + 中低域胴鳴り)
        noise = rng.normal(0.0, 1.0, hit_len)
        body = np.sin(2 * np.pi * 200.0 * idx / sr)
        hit = (0.7 * noise + 0.3 * body) * env

    end = min(start + hit_len, n)
    y[start:end] = hit[: end - start]
    peak = np.max(np.abs(y))
    if peak > 0:
        y = y / peak
    return y


def test_silence_returns_empty_list() -> None:
    # Arrange
    y = np.zeros(_SR, dtype=np.float64)

    # Act
    events = detect_drums(y, _SR)

    # Assert
    assert events == []


def test_too_short_input_returns_empty_list() -> None:
    # Arrange
    y = np.ones(100, dtype=np.float64)  # _MIN_LEN 未満

    # Act
    events = detect_drums(y, _SR)

    # Assert
    assert events == []


def test_result_schema_is_valid() -> None:
    # Arrange: 低域打撃を1発
    y = _click_at(0.2, 0.6, _SR, "low")

    # Act
    events = detect_drums(y, _SR)

    # Assert: 各要素が規定スキーマ・型・値域を満たす
    assert isinstance(events, list)
    assert len(events) >= 1
    for ev in events:
        assert set(ev.keys()) == {"onset_sec", "kit", "confidence"}
        assert isinstance(ev["onset_sec"], float)
        assert isinstance(ev["kit"], str)
        assert isinstance(ev["confidence"], float)
        assert ev["kit"] in _KITS
        assert 0.0 <= ev["confidence"] <= 1.0
        assert ev["onset_sec"] >= 0.0


def test_low_frequency_hit_is_kick_or_unknown() -> None:
    # Arrange: 60Hz 減衰正弦 → 低域集中(kick 様)
    y = _click_at(0.2, 0.6, _SR, "low")

    # Act
    events = detect_drums(y, _SR)

    # Assert: kick か、疑わしければ unknown(粗判定の脆さを許容)
    assert len(events) >= 1
    kits = {ev["kit"] for ev in events}
    assert kits & {"kick", "unknown", "tom"}  # 低音は tom へ寄る可能性も許容


def test_high_band_noise_is_metallic_or_unknown() -> None:
    # Arrange: 高域バンドノイズ → hihat/cymbal 様
    y = _click_at(0.2, 0.6, _SR, "high")

    # Act
    events = detect_drums(y, _SR)

    # Assert: 高域金属系(hihat/cymbal/snare)か unknown を許容。kick には倒れない
    assert len(events) >= 1
    for ev in events:
        assert ev["kit"] != "kick"
        assert ev["kit"] in _KITS


def test_onsets_are_sorted_ascending() -> None:
    # Arrange: 打点を3つ(帯域を変えて)配置
    dur = 1.2
    y = (
        _click_at(0.15, dur, _SR, "low")
        + _click_at(0.55, dur, _SR, "noise")
        + _click_at(0.95, dur, _SR, "high")
    )
    peak = np.max(np.abs(y))
    y = y / peak if peak > 0 else y

    # Act
    events = detect_drums(y, _SR)

    # Assert: onset_sec が昇順(打点順序が保存される)
    onsets = [ev["onset_sec"] for ev in events]
    assert onsets == sorted(onsets)
    assert len(events) >= 1


def test_stereo_input_is_accepted() -> None:
    # Arrange: (frames, ch) のステレオ入力も _to_mono で受け付ける
    mono = _click_at(0.2, 0.6, _SR, "low")
    stereo = np.stack([mono, mono], axis=1)

    # Act
    events = detect_drums(stereo, _SR)

    # Assert
    assert isinstance(events, list)
    for ev in events:
        assert ev["kit"] in _KITS


def test_non_finite_input_does_not_crash() -> None:
    # Arrange: NaN/Inf を含む破損波形(librosa 即死回避のガードを検証)
    y = _click_at(0.2, 0.6, _SR, "noise")
    y[10] = np.nan
    y[20] = np.inf

    # Act
    events = detect_drums(y, _SR)

    # Assert: 例外を投げずスキーマを保つ
    assert isinstance(events, list)
    for ev in events:
        assert np.isfinite(ev["confidence"])
        assert ev["kit"] in _KITS


def test_confidence_is_capped_low() -> None:
    # Arrange: 学習なし粗判定なので confidence は頭打ち(過信しない)
    y = _click_at(0.2, 0.6, _SR, "low")

    # Act
    events = detect_drums(y, _SR)

    # Assert: どの kit でも 0.55 を超えない(正直な低め確信度)
    assert len(events) >= 1
    assert all(ev["confidence"] <= 0.55 for ev in events)


def test_onset_within_signal_bounds() -> None:
    # Arrange
    dur = 0.8
    y = _click_at(0.3, dur, _SR, "mid")

    # Act
    events = detect_drums(y, _SR)

    # Assert: すべての打点が信号長の範囲内(境界安全性)
    assert len(events) >= 1
    for ev in events:
        assert 0.0 <= ev["onset_sec"] <= dur
