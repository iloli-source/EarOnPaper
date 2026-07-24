# TABリズム記譜の標準 — #143実装前調査（2026-07-25）

**目的:** #143（拍子表示・単独8分の旗・タイ・休符グリフ・三連括弧・コード図衝突）の実装前調査。英中網羅（WebSearch＋grok CLI・Songsterr/Guitar Pro/MuseScore/Hal Leonard/SMuFL/Guitar Pro中文解説）。

## 1. 標準慣行（製品・言語圏の合流点）

- **拍子記号**: 冒頭＋変更小節の小節線直後に表示（行末に予告=cautionary）。TAB単独譜でも表示するのが標準（MuseScoreはTABへの拍子表示を設定で提供・Guitar Pro中文解説も曲頭表示）
- **リズム帯**: stem＋flag/beam。連桁が組めない単独8分/16分には**旗(flag)が必須**（旗なしは4分と区別不能=誤り）。帯の上下はツール設定依存（MuseScore: Above/Below/Through）— 当プロジェクトは参考動画準拠の下側を維持
- **タイ**: **弧が一次表記**。持続先の数字は括弧 `(5)` で出す（Hal Leonard規則）。ただし括弧はゴーストノートとも多義（中国語圏教材は「幽灵音」読みが優勢）→ 凡例か限定運用が必要。弧はフレット数字を遮らない外側に描く
- **三連符**: **角括弧＋中央に「3」**（丸括弧は非標準・「3」を先頭に寄せるのも誤り）。括弧はbeamの外側へ
- **休符**: SMuFL標準形（4分=稲妻型 U+E4E6・8分=玉つき斜線 U+E4E7）。**全休符=線からぶら下がる/2分休符=線に載る、の上下を逆にするのが世界最頻の誤り**。休符はbeamに含めない（Songsterr明記）

## 2. 自前SVGでの失敗例（grok調査・回避リスト）

- タイ弧を弦線の内側に深く通して数字を遮る / タイとスラー(HO/PO)を同じ見た目にする
- 「3」を先頭寄せ・丸括弧・beamと括弧の交差
- 全休符と2分休符の上下逆 / 休符をリズム帯でなく弦線上に音符のように置く
- 2桁フレットの幅を1桁と同じにして符幹と衝突（→#139のrodで解決済み）
- 拍子変更後も4/4のbeam区切りを流用（拍感が壊れる）
- SMuFLを使わない自作pathで「それっぽいが違う」グリフ — 使う場合は登録点（flagのy原点・restのhang/sit）を守る

## 3. 実装への示唆（当プロジェクトの制約込み）

1. **拍子表示＋4/4固定解消**: エンジンは `estimate_meter`（meter.py・単一拍子/曲）と `--beat` 上書きを既に持つ — pipelineで解決済みの拍数を `write_tab_pdf(beats_per_measure=)` に渡し、tab.pyの `_BEATS_PER_MEASURE` 定数参照をパラメータ化。表示は曲頭に数字スタック（L/4）。曲中変化はエンジン未対応のためスコープ外（正直に記録）
2. **単独旗**: `_rhythm_marks` で前後どちらとも連桁にならない8分/16分へ旗を描く（16分は2枚）。SMuFL形状を模した小pathで符幹先端から右へ
3. **休符グリフ**: 4分を稲妻型に改良・全/2分の上下（hang/sit）は現実装が正しいことを確認済み・8分は現行の玉付き斜線を微調整
4. **タイ（小節跨ぎ）**: 小節線を越える持続音を表示分割し、弧＋括弧数字 `(n)` を次小節頭に描く。弧は数字の上側外周。括弧はタイ専用に限定（ゴースト用途と混同させない）
5. **三連括弧**: `grid_per_beat=3` の曲では拍単位に角括弧＋中央「3」をリズム帯下に描く
6. **コード図衝突**: `_CHORD_BAND_H` に対し `diagram_svg` が大きい → 帯の高さを図の実寸+マージンに拡大（システム間隔 `_SYS_GAP` と連動）
7. 描画レイヤ順: 弦線→数字→符幹/beam/旗→タイ→括弧（grok推奨に一致・現行とも整合）

## 主要出典

- Songsterr How to read tab: https://www.songsterr.com/howtoreadtab
- Hal Leonard Guitar Notation Legend: https://www.halleonard.com/bin/GuitarNotationLegend.pdf
- Guitar Pro: Note ties / Time signature: https://www.guitar-pro.com/academy/l/49288-tie-or-note-tie / https://www.guitar-pro.com/academy/l/49282-time-signature
- Guitar Pro中文解説（记谱法/三连音/括号数字）: https://www.guitarpro.cc/jiqiao/lijie-jipu.html ほか
- SMuFL Rests/Flags/Time signatures: https://w3c-cg.github.io/smufl/latest/tables/rests.html ほか
- MuseScore TABカスタマイズ/拍子表示: https://handbook.musescore.org/idiomatic-notation/guitar/customizing-a-tablature-staff
- Gould, Behind Bars sample: https://www.behindbarsnotation.co.uk/contents/sample_pages.pdf
- VexFlow（TAB SVG参照実装）: https://www.vexflow.com/
