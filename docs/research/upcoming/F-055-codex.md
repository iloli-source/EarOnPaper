# 機能「MuseScoreワンクリック連携（ローカルファイル受け渡し・online変換を経路に含めない）」論文＋WEB調査報告（codex担当）

**調査日:** 2026-07-21
**対象:** 採譜アプリの出力を **オンライン/クラウド変換を一切経由せず**、ローカルに `MusicXML` / `MIDI` / `.mscz` を書き出して MuseScore（または他記譜ソフト）でワンクリックで開く連携。
**担当:** codex（OpenAI Codex 読取りセッション `cwd=採譜` ＋ WebSearch / WebFetch による一次情報検証）
**方針:** 実在情報のみ・URL併記・**捏造禁止**・**失敗例を最大化**。英語中心・中国語補完。未確認は「未確認」と明記。

---

## 0. 調査範囲と検証状況（重要）

| 項目 | 内容 |
|------|------|
| Codex実行 | `mcp__codex__codex`（read-only）成功。ローカル調査＋WebFetch検証を併用したレポートを取得。 |
| 一次検証 | GitHub Issue #22857 は WebFetch で本文確認済み（★）。MuseScore Handbook / W3C / Apple 開発者文書も本文確認済み。 |
| bot 403 | `musescore.org/en/node/...` フォーラムは bot 403 で本文未取得のものが多い（WebSearch要約経由）。該当は「検索経由・本文未確認」と注記。 |
| 学術 | 「記譜ソフトのファイル連携UX」を直接扱う査読論文はほぼ皆無。**記号音楽フォーマット変換の fidelity 論文**は存在（Fang/Vigliensoni/Fujinaga 等）。連携失敗の主軸は GitHub Issue・公式Help・フォーラム。 |
| 二層モデル | 「ファイルが開けた（起動成功）」と「楽譜が正しく再現された（import成功）」は**別レイヤ**。混同が事故源。ワンクリック＝手直しゼロは幻想。 |

---

## 1. MusicXML を MuseScore で開く時の非互換・失敗（本機能の最大リスク）

MuseScore 公式自身が「MusicXML は音符・楽器はかなり再現するが、**見た目を元通りにするには通常クリーンアップが必要**」と明記している。つまり MusicXML import は**編集の開始点であり完成譜の完全復元ではない**。

> "it is usually necessary to do some clean-up work to make the transferred score look exactly the same as the original."
> — MuseScore Studio Handbook: Working with MusicXML files（本文確認済み）
> https://handbook.musescore.org/file-management/working-with-musicxml-files

### 1.1 具体的な失敗例（実 Issue / フォーラム）

| 失敗 | 根拠URL | 検証 | 実装上の意味 |
|---|---|---|---|
| **存在しない休符・連符を追加し「corrupt」と誤判定** | GitHub #22857 | ★本文確認 | importは元XML完全保持でない。corruption誤検知あり |
| whole-measure rest（type=whole・duration不一致）で腐敗（Sibelius 7.1.3 direct export起因） | https://musescore.org/en/node/64201 | 検索経由 | Sibelius由来XMLは要正規化 |
| incorrect note types でのimport腐敗 | https://musescore.org/en/node/100971 | 検索経由 | duration/type/dots整合を出力側で担保 |
| irregular triplet import でタイミング不整合・腐敗 | https://musescore.org/en/node/69566 | 検索経由 | tupletsは必須テストケース |
| **export が hidden rests を追加し voice がずれる** | GitHub #28305 | 検索経由 | round-trip前提を捨てる |
| MusicXML export で **最終 vertical frame（歌詞含む）が消失** | GitHub #13715 | 検索経由 | 末尾テキスト/歌詞frameは要確認 |
| no-beam（連桁なし）情報が import で消失 | https://musescore.org/en/node/298438 | 検索経由 | beam情報の往復は不安定 |
| beam properties が固定化し編集しづらくなる | https://musescore.org/en/node/100901 | 検索経由 | beam情報を出し過ぎると編集性低下 |
| **nested tuplets 未対応**（入れ子連符） | GitHub #22671 | 検索経由 | 入れ子連符は避けるか展開して出力 |
| triplet import 不具合 | https://musescore.org/en/node/13996 | 検索経由 | 三連符は fixture 化 |
| コード記号が MuseScore 4 で不可視（MS3 は問題なし） | https://musescore.org/en/node/342157 | 検索経由 | リードシートはQA対象 |
| hidden chord symbols が MS4 で export されない（MS3はしていた） | https://musescore.org/en/node/358824 | 検索経由 | 非表示要素はhandoff前に可視化検討 |
| MusicXML import で楽器が誤って非表示化 | GitHub #16135 | 検索経由 | パート可視性を検証 |
| import で楽器欠落（Finale Notepad 由来 等） | https://musescore.org/en/node/285676 | 検索経由 | 他ソフト由来XMLの楽器確認 |
| round-tripでページサイズ非保持・テキストボックス入れ替わり | https://musescore.org/en/node/351267 | 検索経由（Codex） | レイアウトは再構築前提 |
| **`.mxl` を開くと無言クラッシュ**（4.1.1/3.6.2は動作、4.2.0以降で発生とのコメント） | GitHub #30693 | 検索経由（Codex） | バージョン別実機テストが必須 |
| MusicXML import/export 課題の統括Issue（EPIC） | https://musescore.org/en/node/270643 | 検索経由 | 継続的な既知課題群 |

**中国語圏の観測:** 中国語の「機能トラブル実務ログ」は薄く、公式Help／music21 導入記事（例: https://zhuanlan.zhihu.com/p/676873982 ）に情報が偏在。失敗事例の一次情報は英語 GitHub / musescore.org が主軸。

### 1.2 `.musicxml` / `.mxl` / `.mscz` の違いとリスク

| 形式 | 性質 | リスク |
|---|---|---|
| `.musicxml` | 非圧縮 MusicXML（W3C推奨拡張子） | サイズ大だがデバッグ容易 |
| `.mxl` | ZIP圧縮 MusicXML。W3C仕様で `META-INF/container.xml`・mimetype・UTF-8名の規則あり | ZIP構造/mimetype不備でimport失敗し得る |
| `.mscz` | MuseScoreネイティブ圧縮 | 外部生成は**バージョン互換が重い**。前方互換なし（MS4はMS3を開けるが逆は不可、保存時に内部変換） |

> W3C `.mxl` container 仕様: https://www.w3.org/2021/06/musicxml40/container-reference/elements/container/
> MuseScore ネイティブ形式の前方非互換: https://musescore.org/en/handbook/3/opensaveexportprint

**結論:** primary は `.musicxml`（デバッグ）/`.mxl`（配布）。`.mscz` の外部生成は非推奨。

---

## 2. 自動起動・「MuseScoreで開く」連携の落とし穴

| 失敗 | 根拠URL | 検証 | 対策 |
|---|---|---|---|
| **MuseScore4は未起動時にファイルから開けない**（ダブルクリック/Open With/Terminalで無視、起動済みなら成功） | https://musescore.org/en/node/371438 | 403本文未確認・検索要約 | 「先にapp起動→待機→open」fallback必須 |
| macOS `open -a ...mscore filename.ext` がファイル引数を無視 | GitHub #15465 | 検索経由 | macは起動後にファイルを渡す設計に |
| headless変換が MS3→MS4 で回帰（空ファイル化） | GitHub #16975 | 検索経由（Codex） | one-click open と headless変換を混同しない |
| **MS4でCLI headlessが動かない**（`-platform offscreen` がMS4で無効化、`QEventLoop: Cannot be used without QApplication`） | GitHub #17247 / #15367 | 検索経由 | Linuxは `export QT_QPA_PLATFORM=offscreen` or Xvfb |
| CLI `-o/--export-to` は**GUIを開かない converter mode**。「開く」用途に不適 | https://handbook.musescore.org/en_gb/appendix/command-line-usage | 検索経由（Codex） | 起動には `-o` を使わない |
| CLI引数順依存で無反応（`--export-to output input` 順） | https://musescore.org/en/comment/1187626 | 検索経由（Codex） | subprocessは配列で固定順 |
| Store/WinGet版で実行ファイルパスが不明瞭 | GitHub #27994 | 検索経由（Codex） | `PATH`前提禁止・実行ファイル探索＋手動指定 |
| OSファイル関連付けがMS3/MS4で入れ替わる誤認 | https://musescore.org/en/node/358151 | 検索経由（Codex） | 既定アプリ依存を第一手段にしない |
| MS3とMS4を同時起動できない | https://musescore.org/en/node/351721 | 検索経由 | 併存環境で衝突しうる |
| macOS Gatekeeper：外部DLアプリ初回起動に署名/公証確認＋ユーザー承認 | https://support.apple.com/en-sa/guide/security/sec5599b66df/web | 検索経由（Codex） | 初回はユーザー操作が要る前提 |
| macOS App Sandbox：security-scoped bookmark無しに任意ファイル不可 | https://developer.apple.com/documentation/security/accessing-files-from-the-macos-app-sandbox | 検索経由（Codex） | handoffファイルは許可済み領域へ |

**未確認:** 「既存インスタンスに渡したファイルが必ず前面表示される」保証は今回の公式ソースで確認できず。「開いたがフォーカスしない」ケースを許容するUI設計が必要（未確認）。
**path/encoding:** 日本語/中国語パス・空白・超長パスは QA matrix に含めるべき（一般的リスク。個別バグURLは今回未特定）。

---

## 3. オンライン変換経路が望ましくない理由（＝ローカルhandoffの正当性）

| 問題 | 根拠URL | 検証 | ローカルhandoffの価値 |
|---|---|---|---|
| アップロードにログイン/公開範囲/クラウド保存が絡む | https://handbook.musescore.org/file-management/publish-to-musescorecom | 検索経由（Codex） | 第三者サービスに譜面を送らない |
| upload先は別サービス扱い・独自privacy policy | https://musescore.org/en/about/desktop-privacy-policy | 検索経由（Codex） | 企業/教育/未公開曲で重要 |
| 変換ファイルが削除できない懸念 | https://musescore.org/en/node/368780 | 検索経由（Codex） | 変換履歴を残さない |
| 変換待ち・メール通知・失敗が挟まる | https://musescore.org/en/comment/1239134 | 検索経由（Codex） | 同期的・ローカルにできる |
| PDF converter の変換品質崩れ（拍子/楽器/clef誤認） | https://musescore.org/en/node/166801 | 検索経由（Codex） | 自前XMLなら原因追跡可能 |
| 著作権/UGCライセンスの不確実性 | https://law.stackexchange.com/questions/47794/ | 検索経由（Codex） | 第三者権利曲を上げない設計が安全 |

**結論:** オンライン経路は補助にはなり得るが、**ワンクリック連携の標準経路に入れるべきではない**。

---

## 4. 標準規格・学術の観点

- MusicXML は **W3C Music Notation Community Group** が維持。MNX 等も議論中。
  https://www.w3.org/community/music-notation/
- MusicXML 4.0 で `.mxl` 内に score と parts を同梱する標準化が入った。
  https://www.w3.org/2021/06/musicxml40/version-history/40/
- **MEI vs MusicXML:** MusicXML は notation editor 間の**交換形式**、MEI は知的内容・資料構造・古記譜法に強い（研究/校訂向け）。
  https://music-encoding.org/about/
- **変換fidelityの学術報告:** Humdrum/LilyPond/MEI/MusicXML間の変換で duration・articulation・note offset の差異、変換後 parse 不能ファイルの発生が報告されている（Fang/Vigliensoni/Fujinaga）。
  https://leofang.cn/publication/effects_of_translation/
- MusicXML export 比較データセット（ornaments等の差）: https://zenodo.org/records/8305206

**含意:** 「ローカルで壊れない」保証はフォーマット仕様レベルでも存在しない。fidelity は常にツール依存で劣化しうる。

---

## 5. 推奨実装仕様（本機能向け）

1. **完全ローカル保証** — 変換サーバー/musescore.com upload/web importer を標準経路に入れない。UI に「ファイルはローカル保存され MuseScore に渡されます」と明記。
2. **出力形式** — Primary: `.musicxml`（デバッグ）/`.mxl`（配布）。Playback確認: `.mid`。`.mscz` の外部生成は非推奨。
3. **MusicXML 品質ゲート** — XSD/DTD validation に加え duration/type/dots/tuplet 整合チェック。fixture: tuplets（入れ子含む）・lyrics・末尾frame・chord symbols（hidden含む）・beaming・slur/spanner・repeat/barline・grace/percussion/TAB・大編成。
4. **起動戦略** — ①明示 MuseScore 実行ファイル起動 → ②macは `open -a MuseScore file`（未起動時は「起動→待機→再open」fallback）→ ③失敗時にOS関連付けへfallback。引数は必ず配列で固定順。**起動に `-o` を使わない**（converter mode）。
5. **失敗表示UX** — 「起動成功＝再現成功ではない」「MuseScore 3/4で結果が異なりうる」「開けない場合は File > Open から手動で」。
6. **QA matrix** — OS: Win10/11・macOS(公証)・Linux(AppImage/`QT_QPA_PLATFORM=offscreen`)。MuseScore: 3.6.2 / 4.1.1 / 4.6.x / 4.7.x。path: ASCII/日本語/中国語/空白/超長。

---

## 6. 主要出典一覧（抜粋・本文確認は★）

- ★ MuseScore Handbook: Working with MusicXML files — https://handbook.musescore.org/file-management/working-with-musicxml-files
- ★ GitHub #22857（存在しない休符追加＋corrupt誤判定） — https://github.com/musescore/MuseScore/issues/22857
- GitHub #28305 / #13715 / #22671 / #16135 / #15465 / #16975 / #17247 / #15367 / #27994 / #30693 / #18582
- musescore.org: #270643(EPIC) / #64201 / #100971 / #69566 / #298438 / #100901 / #13996 / #342157 / #358824 / #285676 / #351267 / #371438 / #358151 / #351721 / #368780 / #166801
- Handbook CLI: https://handbook.musescore.org/en_gb/appendix/command-line-usage
- W3C MusicXML CG / 4.0 / container — 上記本文参照
- Apple Gatekeeper / App Sandbox — 上記本文参照
- 学術: leofang.cn / Zenodo 8305206 / music-encoding.org
