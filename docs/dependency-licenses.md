# 依存部品・モデルのライセンス台帳（NF-029）

**最終更新:** 2026-07-21
**目的:** Pitchsieve（採譜エンジン）が利用する依存ライブラリ・モデルのライセンスを台帳化し、
配布時のコピーレフト条件（特に LGPL）の扱いを明示する。本体は Apache-2.0 で公開。

> 判定は `spike/ear-pipeline/requirements.txt` と各パッケージの配布メタデータ（`importlib.metadata`）
> に基づく実測。バージョンは 2026-07-21 時点。

## コア依存（`requirements.txt`）

| パッケージ | バージョン | ライセンス | 種別 | 備考 |
|---|---|---|---|---|
| numpy | 2.4.6 | BSD-3-Clause | 寛容 | |
| scipy | 1.18.0 | BSD-3-Clause | 寛容 | |
| librosa | 0.11.0 | ISC | 寛容 | 音声解析 |
| music21 | 10.5.0 | BSD-3-Clause | 寛容 | 記譜・MusicXML |
| pretty_midi | 0.2.11 | MIT | 寛容 | MIDI |
| soundfile | 0.14.0 | BSD-3-Clause | 寛容 | libsndfile(LGPL)を同梱 ※ |
| pypdf | 6.14.2 | BSD-3-Clause | 寛容 | PDF結合 |
| lxml | 6.1.1 | BSD-3-Clause | 寛容 | XML |
| **CairoSVG** | 2.9.0 | **LGPL-3.0-or-later** | **コピーレフト** | SVG→PDF。下記「LGPLの扱い」参照 |
| **verovio** | 6.2.1 | **LGPL-3.0** | **コピーレフト** | 楽譜浄書。[ADR-004](architecture/ADR-004-verovio.md) 参照 |
| pytest / pytest-cov | 9.1.1 / 7.1.0 | MIT | 寛容 | 開発時のみ（配布物に含めない） |

※ soundfile 自体は BSD だが、同梱される C ライブラリ libsndfile は LGPL-2.1。動的リンクのため
再リンク可能性を保てば LGPL 条件を満たす。

## オプション依存（機能を使う場合のみ）

| パッケージ | ライセンス | 用途（要件） | 備考 |
|---|---|---|---|
| basic-pitch | Apache-2.0 | 多声検出 `--engine poly`（F-010） | Spotify。別 venv(Python 3.12) |
| demucs | MIT | ステム分離 `--stem`（F-003） | 別 venv |
| PyGuitarPro | **LGPL-3.0** | GP5 出力 `--format gp5`（F-051） | コピーレフト。下記参照 |
| sounddevice | MIT | マイク録音 `record`（F-005） | PortAudio(MIT様)に依存 |

## モデル・学習データ

| 項目 | 状況 |
|---|---|
| 独自学習モデル | **なし**（学習は未実施）。NF-025（学習データのライセンスクリーン）は現状「該当なし」 |
| basic-pitch の事前学習モデル | Apache-2.0（Spotify 配布物に同梱） |

## LGPL 部品の扱い（配布時の要点）

本体（Apache-2.0）が LGPL 部品（**verovio / CairoSVG / PyGuitarPro / libsndfile**）を使う場合、
LGPL を維持するための一般的条件は次のとおり:

- **動的リンク／別プロセス呼び出し**を保ち、利用者が当該 LGPL 部品を差し替え（再リンク）できる状態にする。
- LGPL 部品のソース入手方法を配布物に明記する（各プロジェクトの公開リポジトリで足りる）。
- 本体コードを LGPL 化する必要はない（LGPL は「そのライブラリの改変部の開示」を求めるもので、
  利用側アプリのライセンスは縛らない）。
- verovio は wheel 同梱のため、配布形態により再リンク条件の解釈に注意（[ADR-004](architecture/ADR-004-verovio.md)）。

> **結論:** コア機能（MusicXML/MIDI/五線譜PDF/TAB）の依存は寛容ライセンス中心（NF-026 ✅）。
> LGPL は浄書(verovio/CairoSVG)と GP5 出力(PyGuitarPro)に限定され、いずれも
> 動的リンク／別プロセスで条件を満たせる。商用同梱を行う場合のみ再リンク可能性を再確認すること。
