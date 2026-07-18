> 【歴史的記録】本書は作成時点の前提・知見に基づくスナップショットです。その後の決定により一部前提は更新されています。現在の前提は `README.md`・`docs/requirements/product-vision.md`・`docs/research/gate-execution-spec.md`(最新改訂) を参照してください。

Slack投稿は試みましたが、この環境では `send_message` 相当のSlack送信ツールが公開されていないため未実行です。

# AI採譜アプリ UI/UX設計リサーチ

## 1. マイクロインタラクション

| 原則 | 根拠 | 採譜アプリへの適用案 |
|---|---|---|
| 小さな操作を「トリガー、ルール、フィードバック、ループ/モード」に分解する | Dan Saffer『Microinteractions』は4要素を提示。[O'Reilly](https://www.oreilly.com/library/view/microinteractions/9781449342760/ch02.html) | 「音符をドラッグ」「AI候補を採用」「小節を分割」ごとに、発火条件、制約、反応、継続状態を仕様化する |
| モーションは意味を持つべき | Material motion は responsive/natural/aware/intentional、短く明確な遷移を推奨。[Material](https://m1.material.io/motion/material-motion.html) | 音符移動は吸着、補正、確定の3段階をアニメーションで示す。装飾目的の揺れは避ける |
| フィードバックは重要度に応じて強弱を変える | Apple HIG は状況、成功/失敗、警告を明確に伝え、重大度と提示方法を合わせる。[Apple Feedback](https://developer.apple.com/design/human-interface-guidelines/feedback) | AI採譜完了は控えめなバナー、保存失敗や破壊的操作は明確な警告、音符単位の修正は局所ハイライト |
| 「気持ちよさ」は応答性、音、視覚効果、物理感の複合 | Juicy design は豊富な視聴覚フィードバックを扱う研究。[DiGRA](https://dl.digra.org/index.php/dl/article/view/936/)、[Game Feel解説](https://eolt.org/articles/game-feel/) | 音符を置いた瞬間に短い試聴音、吸着時の軽いスナップ、再生ヘッドの滑らかな追従を入れる。ただし過剰演出は編集精度を邪魔しない範囲にする |

## 2. 色による機能区分

| 原則 | 根拠 | 採譜アプリへの適用案 |
|---|---|---|
| 色は意味で固定し、同じ色を別用途に使わない | Apple HIG Color は一貫した色意味、ダーク/高コントラスト対応、色だけに頼らない設計を推奨。[Apple Color](https://developer.apple.com/design/human-interface-guidelines/color) | 青=再生/ナビ、緑=確定済み、黄=要確認、赤=エラー、紫=AI提案など、意味を固定 |
| セマンティックカラーは装飾ではなく状態伝達に使う | Adobe Spectrum は positive/negative/notice/informative などの意味色と、アイコン/テキスト併用を推奨。[Spectrum](https://spectrum.adobe.com/page/color-system/) | AI信頼度を色だけで表さず、形状、アイコン、ラベルも併用する |
| 色覚多様性には二重符号化が必須 | WCAG 2.2 は色だけで情報を伝えないこと、4.5:1の通常文字コントラスト等を規定。[WCAG 2.2](https://www.w3.org/TR/WCAG22/) | 「AI低信頼」は黄色だけでなく点線枠、「人間確認済み」は緑だけでなくチェックアイコン |
| 音楽ソフトは色を整理・識別に使う | Logic はトラック種別/整理に色を使い、Mixerにも連動。[Logic Track Colors](https://support.apple.com/guide/logicpro/change-track-colors-lgcp7a5a5423/10.7/mac/11.0)。Ableton は自動トラック/クリップ色を持つ。[Ableton Theme & Colors](https://www.ableton.com/en/manual/first-steps/) | パート別色、声部別色、AI状態色を衝突させない。色レイヤーを「パート色」と「状態オーバーレイ」に分ける |

## 3. 音楽ソフト特有のUXパターン

| パターン | 根拠 | 採譜アプリへの適用案 |
|---|---|---|
| タイムライン、波形、MIDI/ピアノロール、楽譜の同期 | Logic は Audio/Piano Roll/Score Editor を主要編集ビューとして提供。[Logic Guide](https://help.apple.com/logicpro/mac/) | 3ビュー同期を基本にする。波形で選択した範囲が譜面小節とピアノロール音符に即反映される構造 |
| プレビューは編集と同じ場所で鳴る | Ableton MIDI Note Editor はPreviewオンでキーやノート移動時に発音。[Ableton MIDI Editing](https://www.ableton.com/en/live-manual/12/editing-midi/) | 音符ドラッグ中に対象ピッチを短く鳴らす。和音編集では変更後の和音を即試聴 |
| 非破壊編集を基本にする | Ableton clip envelopes は元サンプルを変えずリアルタイム処理。[Ableton Clip Envelopes](https://www.ableton.com/en/live-manual/12/clip-envelopes/)。Logic Audio File Editor は破壊的編集を明記。[Logic Audio File Editor](https://support.apple.com/en-euro/guide/logicpro/lgcp21587d1c/mac) | 元音声、AI下書き、人間編集を別レイヤー化。書き出しまで原音とAI候補を保持 |
| Undoは履歴として見えるべき | Logic は最大200ステップのUndo Historyを持つ。[Logic Undo](https://support.apple.com/guide/logicpro/undo-and-redo-edits-lgcp1dbd67ab/mac) | 「AI再解析」「音符移動」「小節分割」など意味単位でUndo Historyに残す |
| ドラッグには物理的な制約が必要 | Ableton はグリッドスナップ、バイパス修飾キー、クリップ端ドラッグ等を明確化。[Ableton Arrangement](https://www.ableton.com/en/manual/arrangement-view/) | 音符は拍グリッド、近傍ピッチ、声部規則へ吸着。修飾キーで一時的に自由移動 |

## 4. AI下書きから人間仕上げへのUX

| 原則 | 根拠 | 採譜アプリへの適用案 |
|---|---|---|
| AIの能力と限界を先に示す | Microsoft HAX は「何ができるか、どの程度できるか」を明確にする。[HAX](https://www.microsoft.com/en-us/haxtoolkit/ai-guidelines/) | 初回解析前に「リズム推定は要確認」「ポリフォニーは信頼度低下しやすい」などを短く提示 |
| 信頼度表示は有用な場面に絞る | Google PAIR は信頼度表示が判断を助ける一方、誤解も生むためテストを推奨。[PAIR Explainability](https://pair.withgoogle.com/guidebook-v2/chapter/explainability-trust/) | 全音符に数値%を出さず、低信頼箇所だけ帯/点線/候補数で示す |
| 提案は受入、却下、修正、再試行できる | Apple GenAI HIG はEdit/Undo/Retry/Adjustを近くに置くことを推奨。[Apple Generative AI](https://developer.apple.com/design/human-interface-guidelines/generative-ai) | 小節単位で「採用」「別候補」「手修正」「この範囲だけ再解析」を配置 |
| AI出力は人間レビュー対象として扱う | Copilot Review はAIがコメントし、人間が適用/破棄できる。[GitHub Docs](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review) | AIを「確定譜面」ではなく「レビュー待ち下書き」と表示。人間確認済みだけ濃く表示 |
| 差分と候補を見せる | Photoshop Generative Fill は非破壊生成とバリエーション選択を提供。[Adobe Photoshop](https://helpx.adobe.com/uk/photoshop/desktop/create-open-import-images/create-images/edit-images-with-generative-fill.html) | 再解析後は旧譜面との差分を赤/緑ではなく、追加/削除形状とラベルで表示 |

## 5. 実装制約

| 選択肢 | 制約/根拠 | 採譜アプリへの判断 |
|---|---|---|
| Electron | 公式Performance GuideはCPU/メモリ/起動/入力応答の最適化を重視。[Electron](https://www.electronjs.org/docs/latest/tutorial/performance) | Web技術で高速に作れるが、波形描画とAI処理はWorker/ネイティブ分離が必要 |
| Tauri | OS WebView利用。WebView差異に注意。[Tauri WebView](https://v2.tauri.app/reference/webview-versions/)、[Benchmark](https://tauri-apps.github.io/benchmark_results/) | 軽量配布に向くが、macOS/WindowsのWebView差を吸収する設計が必要 |
| Web Animations / CSS | 60fpsは16.7ms以内。`transform`/`opacity`が安全。[MDN Animation Performance](https://developer.mozilla.org/en-US/docs/Web/Performance/Guides/Animation_performance_and_frame_rate) | 音符、カーソル、選択枠はtransform中心。波形再描画はCanvas/WebGLで差分更新 |
| Framer Motion / Motion | transform/opacity中心、WAAPI活用が高性能。[Motion Performance](https://motion.dev/docs/performance) | React UIなら状態遷移に有効。ただし大量音符の個別アニメーションは仮想化する |

# 採譜アプリのUI/UX設計原則 10箇条

1. 操作は必ず即時反応させる。根拠: Material motion、MDN 60fps。
2. 音符編集は「見る、聴く、触る」を同時に返す。根拠: Apple Feedback、Ableton Preview、Game Feel。
3. 色は機能区分ではなく意味体系として設計する。根拠: Apple Color、Spectrum、Fluent。
4. 色だけで状態を伝えない。根拠: WCAG 1.4.1、Apple Color。
5. AI下書きは確定譜面と視覚的に分ける。根拠: Apple Generative AI、Microsoft HAX。
6. 低信頼箇所だけを目立たせ、全部を警告色にしない。根拠: PAIR confidence guidance。
7. 波形、ピアノロール、楽譜は常に同じ時間軸で同期する。根拠: Logic Editors、Ableton Arrangement。
8. 編集は非破壊を基本にし、書き出し時だけ確定する。根拠: Ableton Clip Envelopes、Logic Audio File Editor。
9. Undoは技術操作ではなく音楽的意味単位で残す。根拠: Logic Undo History。
10. 気持ちよさは装飾ではなく、応答時間、吸着、試聴音、短いモーションの整合で作る。根拠: Saffer、Apple Motion、DiGRA juicy design。
