# F-099 採譜結果のLLM/エージェント可読エクスポート — 論文＋WEB調査

> 機能: 採譜結果を LLM/エージェントが読める構造化テキストに変換する（小節・コード・音符列の構造化）。
> 調査観点: (1) 音楽の構造化テキスト表現の比較と情報欠落 (2) LLMが誤読/破綻する失敗例の最大化 (3) ベストプラクティス。
> 調査手段: `mcp__codex__codex`（gpt-5.2）による一次調査 → WebSearch で主要URL・主張の実在検証。英語・中国語中心。
> 作成日: 2026-07-21 / 調査主体: Codex + WebSearch 検証

---

## 要約（3行）

- LLM/agent向けの採譜exportは、既存記法をそのまま渡すのではなく `bar_id / voice_id / onset(絶対) / duration / pitch_spelling / midi / chord / confidence / source_span` を明示した**正規JSONL**を主形式にし、MusicXML/MIDI/ABCは派生ビューとして分離するのが最も堅い。
- 最大の失敗源は5つ: ①MIDI系の記譜情報欠落（enharmonic/tie/slur/rest消失）②ABC/LilyPondの暗黙状態（onset累積復元・`\relative`のoctave伝播）③MusicXML/MEIの冗長性によるcontext切れ・タグ破壊 ④コードシンボルの曖昧性 ⑤tuplet/tie/beam/voiceの復元推測。
- 実証研究では、LLMは symbolic(MIDI/ABC) では高精度でも voice数増加や audio 化で急落する（Libretto: ABC読取8声で17%まで低下、Carone et al.: MIDIは天井近いがaudioで大幅低下）。決定論的スキーマ検証を人間レビュー前に噛ませることが必須。

---

## 1. 構造化テキスト表現の比較と失われる情報

| Format | 向いている用途 | 失いやすい情報 / LLM失敗点 |
|---|---|---|
| **MusicXML** | Western notation の交換（interchange）。bars/parts/notes/lyrics/layout semantics をかなり保持 | XMLが冗長で大きい。長い曲でLLM context切れ、閉じタグ破壊、`tie start/stop`・`slur number`の対応崩れ。出版社別 engraving は完全再現しない |
| **MEI** | 学術edition、source variants、editorial markup、facsimile連携 | 柔軟すぎ（"framework, not a data format"）。同一事象を複数encode可能でagentに負担。MEI Basicでeditorial/complex markup脱落 |
| **Humdrum `**kern`** | 解析向け。pitch/duration/accidentals/articulations/ornaments/ties/slurs/beaming を持てる | syntactic中心でorthographic情報は薄い。tab/spine/null tokenに依存し空白変換で破壊。transposing楽器はconcert pitch化で記譜音消失 |
| **ABC notation** | 軽量テキスト、folk tune、LLM学習に最適（MIDIの約38%トークン数） | onsetが累積durationで**暗黙**（絶対onsetがない）。tie `-` と slur `()` の混同。chord内異duration は仕様上 undefined。未知記号はignore。chord記号は仕様側も "liberally" 扱いと明記するほど曖昧 |
| **LilyPond** | engraving source（高品質出力、言語的） | `\relative` は前音基準でoctave決定 → 1音の`'`/`,`欠落が**後続全体にoctave伝播**。macro/変数/命令が多く部分編集で構文破壊しやすい |
| **MIDI / MIDI-as-JSON** | playback、DAW、note event列（Tone.js MIDI JSON, MusPy note repr） | 記譜情報が大量脱落。F#とGb、rests、stem、ties、slurs、beams、clef、phrasing を表せない。`pitch=63`だけでは D#/Eb 不明 |
| **Custom JSON**（推奨） | agent-readable の最有力。bar/voice/onset明示、schema validation可 | 設計を誤ると「ただのMIDI JSON」に退化し enharmonic/tuplet/tie/voice/chord spelling/confidence/provenance を落とす |
| **Fumen / lead-sheet系** | chord chart、rhythm slash、repeats、rehearsal mark | note列採譜には不足。melody/polyphony/voice-leadingの主表現に使ってはいけない。※「moe-fumen / 萌え譜面」という**標準フォーマットの実在URLは確認できず**（検索ではrhythm-game chart用語や `hbjpn/fumen`（太鼓リズムゲーム譜面ライブラリ）が主。音楽採譜の汎用表現規格としては非実在の可能性が高い） |
| **Strudel** | live coding / pattern（mini-notation） | cycle/pattern semantics中心。bar単位の確定採譜・engraving・演奏者向けvoice分離に弱い |
| **REMI / tokenized MIDI** | Transformer入力（bar/position/pitch/duration token） | agent読取にはflat event streamが散乱。Librettoは REMI が約6.9x token・single voice参照で約44x読取負荷と主張 |

---

## 2. LLM/agentが誤読・破綻する具体的失敗例

1. **ABC onset hallucination / voice崩壊**: ABCはbar内onsetを累積durationで復元させる必要がある。Libretto の比較ベンチではABC読取が42%、**8声では17%**まで低下し out-of-meter な回答も出た（※著者提供の小規模ベンチという caveat 付き）。
2. **ABC multi-track misalignment**: MuPT は multi-track 生成で measure alignment が崩れる問題を挙げ、**SMT-ABC Notation**（同一index barを`<|>`で連結）で bar/track consistency を保つ設計にした。
3. **ABC syntax break**: `tie -` と `slur ()` の混同、tuplet `(3abc` の範囲誤読、未知decoration無視、chord内duration不一致（仕様上undefined）。
4. **LilyPond octave cascade**: `\relative` の近接音高規則により、1つの `'`/`,` 欠落で後続全体が octave シフト。LilyBench も「compile可能でも structural understanding は困難」と報告。
5. **MusicXML context failure**: 保持力は高いが verbose。全曲XMLを渡すと context truncation・閉じタグ破壊・`tie`/`slur number` 対応崩れ。
6. **MIDI-as-JSON hallucination**: `pitch=63` から D#/Eb・rest・beam・tie・slur・clef を agent が「もっともらしく」補完してしまう。
7. **chord symbol ambiguity**: `C/E` は inversion か added-bass か。`dim / ø / alt / sus / no3 / N.C.` は実装差大。ABC仕様も chord handling を volatile/liberal と明記。
8. **audio依存の誤認 (重要)**: Carone et al. (2026, PMLR v303) は「LLMs can read music, but struggle to hear it」— **symbolic(MIDI)では天井近いが audio で大幅低下**、reasoning/few-shot でも埋まらず、小さな知覚誤りで記号推論層が崩壊すると報告。採譜agentには audio推論頼みではなく machine-checkable schema + 決定論的検証が必要。

---

## 3. LLM/agent-readable export のベストプラクティス

- **主形式は canonical transcription JSONL**: 1 bar 1 object（または1 event 1 line）。長い曲でも chunk 単位で検証・差分編集できる。
- **onsetは必ず絶対値**: `bar_index / beat / slot / tick / duration_tick`。ABCのような累積復元を agent にやらせない。
- **pitchは二重保持**: `pitch_spelling:"Eb4"` + `midi:63`、加えて `enharmonic_policy / key_context / confidence`。
- **chordも二重保持**: `symbol_raw:"C/E"` + `root/quality/bass/degrees/omitted/altered/confidence`。曖昧なら `parse_status:"ambiguous"`。
- **notation-only情報を落とさない**: `tie_group_id / slur_id / beam_group_id / tuplet_ratio / voice_id / staff_id / stem / articulations / ornaments`。
- **provenanceを持つ**: `source_audio_start_sec / source_audio_end_sec / omr_bbox / model_confidence / human_verified`。
- **exportを多層化**: `canonical.jsonl` を真実、`musicxml` を notation interchange、`midi` を playback、`abc / lilypond / fumen` を人間/LLM向け軽量ビュー。
- **agent編集はpatch式**: 全再生成でなく stable ID で `replace note n123 duration_tick=240`。
- **CI検証必須**: JSON Schema / bar duration sum / voice overlap / tie-slur pairing / tuplet total / MusicXML round-trip / MIDI render smoke test。

### 最小スキーマ例

```json
{
  "bar_id": "b012",
  "time_signature": "4/4",
  "grid": {"ppq": 480, "slots_per_bar": 16},
  "chord": {"raw": "F#m7b5", "root": "F#", "quality": "m7b5", "parse_status": "ok"},
  "events": [
    {
      "id": "n012_01",
      "voice_id": "melody",
      "onset_tick": 0,
      "duration_tick": 240,
      "pitch_spelling": "E4",
      "midi": 64,
      "tie_group_id": null,
      "tuplet": null,
      "confidence": 0.93
    }
  ]
}
```

---

## 参照URL（WebSearchで実在確認済み）

- Libretto: Giving LLM Agents a Sense of Musical Structure — https://arxiv.org/abs/2606.22708
- ChatMusician: Understanding and Generating Music Intrinsically with LLM — https://arxiv.org/abs/2402.16153
- MuPT: A Generative Symbolic Music Pretrained Transformer (SMT-ABC Notation) — https://arxiv.org/abs/2404.06393
- ABC-Eval: Benchmarking LLMs on ABC notation — https://arxiv.org/abs/2509.23350
- Can LLMs understand LilyPond? (LilyBench) — https://arxiv.org/abs/2606.08722
- MSU-Bench: Musical Score Understanding Benchmark — https://openreview.net/pdf/6e87af4a985e84aec4ab4dd71171b7d7f3f30279.pdf
- Carone et al., "LLMs can read music, but struggle to hear it" (PMLR v303, 2026) — https://proceedings.mlr.press/v303/carone26a.html （OpenReview版: https://openreview.net/pdf?id=hKE8tQzueC ）
- A Survey of Foundation Models for Music Understanding — https://arxiv.org/pdf/2409.09601
- MusicXML (W3C Community Group) — https://www.w3.org/2021/06/musicxml40/
- MEI (Music Encoding Initiative) — https://music-encoding.org/
- Humdrum `**kern` — https://www.humdrum.org/rep/kern/
- ABC notation standard v2.1 — https://abcnotation.com/wiki/abc:standard:v2.1
- LilyPond — https://lilypond.org/
- Tone.js @tonejs/midi (MIDI-as-JSON) — https://github.com/Tonejs/Midi
- MusPy (note representation) — https://github.com/salu133445/muspy
- Strudel (mini-notation, live coding) — https://strudel.cc/

### 実在を確認できなかった / 要注意

- **「moe-fumen / 萌え譜面」**: 音楽採譜の汎用構造化テキスト規格としての実在URLは確認できず。検索ではリズムゲーム譜面用語や `hbjpn/fumen`（太鼓さん次郎系の譜面ライブラリ）がヒット。採譜exportの参照規格として採用する前に、依頼元の定義・出典の再確認が必要。捏造回避のため本ドキュメントでは「非標準/要検証」として扱う。
