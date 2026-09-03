# MenuTitle: Rename Selected Glyphs to Default Names
# -*- coding: utf-8 -*-

__doc__ = """
Checks the assigned Unicode of every selected glyph, then renames the glyph to
Glyphs’ default name for that Unicode. The current glyph name is not used to
determine the new name, and all existing Unicode values are preserved.
"""

from GlyphsApp import Glyphs


font = Glyphs.font
selected_glyphs = []

for layer in font.selectedLayers:
	glyph = layer.parent
	if glyph not in selected_glyphs:
		selected_glyphs.append(glyph)

renamed_count = 0
unchanged_count = 0
skipped_count = 0

if not selected_glyphs:
	print("You haven’t selected any glyphs to rename.")
else:
	font.disableUpdateInterface()
	try:
		for glyph in selected_glyphs:
			unicode_values = list(glyph.unicodes or [])
			unicode_value = glyph.unicode
			if not unicode_value:
				print(f"Skipped {glyph.name}: no Unicode value.")
				skipped_count += 1
				continue

			# Resolve the name exclusively from the glyph’s assigned Unicode.
			glyph_info = Glyphs.glyphInfoForUnicode(unicode_value)
			default_name = glyph_info.name if glyph_info else None
			if not default_name:
				print(f"Skipped {glyph.name}: no default name for U+{unicode_value}.")
				skipped_count += 1
				continue

			if glyph.name == default_name:
				unchanged_count += 1
				continue

			existing_glyph = font.glyphs[default_name]
			if existing_glyph is not None and existing_glyph != glyph:
				print(
					f"Skipped {glyph.name}: {default_name} already exists "
					f"for U+{unicode_value}."
				)
				skipped_count += 1
				continue

			old_name = glyph.name
			glyph.beginUndo()
			try:
				glyph.name = default_name
			finally:
				glyph.endUndo()

			renamed_count += 1
			print(
				f"Renamed {old_name} to {default_name}; "
				f"Unicode remains {', '.join('U+' + value for value in unicode_values)}."
			)
	finally:
		font.enableUpdateInterface()

	Glyphs.showNotification(
		"Rename Selected Glyphs",
		f"Renamed {renamed_count}; unchanged {unchanged_count}; skipped {skipped_count}.",
	)
