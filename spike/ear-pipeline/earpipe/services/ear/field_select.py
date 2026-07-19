"""選択的抽出(C8): SNRに応じて確信度要求を上げ「怪しいものは拾わない」側に倒す。

絶対音感者の実態(雑音下では選択的注意で音程成分だけを拾う)のエミュレーション。
雑音が強いほど閾値を上げるため、取りこぼしは増えるが幽霊は抑えられる —
「間違って書くより、書かないで正直に言う」設計原則(product-vision)。
"""

from earpipe.contracts import NOTABLE_CLASSES, PitchEvent, SoundEvent

# 閾値はfield.pyの実SNRスケール(dB)と同期(#45で無音率検出器から作り直し20/10dBに再較正)
_SNR_CLEAN_DB = 20.0     # field.py._SNR_CLEAN_DB と同値(サービス境界のため定数重複。変更時は両方)
_SNR_NOISY_DB = 10.0     # field.py._SNR_NOISY_DB と同値
_CONF_CLEAN = 0.50       # >=20dB(clean): 既定と同じ
_CONF_NOISY = 0.55       # 10-20dB(noisy)
_CONF_VERY_NOISY = 0.58  # <10dB(very_noisy)
_MIN_DUR_NOISY = 0.10    # 雑音下では極短イベントも捨てる(秒)


def select_events(events: list[PitchEvent], snr_db: float) -> list[PitchEvent]:
    """SNR適応の確信度・持続時間フィルタ。

    閾値は2026-07-19の実測較正: mono(pYIN)は雑音下でも幽霊をほぼ出さないため
    過度の絞りは良品を殺すだけと判明(pink SNR10でF1 0.968→0.316の実測)。
    軽い絞り+極短除去に留める。
    """
    if snr_db >= _SNR_CLEAN_DB:
        min_conf, min_dur = _CONF_CLEAN, 0.0
    elif snr_db >= _SNR_NOISY_DB:
        min_conf, min_dur = _CONF_NOISY, _MIN_DUR_NOISY
    else:
        min_conf, min_dur = _CONF_VERY_NOISY, _MIN_DUR_NOISY

    return [
        e
        for e in events
        if e.confidence >= min_conf and (e.offset - e.onset) >= min_dur
    ]


def gate_by_class(sound: SoundEvent, allow_poly: bool = False) -> bool:
    """音事件の分類タグに基づき「音符化してよいか」を返す(F-108受入条件(1)(3))。

    - noisy/inharmonic/speech は音符化しない(音響オブジェクトとして別途保持)。
    - 既定は単音抽出優先: poly(和音)は音符化を保留し、失望を防ぐ
      (allow_poly=True でオンデマンド分解を許可)。
    - pitched_stable/pitched_transient は常に音符化を許す。

    「間違って書くより、書かないで正直に言う」設計原則(product-vision)の実装。
    """
    if sound.label == "poly":
        return allow_poly
    return sound.label in NOTABLE_CLASSES
