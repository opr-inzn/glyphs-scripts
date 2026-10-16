#MenuTitle: Copy Metric Keys Between Masters
# -*- coding: utf-8 -*-
__doc__ = """
Copies only local left, right and width metric keys between masters in the
current font for selected glyphs. Empty source keys clear target keys.
Glyph-level keys, numeric spacing, outlines and other layers are left unchanged.
Metrics are not synchronized or recalculated.
"""

from collections import Counter

from GlyphsApp import Glyphs
from vanilla import Button, PopUpButton, TextBox, Window


METRIC_KEY_ATTRIBUTES = (
	"leftMetricsKey",
	"rightMetricsKey",
	"widthMetricsKey",
)


class CopyMetricKeysBetweenMasters(object):

	def __init__(self):
		self.font = Glyphs.font
		if self.font is None:
			Glyphs.showNotification("Copy Metric Keys", "No font open.")
			return

		self.masters = list(self.font.masters)
		if len(self.masters) < 2:
			Glyphs.showNotification(
				"Copy Metric Keys",
				"This script needs at least two masters in the current font.",
			)
			return

		self.master_labels = self.unique_master_labels()
		current_master = self.font.selectedFontMaster
		if self.font.selectedLayers:
			current_master = self.font.selectedLayers[0].master or current_master
		current_master_id = current_master.id if current_master is not None else None
		target_index = self.master_index(current_master_id)
		source_index = 0 if target_index != 0 else 1

		self.w = Window((500, 160), "Copy Metric Keys")
		self.w.sourceLabel = TextBox((15, 18, 105, 22), "Copy from")
		self.w.source = PopUpButton((120, 14, 365, 24), self.master_labels)
		self.w.source.set(source_index)

		self.w.targetLabel = TextBox((15, 52, 105, 22), "Copy to")
		self.w.target = PopUpButton((120, 48, 365, 24), self.master_labels)
		self.w.target.set(target_index)

		self.w.note = TextBox(
			(15, 84, 470, 34),
			"Copies local LSB, RSB and width keys for selected glyphs. "
			"Empty source keys clear target keys; spacing stays unchanged.",
			sizeStyle="small",
		)
		self.w.cancelButton = Button((265, 124, 80, 24), "Cancel", callback=self.cancel_callback)
		self.w.cancelButton.getNSButton().setKeyEquivalent_("\x1b")
		self.w.cancelButton.getNSButton().setKeyEquivalentModifierMask_(0)
		self.w.copyButton = Button((355, 124, 130, 24), "Copy", callback=self.copy_callback)
		self.w.setDefaultButton(self.w.copyButton)
		self.w.open()
		self.w.makeKey()

	def unique_master_labels(self):
		raw_labels = [master.name for master in self.masters]
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

	def master_index(self, wanted_master_id):
		for index, master in enumerate(self.masters):
			if master.id == wanted_master_id:
				return index
		return 0

	def selected_glyph_names(self):
		glyph_names = []
		seen = set()
		for layer in self.font.selectedLayers:
			glyph = layer.parent
			if glyph is not None and glyph.name not in seen:
				glyph_names.append(glyph.name)
				seen.add(glyph.name)
		return glyph_names

	def cancel_callback(self, sender):
		self.w.close()

	def copy_callback(self, sender):
		source_index = self.w.source.get()
		target_index = self.w.target.get()
		source_master = self.masters[source_index]
		target_master = self.masters[target_index]

		if source_master.id == target_master.id:
			Glyphs.showNotification("Copy Metric Keys", "Choose two different masters.")
			return

		if self.font not in list(Glyphs.fonts):
			Glyphs.showNotification("Copy Metric Keys", "The font was closed. Reopen this script.")
			return
		for master in (source_master, target_master):
			if not any(item.id == master.id for item in self.font.masters):
				Glyphs.showNotification("Copy Metric Keys", "A master was removed. Reopen this script.")
				return

		glyph_names = self.selected_glyph_names()
		if not glyph_names:
			Glyphs.showNotification("Copy Metric Keys", "No glyphs selected.")
			return

		changed = 0
		changed_keys = 0
		skipped = []
		self.font.disableUpdateInterface()
		try:
			for glyph_name in glyph_names:
				glyph = self.font.glyphs[glyph_name]
				if glyph is None:
					skipped.append("%s: glyph was removed" % glyph_name)
					continue

				source_layer = glyph.layers[source_master.id]
				target_layer = glyph.layers[target_master.id]
				if source_layer is None or target_layer is None:
					skipped.append("%s: missing source or target layer" % glyph_name)
					continue

				key_changes = [
					(attribute, getattr(source_layer, attribute))
					for attribute in METRIC_KEY_ATTRIBUTES
					if getattr(source_layer, attribute) != getattr(target_layer, attribute)
				]
				if not key_changes:
					continue

				glyph.beginUndo()
				try:
					# Copy key strings exactly, including empty keys. Do not set any
					# numeric metrics or call syncMetrics/updateMetrics.
					for attribute, value in key_changes:
						setattr(target_layer, attribute, value)
				finally:
					glyph.endUndo()
				changed += 1
				changed_keys += len(key_changes)
		finally:
			self.font.enableUpdateInterface()

		self.w.close()
		message = "Copied %i metric key(s) in %i selected glyph(s)." % (changed_keys, changed)
		if skipped:
			message += " Skipped %i; see Macro Panel." % len(skipped)
			print("Skipped:")
			for skipped_message in skipped:
				print(skipped_message)
		print("%s\n%s → %s" % (message, self.master_labels[source_index], self.master_labels[target_index]))
		Glyphs.showNotification("Copy Metric Keys", message)


CopyMetricKeysBetweenMasters()
