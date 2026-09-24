#MenuTitle: Copy Glyph Spacing Between Masters
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

__doc__ = """
Copies the left and right sidebearings of the selected glyphs from one master
to another. The target master's outlines are not replaced or reshaped; its
advance width changes as needed to accommodate the copied sidebearings. Local
layer metrics keys for the left side, right side, and width are also copied.
"""

from GlyphsApp import Glyphs, Message
from vanilla import Button, PopUpButton, TextBox, Window


LOCAL_METRIC_KEY_ATTRIBUTES = (
	"leftMetricsKey",
	"rightMetricsKey",
	"widthMetricsKey",
)


class CopyGlyphSpacingBetweenMasters(object):

	def __init__(self):
		self.font = Glyphs.font
		if self.font is None:
			Message(title="Copy Spacing", message="No font open.")
			return

		self.masters = list(self.font.masters)
		if len(self.masters) < 2:
			Message(title="Copy Spacing", message="This script needs at least two masters.")
			return

		current_index = self.master_index_for_id((self.font.selectedLayers[0].master if self.font.selectedLayers else self.font.selectedFontMaster).id)
		target_index = 0 if current_index != 0 else 1

		self.w = Window((380, 142), "Copy Spacing Between Masters")
		self.w.sourceLabel = TextBox((15, 18, 105, 22), "Copy from")
		self.w.source = PopUpButton((120, 14, 245, 24), self.master_names())
		self.w.source.set(current_index)

		self.w.targetLabel = TextBox((15, 52, 105, 22), "Copy to")
		self.w.target = PopUpButton((120, 48, 245, 24), self.master_names())
		self.w.target.set(target_index)

		self.w.note = TextBox(
			(15, 82, 350, 24),
			"Copies LSB, RSB, and local layer metrics keys.",
			sizeStyle="small",
		)
		self.w.cancelButton = Button((165, 106, 80, 24), "Cancel", callback=self.cancel_callback)
		self.w.cancelButton.getNSButton().setKeyEquivalent_("\x1b")
		self.w.cancelButton.getNSButton().setKeyEquivalentModifierMask_(0)
		self.w.copyButton = Button((255, 106, 110, 24), "Copy", callback=self.copy_callback)
		self.w.setDefaultButton(self.w.copyButton)
		self.w.open()
		self.w.makeKey()

	def master_names(self):
		return [master.name for master in self.masters]

	def master_index_for_id(self, master_id):
		for index, master in enumerate(self.masters):
			if master.id == master_id:
				return index
		return 0

	def selected_glyphs(self):
		glyphs = []
		seen = set()
		for layer in self.font.selectedLayers:
			glyph = layer.parent
			if glyph is not None and glyph.name not in seen:
				glyphs.append(glyph)
				seen.add(glyph.name)
		return glyphs

	def cancel_callback(self, sender):
		self.w.close()

	def copy_callback(self, sender):
		source_master = self.masters[self.w.source.get()]
		target_master = self.masters[self.w.target.get()]

		if source_master.id == target_master.id:
			Message(title="Copy Spacing", message="Choose two different masters.")
			return

		glyphs = self.selected_glyphs()
		if not glyphs:
			Message(title="Copy Spacing", message="No glyphs selected.")
			return

		changed = 0
		skipped = []

		self.font.disableUpdateInterface()
		try:
			for glyph in glyphs:
				source_layer = glyph.layers[source_master.id]
				target_layer = glyph.layers[target_master.id]

				if source_layer is None or target_layer is None:
					skipped.append("%s: missing source or target layer" % glyph.name)
					continue

				source_lsb = source_layer.LSB
				source_rsb = source_layer.RSB
				old_lsb = target_layer.LSB
				old_rsb = target_layer.RSB
				source_metric_keys = {
					attribute: getattr(source_layer, attribute, None)
					for attribute in LOCAL_METRIC_KEY_ATTRIBUTES
				}

				glyph.beginUndo()
				try:
					# Assign both sides independently. Glyphs moves the target shapes for
					# the LSB and adjusts the advance width for the RSB.
					target_layer.LSB = source_lsb
					target_layer.RSB = source_rsb
					for attribute, value in source_metric_keys.items():
						setattr(target_layer, attribute, value)
				finally:
					glyph.endUndo()

				changed += 1
				print(
					"%s: %s L/R %s/%s -> %s L/R %s/%s (was %s/%s)"
					% (
						glyph.name,
						source_master.name,
						source_lsb,
						source_rsb,
						target_master.name,
						target_layer.LSB,
						target_layer.RSB,
						old_lsb,
						old_rsb,
					)
				)
		finally:
			self.font.enableUpdateInterface()

		self.w.close()

		message = "Copied spacing for %i selected glyph(s)." % changed
		if skipped:
			message += " Skipped %i; see Macro Panel." % len(skipped)
			print("Skipped:")
			for skipped_message in skipped:
				print(skipped_message)

		Glyphs.showNotification("Copy Spacing", message)


CopyGlyphSpacingBetweenMasters()
