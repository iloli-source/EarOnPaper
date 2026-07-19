"""受入テスト C6: MusicXMLエクスポートの規格妥当性・互換性・.mxl (Issue #44)。

core-requirements-v3 C6 の受入条件をテスト化する:
- XSDスキーマ妥当性: MusicXML 4.0 公式スキーマ(リポジトリ同梱・オフライン検証)
- 相互運用: music21 での再読込と音符数保存
- 圧縮形式: .mxl の生成と再読込

スコープ外(明記): MuseScore/Dorico 等の実機アプリでのインポート確認は
自動化環境に実機がないため対象外。NF-011 の「対象アプリ別インポート確認」は
ユーザーテスト段階のチェックリストで扱う。
"""

from pathlib import Path

import music21
import pytest
import soundfile as sf
from lxml import etree

from earpipe.pipeline import transcribe_file
from tests.conftest import MELODY_SIMPLE, SR, render_melody

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas" / "musicxml40"


class _LocalResolver(etree.Resolver):
    """スキーマ内の外部参照(xml.xsd等)を同梱ファイルへ解決する(通信ゼロ)。"""

    def resolve(self, url: str, id: str | None, context: object) -> object:
        name = url.rsplit("/", 1)[-1]
        local = SCHEMA_DIR / name
        if local.exists():
            return self.resolve_filename(str(local), context)
        return None


def _load_schema() -> etree.XMLSchema:
    parser = etree.XMLParser(load_dtd=False, no_network=True)
    parser.resolvers.add(_LocalResolver())
    return etree.XMLSchema(etree.parse(str(SCHEMA_DIR / "musicxml.xsd"), parser))


@pytest.fixture(scope="module")
def transcribed_musicxml(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    """代表メロディを実際にパイプラインで採譜したMusicXMLを用意する。"""
    tmp = tmp_path_factory.mktemp("c6")
    wav = tmp / "melody.wav"
    sf.write(wav, render_melody(MELODY_SIMPLE, bpm=100), SR)
    out = tmp / "melody.musicxml"
    result = transcribe_file(wav, out_musicxml=out)
    assert out.exists()
    return out, result


@pytest.mark.integration
class TestC6MusicXmlAcceptance:
    def test_schema_files_are_vendored(self) -> None:
        """オフライン検証の前提: スキーマ一式がリポジトリに同梱されている。"""
        for name in ("musicxml.xsd", "xml.xsd", "xlink.xsd"):
            assert (SCHEMA_DIR / name).exists(), f"スキーマ同梱漏れ: {name}"

    def test_xsd_valid(self, transcribed_musicxml: tuple[Path, dict]) -> None:
        """生成MusicXMLが MusicXML 4.0 XSD に対して妥当(C6受入の中核)。"""
        path, _ = transcribed_musicxml
        schema = _load_schema()
        parser = etree.XMLParser(load_dtd=False, no_network=True, huge_tree=True)
        doc = etree.parse(str(path), parser)
        ok = schema.validate(doc)
        errors = "\n".join(e.message for e in schema.error_log[:10])
        assert ok, f"XSD違反:\n{errors}"

    def test_music21_roundtrip_preserves_notes(
        self, transcribed_musicxml: tuple[Path, dict]
    ) -> None:
        """music21 で再読込でき、音符数が書き出し時と一致する。"""
        path, result = transcribed_musicxml
        reloaded = music21.converter.parse(path)
        # 小節線をまたぐ音はタイで分割される(正しい記譜挙動)ため、
        # 音楽的な音符数で比較する: stripTies でタイ連結を1音に戻して数える
        n_reloaded = len(reloaded.stripTies().flatten().notes)
        assert n_reloaded > 0
        assert n_reloaded == result["n_notes"], (
            f"往復で音符数が変わった: 書出{result['n_notes']} → 再読{n_reloaded}"
        )

    def test_mxl_roundtrip(
        self, transcribed_musicxml: tuple[Path, dict], tmp_path: Path
    ) -> None:
        """圧縮 .mxl を生成でき、再読込で音符数が保存される。"""
        path, result = transcribed_musicxml
        score = music21.converter.parse(path)
        mxl = tmp_path / "melody.mxl"
        score.write("mxl", fp=mxl)
        assert mxl.exists() and mxl.stat().st_size > 0
        # .mxl は zip コンテナ(META-INF/container.xml)であることも確認
        import zipfile

        with zipfile.ZipFile(mxl) as zf:
            assert "META-INF/container.xml" in zf.namelist()
        reloaded = music21.converter.parse(mxl)
        assert len(reloaded.stripTies().flatten().notes) == result["n_notes"]
