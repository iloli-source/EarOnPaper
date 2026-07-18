# F-098 歌声合成エクスポート受入マトリクス調査（Issue #20）

**調査日:** 2026-07-19
**目的:** F-098（歌声合成向けエクスポート）の受入条件を「エディタ別×形式×要素」の可否マトリクスとして確定するための一次調査。codex批判(round2)で「SynthV/OpenUTAU/VOCALOID別のインポート可否・受入マトリクスがない」と指摘された未定義部分を埋める。
**方法:** 各エディタの公式ドキュメント・公式FAQ・コミュニティ資料のWeb調査。**実機検証は未実施**（受入条件確定前に要実測。本書は設計ドラフト）。

---

## 1. エディタ別インポート対応（調査結果）

### Synthesizer V Studio（Dreamtonics）

- インポート対応: **MIDI / UST / VSQX / VPR / CCS**、トラック追加として SVP / S5P。SV Studio 2 Pro は **MusicXML** も対応
- 歌詞: MIDI経由は取り込み精度に制限あり。**MusicXMLの方が歌詞を正確に取り込める**（英語基準。言語により変動）と公式マニュアルが明記
- 出典: [SV Studio 2 公式マニュアル](https://svdocs.dreamtonics.com/en/synthv/basic-usage/project) / [非公式マニュアル](https://manual.synthv.info/quickstart/managing-tracks/) / [Dreamtonicsフォーラム](https://forum.dreamtonics.com/t/can-synthesizer-v-import-midi-files-with-lyrics-in-them-karaoke-files/1096)

### OpenUTAU

- インポート対応: **USTX / UST / VSQX**（Import Tracks）、**MIDI**（Import MIDI）
- USTX はYAMLベースで音符・ダイナミクス・ビブラート・ピッチ・歌詞を保持
- 出典: [OpenUtau Wiki Getting Started](https://github.com/stakira/OpenUtau/wiki/Getting-Started) / [USTX形式](https://fileinfo.com/extension/ustx)

### VOCALOID6（Yamaha）

- インポート対応: **VSQX**（V3/V4）/ **VPR**（V5）/ **MIDI**（テンポ・拍子情報の取り込み対応、**歌詞の文字エンコーディング選択機能**あり）/ ppsf（6.9.0以降）
- 非対応: VSQ（V2）・V1形式
- 出典: [VOCALOID公式FAQ(旧版ファイル)](https://www.vocaloid.com/en/support/faq/603) / [SMFインポート](https://www.vocaloid.com/en/support/faq/308) / [テンポ・拍子の取り込み](https://www.vocaloid.com/en/support/faq/312)

### 参考: 変換ハブの既存実装

- **UtaFormatix3**（OSS）が UST/USTX/VSQX/VPR/CCS/MusicXML/MIDI 等の相互変換を実装済み。フォーマット仕様の参照実装・変換層の再利用候補（ライセンス確認のうえ）
- 出典: [utaformatix3](https://github.com/sdercolin/utaformatix3)

## 2. 受入マトリクス（形式 × 要素）

凡例: ◎=公式に対応 / ○=対応するが制限・精度注意 / △=形式上は保持されるがエディタ側の扱い要実測 / ×=非対応 / **?=今回の調査では確認できず（要実測）**

| 要素 | MIDI | MusicXML | UST | USTX | VSQX |
|---|---|---|---|---|---|
| 音符（音高・音価） | ◎（全エディタ） | ◎（SynthVのみ） | ◎（OpenUTAU） | ◎（OpenUTAU） | ◎（SynthV/V6/OpenUTAU） |
| 歌詞 | ○（SynthV=精度制限あり・V6=エンコーディング選択） | ◎（SynthV。MIDIより正確と公式明記） | ◎ | ◎ | ◎ |
| テンポ | ◎ | ◎ | ◎ | ◎ | ◎ |
| 拍子 | ◎（V6公式FAQで確認） | ◎ | △ | △ | ◎ |
| ピッチベンド（連続ピッチ） | ? （MIDI PB搬送は可能だが歌声エディタが自声ピッチを再生成するのが通例） | × | ○（mode2ピッチ） | ◎（pitch保持） | △ |
| ブレス | ? （標準的な搬送手段なし） | × | ? | ? | ? |
| ダイナミクス | ○（velocity/CC） | △ | ○ | ◎ | △ |

## 3. F-098 受入条件ドラフト（要件v3反映用）

F-098の受入条件は「全要素完全転送」ではなく、**要素をTier分けして段階保証**する:

- **Tier1（必須・受入テスト対象）:** 対象3エディタ（SynthV Studio / OpenUTAU / VOCALOID6）で、エクスポートしたファイルが**警告なく開け、音符（音高・音価）・テンポ・拍子が保持される**こと
  - 実現形式: **MIDI（歌詞メタイベント付き・エンコーディングはUTF-8/Shift_JIS選択可）を共通経路**とし、OpenUTAU向けに**UST/USTX**を追加提供
- **Tier2（Should）:** 歌詞の保持。SynthV向けは**MusicXML経路**（公式が「MIDIより正確」と明記）を優先提供。日本語歌詞はかな正規化オプション
- **Tier3（明示的にスコープ外＝v1では保証しない）:** 連続ピッチカーブ・ブレス・ダイナミクスの転送（歌声エディタ側がピッチを再生成する設計が通例のため。将来USTXのpitch書き出しで部分対応の余地）
- **検証手順（受入テスト）:** 基準曲（歌詞つき単旋律・転調/拍子変更を含む）をエクスポート→各エディタ実機でインポート→音符数一致・歌詞文字化けゼロ・テンポ/拍子一致を確認。**?セルは実機検証で埋めてから受入条件を封緘**

## 4. 残課題（正直な記録）

- ピッチベンド・ブレスの各エディタ実挙動（マトリクスの?セル）は**実機検証が必要**（各エディタの無料版/体験版で検証可能）
- UtaFormatix3のライセンスと再利用可否の確認（変換層を自作するか流用するか）
- CeVIO/NEUTRINO等の追加エディタ対応は観測リスト扱い（需要シグナル待ち）
