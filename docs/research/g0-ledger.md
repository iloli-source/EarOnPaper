# G0' 実施台帳

**実施日:** 2026-07-19（機械パート実施済み。残作業は末尾）
**実施方式:** AIの耳ハーネスによる二段判定の第一段（客観指標）。第二段（ユーザー聴き比べ）は未実施
**関連:** g0-prime-kit.md（手順）/ gate-execution-spec.md 改訂3（判定基準）/ Issue #13

## 1. 選曲記録（公式アップロードのみ）

| 曲ID | 用途セル | 曲名 | チャンネル（公式確認） | 長さ | URL | 選定理由 |
|---|---|---|---|---|---|---|
| u1 | U1 ピアノ | Joe Hisaishi - Summer | **Joe Hisaishi Official**（公式） | 4:03 | youtube.com/watch?v=l0GN40EL1VU | ピアノ主体・中庸テンポ・スタジオ品質。キットの「ピアノソロカバー」枠は公式音源の制約から公式ピアノ曲に置換（理由: 公式アップロード限定のユーザー承認条件を優先） |
| u2 | U2 弾き語り | Jack Johnson - Better Together | **jackjohnsonmusic**（公式アーティスト） | 3:28 | youtube.com/watch?v=RSsTx2TBrww | ボーカル＋アコースティックギターの2要素・コード進行明確 |
| u4 | U4 バンド | Official髭男dism - ノーダウト | **OFFICIAL HIGE DANDISM**（公式） | 3:19 | youtube.com/watch?v=EHw005ZqCXk | ドラム・ベース・ギター・鍵盤・ボーカルの多楽器ポップバンド編成・2-4分内 |

**法的整理:** 全曲アーティスト公式チャンネルからの取得。私的な検証目的（30条1項の私的使用の範囲）で端末内処理のみ。音源・出力はgit管理外（tools/ai-ears/testdata/g0/、gitignore済み）・外部送信なし・出力譜面の公開/配布なし。外部AI（Gemini等）への音源送信も行っていない。

## 2. ツール実行記録

| ツール | 結果 | 詳細 |
|---|---|---|
| MuScriptor | **ブロック（未実行）** | pip導入成功（Python3.12 venv）だがモデル重み（small/medium/large全て）がHugging Faceの**アクセス制限付き** — HFアカウントでの利用規約同意＋認証トークンが必要。→ 残作業①（ユーザーのHF数クリック or トークン提供） |
| Basic Pitch (Spotify) | **成功** | 非ゲートOSS（Apache-2.0）。spec上のOSS下限参照ツール。ONNXバックエンド・3曲合計28秒で採譜完了。導入時の互換問題2件を解決（setuptools<81固定・scipy==1.12固定）＋ONNXモデルパス明示が必要（ハーネスREADMEに追記推奨） |
| MuseScore audio2score β | **未実行** | GUI/オンライン変換のため。→ 残作業② |

## 3. AIの耳スコア（第一段判定・Basic Pitch）

| 曲 | 総合 | 音高一致 | 音の出だし一致 | テンポ整合 | 譜面健全性 |
|---|---|---|---|---|---|
| u1 ピアノ | **0.767** | 0.863 | 0.415 | 0.978 | 1.0 |
| u2 弾き語り | **0.739** | 0.838 | 0.367 | 0.932 | 1.0 |
| u4 バンド | **0.693** | 0.912 | **0.162** | 0.790 | 1.0 |

詳細レポート: tools/ai-ears/testdata/g0/reports/（git外）

### 読み取り（暫定・第一段のみ）

- **音高（耳の音程部分）は3曲とも0.84-0.91で「部分一致〜ほぼ同じ曲」水準** — 音の高さ自体はOSS下限ツールでもかなり拾えている
- **音の出だし（リズム側）が全曲で低く、編成が複雑なほど崩壊**（ピアノ0.42→バンド0.16）— リサーチの結論「全社共通の弱点はリズム・整譜」とAIの耳の実測が一致
- **二層切り分けの暫定示唆: 崩れは「耳の音程」より「リズム/記譜」起因が優勢**（ハーネスの既知の限界: 出だし一致の絶対値は辛めに出る傾向。ツール間相対比較が本来の用途のため、MuScriptor/MuseScoreβが加わった時点で確定判断する）

## 4. 残作業（判定確定まで）

1. **MuScriptor**: ユーザーのHuggingFaceアカウントでモデル利用規約に同意しトークンを設定（数クリック）→ AIが再実行
2. **MuseScore audio2score β（NoteVision）**: 自動化不可＝ユーザー手動。詳細は末尾「§6 MuseScoreβ手順書」参照。
3. **第二段判定=ユーザー聴き比べ**: 各曲「元音源 → 採譜結果の再生音」を聴き比べ3段階記録。再生ペアは準備済み — 元: testdata/g0/uX.wav / 採譜再生: testdata/g0/renders/uX_basicpitch_render.wav
4. 3ツール揃った時点で相対比較→封緘ルール（kit §4）で判定

## 5. 判定（未確定）

第一段の暫定値のみ。封緘ルールでの判定は残作業1-3の完了後に行う。**現時点の暫定観察: OSS下限ツールでも「音の高さは大体合うがリズムが崩れる」— これは本プロジェクトの勝負所（リズム/整譜・選択的抽出）が実在する方向の証拠だが、競合上位ツール（MuScriptor/MuseScoreβ）の実測を待って判断する。**

## 6. MuseScoreβ手順書（自動化不可のためユーザー手動）

**偵察結果（2026-07-19実施）**
- 「Import audio to score」の実体は MuseScore.com の Web機能「**NoteVision**」。エントリーは **https://musescore.com/upload** の「Convert」欄にある **「Audio to MSCZ（Beta）」** ボタン。MuseScore Studio 4.7.4 の File メニューからも同URLへ飛ぶ。
- **自動化不可の理由:** ボタン押下で即「無料アカウント作成／ログイン」モーダルが出る＝**ログイン必須**。ユーザーの現Chromeセッションはmusescore.comにサインイン途中（ユーザー名未作成・希望名「kurachi」が使用済みで停止中）で、使えるログイン状態ではない。制約により新規アカウント作成は行わないため、AI自動実行はここで打ち切り。
- **料金/制限:** 従来は完全無料。現在は「無料枠（アップロード回数に上限あり・具体数は非公表）＋ MuseScore Pro Plus は無制限」へ移行中。出力は **MSCZ**（MusicXML書き出しの明記なし。MSCZをMuseScore Studioで開けば内部でMusicXML/MIDI相当に変換可）。3曲の検証は無料枠内で十分収まる想定。
- **音源準備済み:** WAV（35-42MB）はアップロード上限に触れる恐れがあるため 192kbps MP3 に変換済み → `tools/ai-ears/testdata/g0/musescore/u1.mp3 u2.mp3 u4.mp3`（各5-6MB）。

**そのままなぞれる操作手順（ユーザー実施）**
1. https://musescore.com/upload を開く（またはMuseScore Studio 4.7.4の File → Import audio to score）。右上「ログイン」から自分のアカウントでサインインを完了する（ユーザー名作成が必要なら別名を設定。※本作業はkurachiでなくても可）。
2. 「Convert」欄の **「Audio to MSCZ（Beta）」** をクリック。
3. ファイル選択で `…/採譜/tools/ai-ears/testdata/g0/musescore/u1.mp3` をアップロード → AI変換を待つ。
4. 変換結果画面で **MSCZをダウンロード**。保存先: 同じ `musescore/` フォルダに `u1.mscz` として保存。
5. u2.mp3・u4.mp3 で 2-4 を繰り返し、`u2.mscz` `u4.mscz` を同フォルダに保存。
6. 完了後にこのセッション（またはAI）へ「3曲のmsczを保存した」と伝える → AIが ears.py で評価し、本台帳「§2 ツール実行記録」のMuseScoreβ行と「§3」スコア表を更新して封緘判定に進む。

**AI側の後続手順（msczが揃い次第）:** 各msczをMuseScore CLIで `--export-to uX_musescore.mid`（またはMusicXML）へ変換 → ears.py に既存Basic Pitchと同じ参照で投入 → 3ツール相対比較で判定確定。
