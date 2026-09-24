#MenuTitle: Adapt Sidebearings Between Masters
# -*- coding: utf-8 -*-
__doc__ = """
For selected glyphs, preserves the source left-minus-right sidebearing
difference in another open font/master, distributing any extra space equally
while keeping the target layer’s width and outline size unchanged.
"""

from collections import Counter

from GlyphsApp import Glyphs
from vanilla import Button, PopUpButton, TextBox, Window


class AdaptSidebearingsBetweenFontsAndMasters(object):

	def __init__(self):
		self.selection_font = Glyphs.font
		if self.selection_font is None:
			Glyphs.showNotification("Adapt Sidebearings", "No font open.")
			return

		self.fonts = list(Glyphs.fonts)
		self.locations = [
			(font, master)
			for font in self.fonts
			for master in font.masters
		]
		if len(self.locations) < 2:
			Glyphs.showNotification(
				"Adapt Sidebearings",
				"Open another font or add another master.",
			)
			return

		self.location_labels = self.unique_location_labels()
		current_master_id = (self.selection_font.selectedLayers[0].master if self.selection_font.selectedLayers else self.selection_font.selectedFontMaster).id
		target_index = self.location_index(self.selection_font, current_master_id)
		source_index = self.preferred_source_index(target_index)

		self.w = Window((500, 160), "Adapt Sidebearings")
		self.w.sourceLabel = TextBox((15, 18, 105, 22), "Read from")
		self.w.source = PopUpButton((120, 14, 365, 24), self.location_labels)
		self.w.source.set(source_index)

		self.w.targetLabel = TextBox((15, 52, 105, 22), "Apply to")
		self.w.target = PopUpButton((120, 48, 365, 24), self.location_labels)
		self.w.target.set(target_index)

		self.w.note = TextBox(
			(15, 84, 470, 34),
			"Uses the frontmost font’s selection. Preserves the source LSB − RSB difference and the target width.",
			sizeStyle="small",
		)
		self.w.applyButton = Button((355, 124, 130, 24), "Apply", callback=self.apply_callback)
		self.w.setDefaultButton(self.w.applyButton)
		self.w.open()
		self.w.makeKey()

	def font_label(self, font):
		family_name = font.familyName or "Untitled"
		file_path = font.filepath
		if file_path:
			try:
				file_name = file_path.lastPathComponent()
			except Exception:
				file_name = str(file_path).split("/")[-1]
			return "%s (%s)" % (family_name, file_name)
		return family_name

	def unique_location_labels(self):
		raw_labels = [
			"%s – %s" % (self.font_label(font), master.name)
			for font, master in self.locations
		]
		counts = Counter(raw_labels)
		seen = {}
		labels = []
		for label in raw_labels:
			if counts[label] == 1:
				labels.append(label)
			else:
				seen[label] = seen.get(label, 0) + 1
				labels.append("%s [%i]" % (label, seen[label]))
		return labels

	def location_index(self, wanted_font, wanted_master_id):
		for index, (font, master) in enumerate(self.locations):
			if font == wanted_font and master.id == wanted_master_id:
				return index
		return 0

	def preferred_source_index(self, target_index):
		target_font, unused_target_master = self.locations[target_index]
		for index, (font, unused_master) in enumerate(self.locations):
			if index != target_index and font == target_font:
				return index
		for index in range(len(self.locations)):
			if index != target_index:
				return index
		return target_index

	def selected_glyph_names(self):
		glyph_names = []
		seen = set()
		for layer in self.selection_font.selectedLayers:
			glyph = layer.parent
			if glyph and glyph.name not in seen:
				glyph_names.append(glyph.name)
				seen.add(glyph.name)
		return glyph_names

	def apply_callback(self, sender):
		source_index = self.w.source.get()
		target_index = self.w.target.get()
		source_font, source_master = self.locations[source_index]
		target_font, target_master = self.locations[target_index]

		if source_font == target_font and source_master.id == target_master.id:
			Glyphs.showNotification(
				"Adapt Sidebearings",
				"Choose two different fonts or masters.",
			)
			return

		glyph_names = self.selected_glyph_names()
		if not glyph_names:
			Glyphs.showNotification("Adapt Sidebearings", "No glyphs selected.")
			return

		changed = 0
		skipped = []

		target_font.disableUpdateInterface()
		try:
			for glyph_name in glyph_names:
				source_glyph = source_font.glyphs[glyph_name]
				target_glyph = target_font.glyphs[glyph_name]

				if source_glyph is None:
					skipped.append("%s: missing from source font" % glyph_name)
					continue
				if target_glyph is None:
					skipped.append("%s: missing from target font" % glyph_name)
					continue

				source_layer = source_glyph.layers[source_master.id]
				target_layer = target_glyph.layers[target_master.id]

				if source_layer is None or target_layer is None:
					skipped.append("%s: missing source or target layer" % glyph_name)
					continue

				target_width = target_layer.width
				target_bounds = target_layer.bounds
				target_black_width = target_bounds.size.width
				if target_black_width <= 0:
					skipped.append("%s: target layer has no usable outline" % glyph_name)
					continue

				total_target_sb = target_width - target_black_width
				# Preserve the source’s offset from centered spacing. Sharing the
				# extra space equally avoids magnifying negative sidebearings or
				# unstable ratios when the source sidebearings nearly cancel out.
				source_imbalance = source_layer.LSB - source_layer.RSB
				new_lsb = round((total_target_sb + source_imbalance) / 2.0)
				new_rsb = total_target_sb - new_lsb

				target_glyph.beginUndo()
				try:
					target_layer.LSB = new_lsb
					# Setting sidebearings can affect the advance width. Restore it last
					# so this script can never leave the target at a different width.
					target_layer.width = target_width
				finally:
					target_glyph.endUndo()

				changed += 1
				print(
					"%s: %s L/R %s/%s -> %s width %s, L/R %s/%s"
					% (
						glyph_name,
						self.location_labels[source_index],
						source_layer.LSB,
						source_layer.RSB,
						self.location_labels[target_index],
						target_width,
						new_lsb,
						new_rsb,
					)
				)
		finally:
			target_font.enableUpdateInterface()

		self.w.close()

		message = "Updated %i selected glyph(s)." % changed
		if skipped:
			message += "\n\nSkipped:\n" + "\n".join(skipped[:10])
			if len(skipped) > 10:
				message += "\n...and %i more." % (len(skipped) - 10)

		Glyphs.showNotification("Adapt Sidebearings", message)


AdaptSidebearingsBetweenFontsAndMasters()
