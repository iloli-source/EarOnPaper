from earpipe.services.notate.score import (
    to_score,
    write_midi,
    write_midi_raw,
    write_musicxml,
)

from .chord import estimate_chords
from .engrave import render_svg_pages, svg_note_count, write_pdf, write_png_preview
from .tab import assign_frets, write_tab_pdf
from .musicxml_validate import ValidationReport, validate_musicxml
from .preview import render_preview
from .jianpu import to_jianpu
from .leadsheet import to_leadsheet
from .roman_nashville import to_nashville, to_roman
from .movable_do import to_movable_do
from .technique import Technique, detect_techniques
from .guitarpro_export import write_guitarpro
from .scale_cleanse import cleanse_to_scale
from .vocal_synth_export import to_ust, to_vocal_midi
from .llm_export import to_llm_text
from .transpose import (
    spell_transposed_key,
    transpose_key,
    transpose_notes,
    transpose_tab_out_of_range,
)
from .convert import staff_to_jianpu, staff_to_tab_frets, tab_to_staff
from .density import DroppedNote, simplify_density, simplify_density_verbose
from .render_text import render_jianpu_pdf, render_leadsheet_pdf, render_png_preview
from .drum_notation import drums_to_musicxml, gm_note_to_musicxml_unpitched
from .instrument_profile import (
    PROFILES,
    FitResult,
    InstrumentProfile,
    fit_to_profile,
    get_profile,
)
from .ornament import interpret_ornaments
from .piano_fingering import assign_fingering
from .visual_card import CardLayout, card_layout, render_visual_card
from .multivoice import separate_voices
from .vocal_lyrics import MELISMA_CONTINUATION, align_lyrics, count_unassigned
from .score_diff import diff_notes
from .asset_io import export_asset, import_asset
from .output_profiles import adjust_musicxml_for
from .format_registry import (
    FORMAT_REGISTRY,
    OutputFormat,
    available_formats,
    get_format,
)
from .musescore_handoff import prepare_handoff
from .handoff_package import HandoffManifest, build_handoff_package
from .soundfont_preview import fluidsynth_available, render_soundfont_preview
from .tempo_playback import is_artifact_prone, loop_region, time_stretch

__all__ = [
    "to_score", "write_midi", "write_midi_raw", "write_musicxml",
    "render_svg_pages", "svg_note_count", "write_pdf", "write_png_preview",
    "assign_frets", "write_tab_pdf", "estimate_chords",
    "ValidationReport", "validate_musicxml",
    "render_preview", "to_jianpu", "to_leadsheet",
    "to_roman", "to_nashville", "to_movable_do",
    "Technique", "detect_techniques",
    "write_guitarpro", "cleanse_to_scale", "to_ust", "to_vocal_midi",
    "to_llm_text",
    "transpose_notes", "transpose_key", "spell_transposed_key", "transpose_tab_out_of_range",
    "staff_to_jianpu", "staff_to_tab_frets", "tab_to_staff",
    "DroppedNote", "simplify_density", "simplify_density_verbose",
    "render_jianpu_pdf", "render_leadsheet_pdf", "render_png_preview",
    "drums_to_musicxml", "gm_note_to_musicxml_unpitched",
    "InstrumentProfile", "PROFILES", "FitResult", "fit_to_profile", "get_profile",
    "interpret_ornaments", "assign_fingering",
    "CardLayout", "card_layout", "render_visual_card",
    "separate_voices",
    "MELISMA_CONTINUATION", "align_lyrics", "count_unassigned",
    "diff_notes", "export_asset", "import_asset",
    "adjust_musicxml_for",
    "OutputFormat", "FORMAT_REGISTRY", "available_formats", "get_format",
    "prepare_handoff", "HandoffManifest", "build_handoff_package",
    "fluidsynth_available", "render_soundfont_preview",
    "time_stretch", "loop_region", "is_artifact_prone",
]
