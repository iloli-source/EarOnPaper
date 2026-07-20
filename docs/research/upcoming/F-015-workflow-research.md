# F-015 楽器分類 — 実装前リサーチ(10並列ワークフロー)

**取得日:** 2026-07-21 / Issue #72 / 実装コミット 5167a73
**方式:** 先行リサーチ(Web/論文・失敗例重視)→実装 の並列ワークフローのリサーチ段を保存

## 推奨アプローチ(approach)
実装対象: classify_instrument(y: np.ndarray, sr: int) -> InstrumentGuess。既存の姉妹モジュール earpipe/services/stem/field.py の classify_segment を「型・命名・スタイルの手本」として厳密に踏襲する(親が後で配線する前提の自己完結モジュール)。

【InstrumentGuess の定義場所】contracts.py は編集禁止のため、field.py が FieldAnalysis をローカル定義するのと同じ流儀で、新規モジュール冒頭に @dataclass(frozen=True) InstrumentGuess(label: str, confidence: float, features: dict[str, float]) を定義する。label は Literal ではなく str 指定なので Literal 化せず str のまま(指示準拠)。features は round 済みの生特徴を格納(centroid/bandwidth/rolloff/zcr/perc_ratio/hp_ratio 等)。

【特徴抽出】field.py と同一の下ごしらえを再利用する形で自前実装:
1. y = _to_mono(np.asarray(y, dtype=np.float64))、np.all(np.isfinite) で NaN/Inf を nan_to_num。空/極小(max|y|<1e-6 or len<256)は _guess("unknown", 0.0, {}) で早期return。
2. S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=n_fft//4))、n_fft は len に応じ 2048/512(field.py と同一)。
3. spectral_centroid(S=S, sr=sr)[0]、spectral_bandwidth(S=S, sr=sr)[0]、spectral_rolloff(S=S, sr=sr, roll_percent=0.85)[0]、zero_crossing_rate(y)[0] を各々 mean。centroid は np.isfinite でフィルタしてから mean(field.py の作法)。
4. HPSS 打楽器性: H,P = librosa.decompose.hpss(S); perc_ratio = p_e/(h_e+p_e+1e-18)。

【判定(粗いヒューリスティック・確信度は正直に低め)】判定順で早期return、閾値は module 定数化(field.py の calibration コメント様式):
- percussive: perc_ratio が高い(例 >0.6)かつ ZCR 高め → "percussive"。
- bass_like: mean_centroid が低い(概ね <500Hz 目安)かつ rolloff 低め・調波優勢 → "bass_like"。低スペクトル重心=暗い/低音は文献一致(bass guitar は低 centroid)。
- vocal_like: centroid_flux(std/mean、音素遷移で揺れる)が大きく、centroid 中低域(<3kHz 目安)、調波優勢 → "vocal_like"。field.py の speech 代理ロジックを流用。
- keyboard_like: 明確なアタック+安定調波+中域 centroid で穏当な帯域幅 → "keyboard_like"。
- guitar_string_like: 中域 centroid・撥弦アタック(短時間高 ZCR/立ち上がり)・調波優勢 → "guitar_string_like"。
- どれにも当てにならなければ "unknown"。
確信度は max 0.5〜0.6 程度に頭打ちさせ、_guess で np.clip(0,1) と round。「学習なし・粗判定」を confidence とdocstringで正直に明記。

【テスト】新規テスト1つ。AAA形式・pytest。合成信号で各ラベルを最低限検証:白色/インパルス列→percussive、低周波正弦(~80-110Hz)→bass_like、中周波数掃引で重心を揺らした調波音→vocal_like 傾向、無音→unknown、frozen 不変性(dataclasses.FrozenInstanceError)、confidence が 0-1 かつ features が dict。閾値と合成信号は実際に走らせて緑になるよう相互調整する(捏造禁止・実行必須)。.venv/bin/python -m pytest <testfile> -q -p no:cacheprovider で新規テストのみ実行しパス確認。

## 落とし穴・失敗例(pitfalls)
【契約型 InstrumentGuess の所在】最大の落とし穴。contracts.py に InstrumentGuess は存在せず、かつ contracts.py は編集禁止。→ 新規モジュール内にローカル frozen dataclass として定義する(field.py::FieldAnalysis と同一方針)。親が後で contracts.py へ昇格・配線する想定。勝手に contracts.py を編集しないこと。

【librosa の軸配置と mono 化】soundfile と librosa で ch 軸が逆(field.py L79-86 の _to_mono コメント)。ステレオ入力は必ず _to_mono を通す。この helper を新規モジュールにも同名で持たせる(field からの import は「既存編集不可」に抵触しない読み取りだが、自己完結のため再定義が安全)。

【非有限値でlibrosa即死】破損WAV由来の NaN/Inf を通すと librosa がクラッシュ(field.py #45)。stft 前に np.all(np.isfinite)→nan_to_num を必ず入れる。

【ZCR は絶対閾値が脆い】文献一致の限界: 高ZCR=無声摩擦音/ノイズ/打楽器/シビランスすべてで上がるため、ZCR単独で percussive と vocal(サ行)を分離不能。撥弦アタックも一過性に高ZCR。→ 必ず HPSS 打楽器比・調波優勢と AND で使う。単独判定禁止。

【spectral centroid は定常でない】同一音でも時間で重心が動く(researchgate 指摘)。1音=1重心の仮定は崩れる。mean と std(flux)両方を使い、絶対 Hz 閾値には強く依存しない設計に(閾値は「目安」でconfidenceを下げる)。

【HPSS は白色雑音/拍手を調波・打撃へほぼ均等分配】field.py L179,232-235 の教訓: 広帯域雑音は h_e≒p_e となり perc_ratio で捕まらない。純打楽器の閾値を高く取りすぎると雑音を percussive と誤る。ノイズは "percussive" でなく "unknown" に倒す方が正直。

【HPSS 定義の曖昧さ】白色雑音/拍手は harmonic でも percussive でもない(audiolabs-erlangen)。混合音は支配成分に丸められ、多楽器同時発音(piano+guitar)は原理的に分離不能(ismir2009)。→ label は「支配的な1楽器の粗い推測」であり多楽器分類ではないと docstring に明記。

【confidence を高く出さない】学習なし・単一区間・閾値ヒューリスティックなので過信は害。max 0.5〜0.6 で頭打ち、境界帯は "unknown"+低 confidence。「動く」と誇張しない。

【round と NaN==NaN】features dict の値は round し float 化。confidence は np.clip(0,1)→round。空スペクトル(S.size==0)ガードを忘れない(field.py L205)。

【テストの脆さ】合成信号のラベル境界は閾値と密結合。厳密ラベル一致より「期待ラベル or unknown を許容」「confidence レンジ」「frozen 不変」を検証する方が緑を保ちやすい。必ず実行して調整、推測でパス宣言しない。

## 参考(prior_art)
【最重要・同一リポジトリ内の手本】/Users/tadaakikurata/works/iloli/プロジェクト/採譜/spike/ear-pipeline/earpipe/services/stem/field.py の classify_segment(y, sr)。librosa.stft→decompose.hpss→spectral_flatness/spectral_centroid を使い 6タグ分類し、frozen SoundEvent を返す。_to_mono/非有限ガード/n_fft可変/閾値のmodule定数化+較正コメント/confidence を np.clip+round し正直に頭打ち/limitations を docstring 明記、という本機能が守るべき全規約がここに揃っている。新規 classify_instrument はこの写経で書くのが最も堅牢。契約型は /Users/tadaakikurata/works/iloli/プロジェクト/採譜/spike/ear-pipeline/earpipe/contracts.py(PitchEvent/QuantizedNote/FieldReport/SoundEvent、frozen dataclass + Literal 値域固定の流儀)。

【中/英 文献の要点】
- Predominant Musical Instrument Classification based on Spectral Features (arXiv:1912.02606): spectral centroid/rolloff/bandwidth/ZCR/MFCC を楽器分類に使用。特徴融合は冗長・最適閾値が特徴ごとに違い常には精度向上しない、と警告。多楽器 predominant 認識は依然課題。
- ScienceDirect "Spectral Centroid overview" / Meyda audio-features: spectral centroid = スペクトル重心=音の「明るさ」。低 centroid=bass guitar、高 centroid=trumpet の弁別に使えるが絶対値でなく相対指標。
- ResearchGate "Musical Instrument Timbres Classification with Spectral Features": 実楽器の spectral feature は同一音でも常に変動し、多数の timbral 成分のランダムな変動を考慮しないと頑健にならない(=固定閾値ヒューリスティックの根本限界)。
- audiolabs-erlangen FMP C8 (HPSS) / FMP: HPSS は harmonic=時間方向連続(水平線)、percussive=周波数方向連続(垂直線)を利用。white noise/applause は harmonic でも percussive でもなく分離が原理的に曖昧。french horn/oboe は tonal/noise 比が piano/flute より低く、楽器固有の attack/blowing ノイズが HP比分類を難しくする。
- ISMIR2009 "Musical Instrument Recognition in Polyphonic": 多声・多音色で複数楽器同時発音は単一楽器前提を崩す。NMF+GMM(MFCC)等の分離が必要で、単純特徴では overlapping 楽器(piano/guitar)混同。
- Aalto Speech Processing / Wikipedia ZCR: ZCR は支配周波数の粗い推定。低=有声/正弦(母音・ハミング)、高=無声摩擦音('s''f'≈3000 crossings/s)・ノイズ・打楽器・シビランス。voiced/unvoiced や percussive 検出の定番だが、ノイズ・撥弦アタックでも上がるため単独では脆い(→エネルギー/HP比と併用が定石)。
- ijais "Musical Instrument Recognition using ZCR": ZCR を楽器認識特徴として使用する先行例(補助特徴としての位置づけ)。

## 実装上の限界・正直な注記(notes)
実装は既に完成状態で存在しており（前セッションの成果物と推定）、本タスクでは型整合の確認と新規テストの実走検証を行った。以下は正直な限界:

- 学習なし・単一区間・閾値ヒューリスティックのため confidence は _CONF_CAP=0.55 で頭打ち。過信は害という設計。
- label は「支配的な1楽器の粗い推測」であり多楽器同時分類ではない（piano+guitar 等の重なりは原理的に分離不能・ISMIR2009）。
- guitar と violin（撥弦/擦弦）は単一区間の粗特徴では分離困難なため意図的に "guitar_string_like" に束ねている（テストの violin→guitar_string_like はこの仕様）。
- 白色雑音/拍手は HPSS で調波・打撃へほぼ均等分配されるため percussive で捕まらず unknown に倒す設計（test_white_noise_falls_to_unknown_not_percussive で担保）。
- 合成信号テストは閾値と密結合で脆いため、厳密ラベル一致ではなく「期待ラベル or unknown を許容」「confidence レンジ」「frozen 不変」を検証する方針（脆さ回避）。
- vocal_like の閾値（_VOCAL_FLUX_MIN=0.42 / _VOCAL_PERC_MIN=0.18 等）は 2026-07-21 の実7楽器データで較正済みとコメントにあるが、母集団が小さく汎化性能は未保証。
- Python 3.14.6 / .venv 環境で検証。audioread の aifc/sunau DeprecationWarning が出るが機能影響なし。
- 既存ファイル（__init__.py, pipeline.py, contracts.py 等）は一切編集していない。配線は上記 wiring の通り親が実施する。
