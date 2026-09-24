#MenuTitle: Adapt Anchor Position Between Masters
# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals

__doc__ = """
For selected glyphs, reads every anchor's horizontal position from one master
as a ratio across the glyph's black width, then applies those ratios to another
master.

The ratio is measured between LSB and width-RSB:
    (anchor.x - LSB) / ((width - RSB) - LSB)
"""

from GlyphsApp import GSAnchor, Glyphs, Message
from AppKit import NSPoint
from vanilla import Button, CheckBox, PopUpButton, TextBox, Window


class AdaptSelectedAnchorPositionBetweenMasters(object):

	def __init__(self):
		self.font = Glyphs.font
		if self.font is None:
			Message(title="Adapt Anchor Position", message="No font open.")
			return

		self.masters = list(self.font.masters)
		if len(self.masters) < 2:
			Message(title="Adapt Anchor Position", message="This script needs at least two masters.")
			return

		current_master_id = (self.font.selectedLayers[0].master if self.font.selectedLayers else self.font.selectedFontMaster).id
		current_index = self.master_index_for_id(current_master_id)
		source_index = 0 if current_index != 0 else min(1, len(self.masters) - 1)

		self.w = Window((390, 146), "Adapt Anchor Positions")
		self.w.sourceLabel = TextBox((15, 18, 105, 22), "Read from")
		self.w.source = PopUpButton((120, 14, 255, 24), self.master_names())
		self.w.source.set(source_index)

		self.w.targetLabel = TextBox((15, 52, 105, 22), "Apply to")
		self.w.target = PopUpButton((120, 48, 255, 24), self.master_names())
		self.w.target.set(current_index)

		self.w.copyY = CheckBox((120, 80, 255, 22), "Copy Y positions from source", value=False)
		self.w.cancelButton = Button((155, 108, 80, 24), "Cancel", callback=self.cancel_callback)
		self.w.cancelButton.getNSButton().setKeyEquivalent_("\x1b")
		self.w.cancelButton.getNSButton().setKeyEquivalentModifierMask_(0)
		self.w.applyButton = Button((245, 108, 130, 24), "Apply", callback=self.apply_callback)
		self.w.setDefaultButton(self.w.applyButton)
		self.w.open()
		self.w.makeKey()

	def master_names(self):
		return [master.name for master in self.masters]

	def master_index_for_id(self, master_id):
		for i, master in enumerate(self.masters):
			if master.id == master_id:
				return i
		return 0

	def selected_glyphs(self):
		glyphs = []
		seen = set()
		for layer in self.font.selectedLayers:
			glyph = layer.parent
			if glyph and glyph.name not in seen:
				glyphs.append(glyph)
				seen.add(glyph.name)
		return glyphs

	def anchor_for_layer(self, layer, anchor_name):
		return layer.anchorForName_(anchor_name)

	def layer_black_width(self, layer):
		left_edge = layer.LSB
		right_edge = layer.width - layer.RSB
		return right_edge - left_edge

	def anchor_ratio(self, layer, anchor):
		black_width = self.layer_black_width(layer)
		if black_width == 0:
			return None
		return (anchor.position.x - layer.LSB) / float(black_width)

	def cancel_callback(self, sender):
		self.w.close()

	def apply_callback(self, sender):
		source_master = self.masters[self.w.source.get()]
		target_master = self.masters[self.w.target.get()]
		copy_y = self.w.copyY.get()

		if source_master.id == target_master.id:
			Message(title="Adapt Anchor Position", message="Choose two different masters.")
			return

		glyphs = self.selected_glyphs()
		if not glyphs:
			Message(title="Adapt Anchor Position", message="No glyphs selected.")
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

				if not source_layer.anchors:
					skipped.append("%s: source layer has no anchors" % glyph.name)
					continue

				target_black_width = self.layer_black_width(target_layer)
				if self.layer_black_width(source_layer) == 0:
					skipped.append("%s: source black width is zero" % glyph.name)
					continue

				if target_black_width == 0:
					skipped.append("%s: target black width is zero" % glyph.name)
					continue

				glyph.beginUndo()
				try:
					for source_anchor in source_layer.anchors:
						anchor_name = source_anchor.name
						source_ratio = self.anchor_ratio(source_layer, source_anchor)
						new_x = target_layer.LSB + target_black_width * source_ratio
						target_anchor = self.anchor_for_layer(target_layer, anchor_name)
						new_y = source_anchor.position.y

						if target_anchor is None:
							target_anchor = GSAnchor(anchor_name, NSPoint(new_x, new_y))
							target_layer.addAnchor_(target_anchor)
						else:
							if not copy_y:
								new_y = target_anchor.position.y
							target_anchor.setPosition_(NSPoint(new_x, new_y))

						changed += 1
						print(
							"%s: '%s' ratio %.4f from %s -> %s position %.1f, %.1f"
							% (
								glyph.name,
								anchor_name,
								source_ratio,
								source_master.name,
								target_master.name,
								new_x,
								new_y,
							)
						)
				finally:
					glyph.endUndo()
		finally:
			self.font.enableUpdateInterface()

		self.w.close()

		message = "Updated %i anchor(s)." % changed
		if skipped:
			message += " Skipped %i; see Macro Panel." % len(skipped)
			print("Skipped:")
			for skipped_message in skipped:
				print(skipped_message)

		Glyphs.showNotification("Adapt Anchor Position", message)


AdaptSelectedAnchorPositionBetweenMasters()
