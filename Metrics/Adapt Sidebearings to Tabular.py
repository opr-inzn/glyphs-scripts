#MenuTitle: Adapt Sidebearings to Tabular
# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals

__doc__ = """
For each selected glyph, applies the base glyph’s left/right sidebearing
relationship to its matching .tf glyph on the current master while preserving
the .tf glyph’s existing advance width.

Selecting either cent or cent.tf targets cent.tf and reads spacing from cent.
"""

from GlyphsApp import Glyphs


TARGET_SUFFIX = ".tf"


def selected_base_glyph_names(font):
	glyph_names = []
	seen = set()

	for selected_layer in font.selectedLayers:
		glyph = selected_layer.parent
		if glyph is None:
			continue

		glyph_name = glyph.name
		if glyph_name.endswith(TARGET_SUFFIX):
			glyph_name = glyph_name[:-len(TARGET_SUFFIX)]

		if glyph_name and glyph_name not in seen:
			glyph_names.append(glyph_name)
			seen.add(glyph_name)

	return glyph_names


def adapt_tf_sidebearings(font, master, base_glyph_name):
	target_glyph_name = base_glyph_name + TARGET_SUFFIX
	source_glyph = font.glyphs[base_glyph_name]
	target_glyph = font.glyphs[target_glyph_name]

	if source_glyph is None:
		return False, "%s: base glyph is missing" % base_glyph_name
	if target_glyph is None:
		return False, "%s: target glyph is missing" % target_glyph_name

	source_layer = source_glyph.layers[master.id]
	target_layer = target_glyph.layers[master.id]
	if source_layer is None or target_layer is None:
		return False, "%s: source or target layer is missing" % target_glyph_name

	total_source_sidebearings = source_layer.LSB + source_layer.RSB
	if total_source_sidebearings == 0:
		return False, "%s: base sidebearings add up to zero" % base_glyph_name

	target_bounds = target_layer.bounds
	if target_bounds is None or target_bounds.size.width <= 0:
		return False, "%s: target layer has no usable outline" % target_glyph_name

	target_width = target_layer.width
	target_black_width = target_bounds.size.width
	total_target_sidebearings = target_width - target_black_width
	left_ratio = source_layer.LSB / float(total_source_sidebearings)
	new_lsb = round(total_target_sidebearings * left_ratio)
	new_rsb = total_target_sidebearings - new_lsb

	target_glyph.beginUndo()
	try:
		target_layer.LSB = new_lsb
		# Setting a sidebearing can affect advance width. Restore the defined
		# tabular width last so the script cannot leave it changed.
		target_layer.width = target_width
	finally:
		target_glyph.endUndo()

	print(
		"%s -> %s (%s): L/R %s/%s -> %s/%s, width kept at %s"
		% (
			base_glyph_name,
			target_glyph_name,
			master.name,
			source_layer.LSB,
			source_layer.RSB,
			new_lsb,
			new_rsb,
			target_width,
		)
	)
	return True, None


font = Glyphs.font
if font is None:
	Glyphs.showNotification("Adapt Sidebearings to Tabular", "No font open.")
else:
	master = font.selectedFontMaster
	base_glyph_names = selected_base_glyph_names(font)

	if not base_glyph_names:
		Glyphs.showNotification("Adapt Sidebearings to Tabular", "No glyphs selected.")
	else:
		changed = 0
		skipped = []

		font.disableUpdateInterface()
		try:
			for base_glyph_name in base_glyph_names:
				did_change, skip_message = adapt_tf_sidebearings(
					font, master, base_glyph_name
				)
				if did_change:
					changed += 1
				elif skip_message:
					skipped.append(skip_message)
		finally:
			font.enableUpdateInterface()

		message = "Updated %i .tf glyph(s) on %s." % (changed, master.name)
		if skipped:
			message += "\n\nSkipped:\n" + "\n".join(skipped[:10])
			if len(skipped) > 10:
				message += "\n...and %i more." % (len(skipped) - 10)

		Glyphs.showNotification("Adapt Sidebearings to Tabular", message)
