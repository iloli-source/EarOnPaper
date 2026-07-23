"""Lazy public API for notation services.

Notation backends have optional heavyweight dependencies (notably music21 and
renderers).  Importing a lightweight helper such as ``notate.tab`` must not
force every backend to be installed.  Attributes are resolved only when used.
"""

from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "to_score": (".score", "to_score"),
    "write_midi": (".score", "write_midi"),
    "write_midi_raw": (".score", "write_midi_raw"),
    "write_musicxml": (".score", "write_musicxml"),
    "estimate_chords": (".chord", "estimate_chords"),
    "render_svg_pages": (".engrave", "render_svg_pages"),
    "svg_note_count": (".engrave", "svg_note_count"),
    "write_pdf": (".engrave", "write_pdf"),
    "write_png_preview": (".engrave", "write_png_preview"),
    "assign_frets": (".tab", "assign_frets"),
    "write_tab_pdf": (".tab", "write_tab_pdf"),
    "ValidationReport": (".musicxml_validate", "ValidationReport"),
    "validate_musicxml": (".musicxml_validate", "validate_musicxml"),
    "render_preview": (".preview", "render_preview"),
    "to_jianpu": (".jianpu", "to_jianpu"),
    "to_leadsheet": (".leadsheet", "to_leadsheet"),
    "to_nashville": (".roman_nashville", "to_nashville"),
    "to_roman": (".roman_nashville", "to_roman"),
    "to_movable_do": (".movable_do", "to_movable_do"),
    "Technique": (".technique", "Technique"),
    "detect_techniques": (".technique", "detect_techniques"),
    "write_guitarpro": (".guitarpro_export", "write_guitarpro"),
    "cleanse_to_scale": (".scale_cleanse", "cleanse_to_scale"),
    "to_ust": (".vocal_synth_export", "to_ust"),
    "to_vocal_midi": (".vocal_synth_export", "to_vocal_midi"),
    "to_llm_text": (".llm_export", "to_llm_text"),
    "spell_transposed_key": (".transpose", "spell_transposed_key"),
    "transpose_key": (".transpose", "transpose_key"),
    "transpose_notes": (".transpose", "transpose_notes"),
    "transpose_tab_out_of_range": (".transpose", "transpose_tab_out_of_range"),
    "staff_to_jianpu": (".convert", "staff_to_jianpu"),
    "staff_to_tab_frets": (".convert", "staff_to_tab_frets"),
    "tab_to_staff": (".convert", "tab_to_staff"),
    "DroppedNote": (".density", "DroppedNote"),
    "simplify_density": (".density", "simplify_density"),
    "simplify_density_verbose": (".density", "simplify_density_verbose"),
    "render_jianpu_pdf": (".render_text", "render_jianpu_pdf"),
    "render_leadsheet_pdf": (".render_text", "render_leadsheet_pdf"),
    "render_png_preview": (".render_text", "render_png_preview"),
    "drums_to_musicxml": (".drum_notation", "drums_to_musicxml"),
    "gm_note_to_musicxml_unpitched": (".drum_notation", "gm_note_to_musicxml_unpitched"),
    "PROFILES": (".instrument_profile", "PROFILES"),
    "FitResult": (".instrument_profile", "FitResult"),
    "InstrumentProfile": (".instrument_profile", "InstrumentProfile"),
    "fit_to_profile": (".instrument_profile", "fit_to_profile"),
    "get_profile": (".instrument_profile", "get_profile"),
    "interpret_ornaments": (".ornament", "interpret_ornaments"),
    "assign_fingering": (".piano_fingering", "assign_fingering"),
    "CardLayout": (".visual_card", "CardLayout"),
    "card_layout": (".visual_card", "card_layout"),
    "render_visual_card": (".visual_card", "render_visual_card"),
    "separate_voices": (".multivoice", "separate_voices"),
    "MELISMA_CONTINUATION": (".vocal_lyrics", "MELISMA_CONTINUATION"),
    "align_lyrics": (".vocal_lyrics", "align_lyrics"),
    "count_unassigned": (".vocal_lyrics", "count_unassigned"),
    "diff_notes": (".score_diff", "diff_notes"),
    "export_asset": (".asset_io", "export_asset"),
    "import_asset": (".asset_io", "import_asset"),
    "adjust_musicxml_for": (".output_profiles", "adjust_musicxml_for"),
    "FORMAT_REGISTRY": (".format_registry", "FORMAT_REGISTRY"),
    "OutputFormat": (".format_registry", "OutputFormat"),
    "available_formats": (".format_registry", "available_formats"),
    "get_format": (".format_registry", "get_format"),
    "prepare_handoff": (".musescore_handoff", "prepare_handoff"),
    "HandoffManifest": (".handoff_package", "HandoffManifest"),
    "build_handoff_package": (".handoff_package", "build_handoff_package"),
    "fluidsynth_available": (".soundfont_preview", "fluidsynth_available"),
    "render_soundfont_preview": (".soundfont_preview", "render_soundfont_preview"),
    "is_artifact_prone": (".tempo_playback", "is_artifact_prone"),
    "loop_region": (".tempo_playback", "loop_region"),
    "time_stretch": (".tempo_playback", "time_stretch"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    value = getattr(import_module(module_name, __name__), attr_name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
