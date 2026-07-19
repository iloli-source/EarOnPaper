"""選択的抽出(C8): SNRに応じて確信度要求を上げ「怪しいものは拾わない」側に倒す。

絶対音感者の実態(雑音下では選択的注意で音程成分だけを拾う)のエミュレーション。
雑音が強いほど閾値を上げるため、取りこぼしは増えるが幽霊は抑えられる —
「間違って書くより、書かないで正直に言う」設計原則(product-vision)。
"""

from earpipe.contracts import PitchEvent

# 閾値はfield.pyの内部SNRプロキシ値基準(絶対dBではない。クリーン系≈9で飽和する実測スケール)
_CONF_CLEAN = 0.50       # プロキシ>=8.0(clean): 既定と同じ
_CONF_NOISY = 0.55       # 6.0-8.0(noisy)
_CONF_VERY_NOISY = 0.58  # <6.0(very_noisy)
_MIN_DUR_NOISY = 0.10    # 雑音下では極短イベントも捨てる(秒)


def select_events(events: list[PitchEvent], snr_db: float) -> list[PitchEvent]:
    """SNR適応の確信度・持続時間フィルタ。

    閾値は2026-07-19の実測較正: mono(pYIN)は雑音下でも幽霊をほぼ出さないため
    過度の絞りは良品を殺すだけと判明(pink SNR10でF1 0.968→0.316の実測)。
    軽い絞り+極短除去に留める。
    """
    if snr_db >= 8.0:
        min_conf, min_dur = _CONF_CLEAN, 0.0
    elif snr_db >= 6.0:
        min_conf, min_dur = _CONF_NOISY, _MIN_DUR_NOISY
    else:
        min_conf, min_dur = _CONF_VERY_NOISY, _MIN_DUR_NOISY

    return [
        e
        for e in events
        if e.confidence >= min_conf and (e.offset - e.onset) >= min_dur
    ]
