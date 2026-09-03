# MenuTitle: Replace Components with .ss05 Versions
# -*- coding: utf-8 -*-

__doc__ = """
In the selected glyph layers, replaces each direct component with the .ss05
version of that component when the corresponding glyph exists. Component
transforms and automatic-alignment settings are preserved. Glyph- and
layer-level metric keys are redirected to matching .ss05 glyphs as well.
"""

import re

from GlyphsApp import Glyphs


SUFFIX = ".ss05"
METRIC_KEY_ATTRIBUTES = (
	"leftMetricsKey",
	"rightMetricsKey",
	"widthMetricsKey",
)
GLYPH_METRIC_KEY_PATTERN = re.compile(
	r"^(==?)(\|?)([A-Za-z_.][A-Za-z0-9_.-]*)(.*)$"
)


def ss05_metric_key(key, font):
	"""Return an updated glyph-reference key, or the original literal key."""
	if not isinstance(key, str):
		return key, None

	match = GLYPH_METRIC_KEY_PATTERN.match(key)
	if not match:
		# Leaves numbers and expressions such as 39, =39, =+20, and =| alone.
		return key, None

	equals, mirror, referenced_name, remainder = match.groups()
	if referenced_name.endswith(SUFFIX):
		return key, None

	target_name = referenced_name + SUFFIX
	if font.glyphs[target_name] is None:
		return key, target_name

	return "%s%s%s%s" % (equals, mirror, target_name, remainder), None


def update_metric_keys(owner, font, owner_label, missing_keys):
	updated = 0
	for attribute in METRIC_KEY_ATTRIBUTES:
		old_key = getattr(owner, attribute, None)
		new_key, missing_name = ss05_metric_key(old_key, font)
		if missing_name:
			missing_keys.add("%s → %s on %s" % (old_key, missing_name, owner_label))
		elif new_key != old_key:
			setattr(owner, attribute, new_key)
			updated += 1
			print("%s: %s → %s" % (owner_label, old_key, new_key))
	return updated


font = Glyphs.font

if font is None:
	Glyphs.showNotification("Replace Components with .ss05", "No font is open.")
else:
	selected_layers = list(font.selectedLayers)
	replaced_count = 0
	metric_key_count = 0
	unchanged_count = 0
	missing = []
	missing_keys = set()
	self_references = []
	updated_glyph_names = set()

	if not selected_layers:
		Glyphs.showNotification(
			"Replace Components with .ss05",
			"No glyphs are selected.",
		)
	else:
		font.disableUpdateInterface()
		try:
			for layer in selected_layers:
				glyph = layer.parent
				if glyph is None:
					continue

				glyph.beginUndo()
				try:
					if glyph.name not in updated_glyph_names:
						metric_key_count += update_metric_keys(
							glyph,
							font,
							"%s (glyph)" % glyph.name,
							missing_keys,
						)
						updated_glyph_names.add(glyph.name)

					metric_key_count += update_metric_keys(
						layer,
						font,
						"%s, %s (layer)" % (glyph.name, layer.name),
						missing_keys,
					)

					for component in layer.components:
						source_name = component.componentName
						if not source_name or source_name.endswith(SUFFIX):
							unchanged_count += 1
							continue

						target_name = source_name + SUFFIX
						if target_name == glyph.name:
							self_references.append(
								"%s on %s" % (target_name, layer.name)
							)
							continue

						if font.glyphs[target_name] is None:
							missing.append(
								"%s → %s on %s" % (source_name, target_name, glyph.name)
							)
							continue

						component_transform = component.transform
						automatic_alignment = bool(component.automaticAlignment)
						alignment = component.alignment
						disable_alignment = bool(component.disableAlignment)
						component.componentName = target_name
						if automatic_alignment:
							component.alignment = alignment
							component.disableAlignment = disable_alignment
							component.automaticAlignment = True
							component.transform = component_transform
						else:
							# Glyphs can silently enable alignment when componentName changes.
							# Restore every underlying manual-positioning flag, then restore the
							# transform, and assert the manual state once more afterward.
							component.alignment = -1
							component.disableAlignment = True
							component.automaticAlignment = False
							component.transform = component_transform
							component.alignment = -1
							component.disableAlignment = True
							component.automaticAlignment = False
						replaced_count += 1
						print(
							"%s, %s: %s → %s"
							% (glyph.name, layer.name, source_name, target_name)
						)
				finally:
					glyph.endUndo()
		finally:
			font.enableUpdateInterface()

		if missing:
			print("Missing .ss05 glyphs:")
			for message in missing:
				print("  %s" % message)

		if self_references:
			print("Skipped self-referencing components:")
			for message in self_references:
				print("  %s" % message)

		if missing_keys:
			print("Missing .ss05 glyphs referenced by metric keys:")
			for message in sorted(missing_keys):
				print("  %s" % message)

		Glyphs.redraw()
		message = "Replaced %i component(s) and updated %i metric key(s)." % (
			replaced_count,
			metric_key_count,
		)
		if missing:
			message += " Missing %i .ss05 counterpart(s)." % len(missing)
		if self_references:
			message += " Skipped %i self-reference(s)." % len(self_references)
		if missing_keys:
			message += " Missing %i metric-key counterpart(s)." % len(missing_keys)
		Glyphs.showNotification("Replace Components with .ss05", message)
