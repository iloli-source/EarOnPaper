"""F-055 MuseScore「ワンクリック連携」用のローカルファイル受け渡し(Issue #102)。

採譜が書き出した MusicXML を、MuseScore(または他記譜ソフト)へ**ローカルで**
渡すためのハンドオフ・パッケージを準備する。online変換経路(musescore.com
アップロード/クラウド変換API等)は経路に一切含めない(NF-023)。

やること(prepare_handoff):
  1. 入力 .musicxml/.xml を検証(存在・非圧縮MusicXMLらしさ)
  2. 出力先に W3C準拠の .mxl(ZIP圧縮MusicXML)を書く。圧縮に失敗する
     環境では .musicxml をそのままコピーしてフォールバック(黙って壊れない)。
  3. 人間向けの README メモ(README_musescore.txt)を併置し、
     「開けた≠再現できた」「レイアウトは再計算」「起動の落とし穴」を明記。

先行研究(F-055-grok.md / F-055-codex.md)から反映した堅牢化:
  - 中間形式は MusicXML を正本にする。.mscz の外部生成は非推奨のため行わない
    (codex 1.2/5-2: 外部生成 .mscz はバージョン互換が重く前方互換なし)。
  - .mxl は W3C container 仕様(mimetype 非圧縮先頭・META-INF/container.xml)
    に従って自前 zip 構築する。music21 依存や ZIP 構造不備での import 失敗を避ける
    (codex 1.2/59-61: mimetype/container不備で import 失敗し得る)。
  - このモジュールは MuseScore を**自動起動しない**。起動連携は OS/バージョン依存の
    落とし穴(未起動時にファイル引数を無視・macの `open -a` がファイルを無視・
    MS4のCLIヘッドレス回帰・Gatekeeper/Sandbox)が多く、ファイル準備と分離するのが
    安全(codex 2章・grok 3.5/5.3)。起動手順は README に手動導線として記す。
  - online変換はコードパスに存在しない(codex 3章・grok 8-5)。一時ファイルも作らず
    指定 out_dir 配下のみで完結する。

原理的限界(notesにも記載):
  - 「ワンクリック=手直しゼロ」は幻想。MusicXML は論理構造は運ぶが浄書レイアウトは
    受け側で再計算される(grok 4-1/codex 1章)。本機能は「確実にローカルで開ける
    ファイルを用意する」までを保証範囲とし、譜面の完成は別工程。
"""

from __future__ import annotations

import zipfile
from pathlib import Path

# W3C MusicXML 4.0 .mxl container 仕様の固定値。
# mimetype は ZIP の先頭エントリに**無圧縮**で格納する(codex 1.2)。
_MXL_MIMETYPE = "application/vnd.recordare.musicxml"
_CONTAINER_PATH = "META-INF/container.xml"
_README_NAME = "README_musescore.txt"
# 非圧縮MusicXMLとして受理する拡張子(小文字比較)。
_XML_SUFFIXES = (".musicxml", ".xml")

# 受け渡しの注意点(研究の失敗例を人間向けに要約したREADME本文)。
_README_TEXT = """\
MuseScore ローカル受け渡しメモ(採譜 / F-055)
================================================

このフォルダのファイルは、オンライン変換を一切通さずローカルで用意されています。

■ 開き方(手動 / 最も確実)
  1. MuseScore を先に起動する。
  2. メニュー File > Open から、このフォルダの .mxl(または .musicxml)を選ぶ。
  ※ ダブルクリックや「プログラムから開く」は、MuseScore 未起動時に
    ファイル引数が無視されることがあります(未起動→起動待ち→再オープンが安全)。
    macOS では `open -a MuseScore <file>` がファイルを無視する既知の挙動があります。

■ 大事な前提
  - 「開けた」ことと「元どおりに再現できた」ことは別です。
  - MusicXML は音符・調号・拍子など論理構造は運びますが、浄書レイアウト
    (小節割り・改行・要素の配置)は受け側で再計算されます。手直し前提でお使いください。
  - MuseScore 3 と 4 で結果が異なることがあります。開けない場合は File > Open から手動で。

■ フォーマットについて
  - .mxl   : ZIP圧縮された MusicXML(配布・受け渡し用の正本)
  - .musicxml : 非圧縮 MusicXML(デバッグ用。.mxl が使えない環境向け)
  - .mscz(MuseScore ネイティブ)は外部生成しません(バージョン互換が不安定なため)。
"""


def _read_and_validate_source(musicxml_path: Path) -> bytes:
    """入力 MusicXML を読み、非圧縮MusicXMLらしさを最小検証してバイト列を返す。

    Args:
        musicxml_path: 入力する非圧縮 MusicXML(.musicxml/.xml)のパス。

    Returns:
        入力ファイルの生バイト列。

    Raises:
        FileNotFoundError: パスが存在しない/通常ファイルでない場合。
        ValueError: 拡張子が非対応、または内容がMusicXML/XMLに見えない場合。
    """
    if not musicxml_path.is_file():
        raise FileNotFoundError(f"MusicXMLファイルが見つかりません: {musicxml_path}")
    if musicxml_path.suffix.lower() not in _XML_SUFFIXES:
        raise ValueError(
            f"非圧縮MusicXML(.musicxml/.xml)を指定してください: {musicxml_path.name}"
        )
    data = musicxml_path.read_bytes()
    if not data.strip():
        raise ValueError(f"MusicXMLファイルが空です: {musicxml_path}")
    # ZIP(.mxl を誤って渡した)や非XMLを弾く。BOM を除いた先頭が '<' で始まるかを見る。
    head = data.lstrip()[:4]
    if head[:2] == b"PK":
        raise ValueError(
            "圧縮済み(.mxl)が渡されました。非圧縮MusicXMLを指定してください。"
        )
    if not head.startswith(b"<"):
        raise ValueError(f"MusicXMLとして解釈できません(XML宣言なし): {musicxml_path}")
    return data


def _container_xml(inner_name: str) -> bytes:
    """.mxl 内の META-INF/container.xml を生成する(W3C仕様の rootfile 参照)。

    Args:
        inner_name: ZIP内に格納する MusicXML の相対パス(例 "score.musicxml")。

    Returns:
        container.xml のUTF-8バイト列。
    """
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<container>\n"
        "  <rootfiles>\n"
        f'    <rootfile full-path="{inner_name}" '
        'media-type="application/vnd.recordare.musicxml+xml"/>\n'
        "  </rootfiles>\n"
        "</container>\n"
    ).encode("utf-8")


def _write_mxl(xml_data: bytes, mxl_path: Path, inner_name: str) -> None:
    """W3C準拠の .mxl(ZIP圧縮MusicXML)を書き出す。

    mimetype を先頭エントリに**無圧縮**で格納し、続けて container.xml と
    本体 MusicXML を deflate 圧縮で格納する。MuseScore の import 失敗を避けるため
    ZIP 構造・mimetype 規則(codex 1.2)を厳守する。

    Args:
        xml_data: 非圧縮MusicXMLの生バイト列。
        mxl_path: 出力する .mxl のパス。
        inner_name: ZIP内での本体MusicXMLの名前(例 "score.musicxml")。
    """
    with zipfile.ZipFile(mxl_path, "w") as zf:
        # mimetype は仕様上ZIP先頭・無圧縮(STORED)で格納する。
        mimetype_info = zipfile.ZipInfo("mimetype")
        mimetype_info.compress_type = zipfile.ZIP_STORED
        zf.writestr(mimetype_info, _MXL_MIMETYPE)
        zf.writestr(_CONTAINER_PATH, _container_xml(inner_name))
        zf.writestr(inner_name, xml_data, compress_type=zipfile.ZIP_DEFLATED)


def prepare_handoff(musicxml_path: str | Path, out_dir: str | Path) -> Path:
    """MuseScore へローカル受け渡しするためのハンドオフ・パッケージを準備する。

    完全ローカル処理(外部送信・online変換なし・NF-023)。out_dir に
    圧縮 .mxl(既定)と README メモを配置し、圧縮に失敗する環境では
    非圧縮 .musicxml のコピーへフォールバックする(黙って壊れない)。
    MuseScore の自動起動は行わない(OS/バージョン依存の起動落とし穴を回避)。

    Args:
        musicxml_path: 入力する非圧縮 MusicXML(.musicxml/.xml)のパス。
        out_dir: 出力先ディレクトリ。無ければ作成する。

    Returns:
        受け渡しの主ファイルのパス(通常 .mxl。フォールバック時は .musicxml)。

    Raises:
        FileNotFoundError: 入力ファイルが存在しない場合。
        ValueError: 入力が非圧縮MusicXMLでない/空の場合。
    """
    src = Path(musicxml_path)
    xml_data = _read_and_validate_source(src)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # ZIP内・出力名はソースのstemを踏襲(日本語/空白パスもzipfileがUTF-8で扱う)。
    stem = src.stem or "score"
    inner_name = f"{stem}.musicxml"
    mxl_path = out / f"{stem}.mxl"
    xml_copy = out / f"{stem}.musicxml"

    # README は常に併置(受け渡しの注意=研究の失敗例を人間に伝える)。
    (out / _README_NAME).write_text(_README_TEXT, encoding="utf-8")

    # デバッグ用に非圧縮MusicXMLも常に置く(.mxl不調時の手動オープン導線)。
    xml_copy.write_bytes(xml_data)

    try:
        _write_mxl(xml_data, mxl_path, inner_name)
    except OSError:
        # 圧縮に失敗する環境(ディスク/権限等)では非圧縮コピーを主ファイルにする。
        return xml_copy
    return mxl_path
