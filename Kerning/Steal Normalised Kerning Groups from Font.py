# MenuTitle: Steal Normalised Kerning Groups
# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals
__doc__ = """
Normalises production-style kerning group names in a source font, then copies
the source font's kerning groups to another open font.

For example, a group named ``uni018E`` is renamed to the name of the source
font glyph encoded at U+018E. Kerning pairs in the source font are rewritten
as well, so normalising a group does not orphan its kerning.
"""

import re

import vanilla
from GlyphsApp import Glyphs, Message


PRODUCTION_NAME = re.compile(r"^(?:uni([0-9A-Fa-f]{4})|u([0-9A-Fa-f]{5,6}))$")


def font_label(font):
	name = font.familyName or "Untitled"
	if font.filepath:
		try:
			return "%s (%s)" % (name, font.filepath.lastPathComponent())
		except Exception:
			pass
	return "%s (unsaved document)" % name


def glyph_name_for_production_name(font, group_name):
	"""Resolve uniXXXX/uXXXXX through the source font before GlyphData."""
	match = PRODUCTION_NAME.match(group_name or "")
	if not match:
		return group_name

	unicode_value = (match.group(1) or match.group(2)).upper()
	for glyph in font.glyphs:
		if unicode_value in [value.upper() for value in (glyph.unicodes or [])]:
			return glyph.name

	info = Glyphs.glyphInfoForUnicode(unicode_value)
	return info.name if info and info.name else group_name


def api_key_for_kerning_key(font, key):
	if key.startswith("@"):
		return key
	glyph = font.glyphForId_(key)
	return glyph.name if glyph else None


def normalise_source_groups(font, verbose=False):
	left_names = {}
	right_names = {}

	for glyph in font.glyphs:
		old_name = glyph.leftKerningGroup
		new_name = glyph_name_for_production_name(font, old_name)
		if old_name and new_name != old_name:
			left_names[old_name] = new_name

		old_name = glyph.rightKerningGroup
		new_name = glyph_name_for_production_name(font, old_name)
		if old_name and new_name != old_name:
			right_names[old_name] = new_name

	# Snapshot before changing assignments and pair keys.
	pairs_by_master = {}
	for master in font.masters:
		pairs = []
		for left_key, right_side in font.kerning.get(master.id, {}).items():
			if right_side is None:
				continue
			for right_key, value in right_side.items():
				pairs.append((left_key, right_key, value))
		pairs_by_master[master.id] = pairs

	assignment_count = 0
	for glyph in font.glyphs:
		if glyph.leftKerningGroup in left_names:
			glyph.leftKerningGroup = left_names[glyph.leftKerningGroup]
			assignment_count += 1
		if glyph.rightKerningGroup in right_names:
			glyph.rightKerningGroup = right_names[glyph.rightKerningGroup]
			assignment_count += 1

	pair_count = 0
	warnings = []
	for master in font.masters:
		translated = {}
		for left_key, right_key, value in pairs_by_master[master.id]:
			new_left = left_key
			new_right = right_key
			if left_key.startswith("@MMK_L_"):
				group_name = left_key[7:]
				new_left = "@MMK_L_" + right_names.get(group_name, group_name)
			if right_key.startswith("@MMK_R_"):
				group_name = right_key[7:]
				new_right = "@MMK_R_" + left_names.get(group_name, group_name)

			pair = (new_left, new_right)
			if pair in translated and translated[pair] != value:
				warnings.append(
					"%s: kept %s for %s %s; discarded conflicting %s"
					% (master.name, translated[pair], new_left, new_right, value)
				)
				continue
			translated[pair] = value

		font.kerning[master.id] = {}
		for (left_key, right_key), value in translated.items():
			left_api_key = api_key_for_kerning_key(font, left_key)
			right_api_key = api_key_for_kerning_key(font, right_key)
			if left_api_key is None or right_api_key is None:
				warnings.append("%s: could not restore %s %s" % (master.name, left_key, right_key))
				continue
			font.setKerningForPair(master.id, left_api_key, right_api_key, value)

	for old_name, new_name in sorted(set(left_names.items()) | set(right_names.items())):
		print("  Normalised %s → %s" % (old_name, new_name))

	# Count only pairs whose group key actually changed.
	for master_id, pairs in pairs_by_master.items():
		for left_key, right_key, value in pairs:
			new_left = "@MMK_L_" + right_names.get(left_key[7:], left_key[7:]) if left_key.startswith("@MMK_L_") else left_key
			new_right = "@MMK_R_" + left_names.get(right_key[7:], right_key[7:]) if right_key.startswith("@MMK_R_") else right_key
			if new_left != left_key or new_right != right_key:
				pair_count += 1

	return assignment_count, pair_count, warnings


class StealNormalisedKerningGroups(object):
	def __init__(self):
		self.fonts = list(Glyphs.fonts)
		if len(self.fonts) < 2:
			Message(title="Not Enough Fonts", message="Open at least two fonts.")
			return

		labels = [font_label(font) for font in self.fonts]
		current_index = self.fonts.index(Glyphs.font) if Glyphs.font in self.fonts else 0
		target_index = 0 if current_index != 0 else 1

		self.w = vanilla.FloatingWindow((430, 250), "Steal Normalised Kerning Groups")
		self.w.infoText = vanilla.TextBox(
			(15, 15, -15, 28),
			"Normalise groups in the source font, then copy them to the target font.",
			sizeStyle="small",
		)		
		self.w.sourceLabel = vanilla.TextBox((15, 52, 90, 18), "Source font:", sizeStyle="small")
		self.w.source = vanilla.PopUpButton((105, 48, -15, 22), labels, sizeStyle="small")
		self.w.source.set(current_index)
		self.w.targetLabel = vanilla.TextBox((15, 82, 90, 18), "Target font:", sizeStyle="small")
		self.w.target = vanilla.PopUpButton((105, 78, -15, 22), labels, sizeStyle="small")
		self.w.target.set(target_index)
		self.w.allGroups = vanilla.CheckBox((15, 112, -15, 20), "Copy all groups (ignore source selection)", value=True, sizeStyle="small")
		self.w.overwrite = vanilla.CheckBox((15, 138, -15, 20), "Overwrite existing groups in target font", value=True, sizeStyle="small")
		self.w.reset = vanilla.CheckBox((15, 164, -15, 20), "Reset all groups in target font before copying", value=False, sizeStyle="small")
		self.w.verbose = vanilla.CheckBox((15, 190, 230, 20), "Verbose Macro Window report", value=False, sizeStyle="small")
		self.w.runButton = vanilla.Button((-90, -34, -15, 22), "Steal", callback=self.run)
		self.w.setDefaultButton(self.w.runButton)
		self.w.open()
		self.w.makeKey()

	def run(self, sender):
		source_font = self.fonts[self.w.source.get()]
		target_font = self.fonts[self.w.target.get()]
		if source_font == target_font:
			Message(title="Choose Two Fonts", message="Source and target must be different fonts.")
			return

		Glyphs.clearLog()
		print("STEAL NORMALISED KERNING GROUPS\n")
		print("Source: %s" % font_label(source_font))
		print("Target: %s\n" % font_label(target_font))

		source_font.disableUpdateInterface()
		try:
			assignments, pairs, warnings = normalise_source_groups(source_font, self.w.verbose.get())
		finally:
			source_font.enableUpdateInterface()

		if self.w.reset.get():
			for glyph in target_font.glyphs:
				glyph.leftKerningGroup = None
				glyph.rightKerningGroup = None

		if self.w.allGroups.get():
			glyph_names = [glyph.name for glyph in source_font.glyphs]
		else:
			glyph_names = list(dict.fromkeys(layer.parent.name for layer in source_font.selectedLayers))

		copied = 0
		skipped = 0
		overwrite = self.w.overwrite.get()
		for glyph_name in glyph_names:
			source_glyph = source_font.glyphs[glyph_name]
			target_glyph = target_font.glyphs[glyph_name]
			if not target_glyph:
				skipped += 1
				if self.w.verbose.get():
					print("  Skipped /%s – missing in target" % glyph_name)
				continue

			if source_glyph.leftKerningGroup and (overwrite or not target_glyph.leftKerningGroup):
				target_glyph.leftKerningGroup = source_glyph.leftKerningGroup
				copied += 1
			if source_glyph.rightKerningGroup and (overwrite or not target_glyph.rightKerningGroup):
				target_glyph.rightKerningGroup = source_glyph.rightKerningGroup
				copied += 1
			if self.w.verbose.get():
				print(
					"  /%s: left=%s, right=%s"
					% (glyph_name, target_glyph.leftKerningGroup or "–", target_glyph.rightKerningGroup or "–")
				)

		print("\nDone.")
		print("  Source group assignments normalised: %i" % assignments)
		print("  Source kerning pairs renamed: %i" % pairs)
		print("  Target group assignments copied: %i" % copied)
		print("  Missing target glyphs skipped: %i" % skipped)
		for warning in warnings:
			print("  Warning: %s" % warning)

		Glyphs.showNotification(
			"Kerning groups copied",
			"Normalised %i source assignment(s) and copied %i assignment(s)." % (assignments, copied),
		)
		self.w.close()


StealNormalisedKerningGroups()
