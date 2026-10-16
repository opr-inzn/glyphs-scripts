# MenuTitle: Replace Components with Suffixed Versions
# -*- coding: utf-8 -*-

__doc__ = """
Asks for a suffix (e.g. .ss05, .sc, .case), then, in the selected glyph layers,
replaces each direct component with the suffixed version of that component when
the corresponding glyph exists. Component transforms and automatic-alignment
settings are preserved. Glyph- and layer-level metric keys are redirected to
matching suffixed glyphs as well.
"""

import re

from GlyphsApp import Glyphs, Message
from vanilla import Button, ComboBox, TextBox, Window


TITLE = "Replace Components"
DEFAULTS_KEY = "com.officeofpersonalresponsibility.ReplaceComponentsWithSuffixedVersions.suffix"
METRIC_KEY_ATTRIBUTES = (
	"leftMetricsKey",
	"rightMetricsKey",
	"widthMetricsKey",
)
GLYPH_METRIC_KEY_PATTERN = re.compile(
	r"^(==?)(\|?)([A-Za-z_.][A-Za-z0-9_.-]*)(.*)$"
)


def normalized_suffix(text):
	"""Return the suffix with a leading dot, or None if it is not usable."""
	suffix = (text or "").strip()
	if suffix and not suffix.startswith("."):
		suffix = "." + suffix
	if len(suffix) < 2 or re.search(r"[\s/]", suffix):
		return None
	return suffix


def metric_key_reference(key):
	"""Return the glyph name a metric key refers to, or None for literal keys."""
	if not isinstance(key, str):
		return None
	match = GLYPH_METRIC_KEY_PATTERN.match(key)
	return match.group(3) if match else None


def suffixed_metric_key(key, font, suffix):
	"""Return an updated glyph-reference key, or the original literal key."""
	if not isinstance(key, str):
		return key, None

	match = GLYPH_METRIC_KEY_PATTERN.match(key)
	if not match:
		# Leaves numbers and expressions such as 39, =39, =+20, and =| alone.
		return key, None

	equals, mirror, referenced_name, remainder = match.groups()
	if referenced_name.endswith(suffix):
		return key, None

	target_name = referenced_name + suffix
	if font.glyphs[target_name] is None:
		return key, target_name

	return "%s%s%s%s" % (equals, mirror, target_name, remainder), None


def update_metric_keys(owner, font, suffix, owner_label, missing_keys):
	updated = 0
	for attribute in METRIC_KEY_ATTRIBUTES:
		old_key = getattr(owner, attribute, None)
		new_key, missing_name = suffixed_metric_key(old_key, font, suffix)
		if missing_name:
			missing_keys.add("%s → %s on %s" % (old_key, missing_name, owner_label))
		elif new_key != old_key:
			setattr(owner, attribute, new_key)
			updated += 1
			print("%s: %s → %s" % (owner_label, old_key, new_key))
	return updated


def referenced_names(layers):
	"""Glyph names used as components or metric-key references in the layers."""
	names = set()
	for layer in layers:
		glyph = layer.parent
		if glyph is None:
			continue
		for component in layer.components:
			if component.componentName:
				names.add(component.componentName)
		for owner in (glyph, layer):
			for attribute in METRIC_KEY_ATTRIBUTES:
				name = metric_key_reference(getattr(owner, attribute, None))
				if name:
					names.add(name)
	return names


def available_suffixes(font, layers):
	"""Suffixes for which a suffixed counterpart of a referenced glyph exists."""
	references = referenced_names(layers)
	suffixes = set()
	for glyph in font.glyphs:
		name = glyph.name
		dot = name.find(".", 1)
		while dot != -1:
			if name[:dot] in references:
				suffixes.add(name[dot:])
			dot = name.find(".", dot + 1)
	return sorted(suffixes)


def replace_component(component, target_name):
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


def replace_components(font, layers, suffix):
	replaced_count = 0
	metric_key_count = 0
	missing = []
	missing_keys = set()
	self_references = []
	updated_glyph_names = set()

	font.disableUpdateInterface()
	try:
		for layer in layers:
			glyph = layer.parent
			if glyph is None:
				continue

			glyph.beginUndo()
			try:
				if glyph.name not in updated_glyph_names:
					metric_key_count += update_metric_keys(
						glyph,
						font,
						suffix,
						"%s (glyph)" % glyph.name,
						missing_keys,
					)
					updated_glyph_names.add(glyph.name)

				metric_key_count += update_metric_keys(
					layer,
					font,
					suffix,
					"%s, %s (layer)" % (glyph.name, layer.name),
					missing_keys,
				)

				for component in layer.components:
					source_name = component.componentName
					if not source_name or source_name.endswith(suffix):
						continue

					target_name = source_name + suffix
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

					replace_component(component, target_name)
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
		print("Missing %s glyphs:" % suffix)
		for message in missing:
			print("  %s" % message)

	if self_references:
		print("Skipped self-referencing components:")
		for message in self_references:
			print("  %s" % message)

	if missing_keys:
		print("Missing %s glyphs referenced by metric keys:" % suffix)
		for message in sorted(missing_keys):
			print("  %s" % message)

	Glyphs.redraw()
	message = "Replaced %i component(s) with %s and updated %i metric key(s)." % (
		replaced_count,
		suffix,
		metric_key_count,
	)
	if missing:
		message += " Missing %i %s counterpart(s)." % (len(missing), suffix)
	if self_references:
		message += " Skipped %i self-reference(s)." % len(self_references)
	if missing_keys:
		message += " Missing %i metric-key counterpart(s)." % len(missing_keys)
	Glyphs.showNotification(TITLE, message)


class ReplaceComponentsWithSuffixedVersions(object):

	def __init__(self):
		font = Glyphs.font
		if font is None:
			Message(title=TITLE, message="No font is open.")
			return
		if not font.selectedLayers:
			Message(title=TITLE, message="No glyphs are selected.")
			return

		suffixes = available_suffixes(font, font.selectedLayers)
		stored_suffix = Glyphs.defaults[DEFAULTS_KEY]
		if stored_suffix:
			initial_suffix = stored_suffix
		elif suffixes:
			initial_suffix = suffixes[0]
		else:
			initial_suffix = ""

		self.w = Window((380, 142), "Replace Components with Suffixed Versions")
		self.w.suffixLabel = TextBox((15, 18, 105, 22), "Replace with")
		self.w.suffix = ComboBox(
			(120, 15, 245, 22),
			suffixes,
			callback=self.validate,
		)
		self.w.suffix.set(initial_suffix)

		self.w.status = TextBox((15, 50, 350, 48), "", sizeStyle="small")
		self.w.cancelButton = Button((165, 106, 80, 24), "Cancel", callback=self.cancel_callback)
		self.w.cancelButton.getNSButton().setKeyEquivalent_("\x1b")
		self.w.cancelButton.getNSButton().setKeyEquivalentModifierMask_(0)
		self.w.replaceButton = Button((255, 106, 110, 24), "Replace", callback=self.replace_callback)
		self.w.setDefaultButton(self.w.replaceButton)
		self.validate(None)
		self.w.open()
		self.w.makeKey()

	def validate(self, sender):
		suffix = normalized_suffix(self.w.suffix.get())
		self.w.replaceButton.enable(suffix is not None)
		if suffix is None:
			self.w.status.set("Enter a suffix such as .ss05, .sc or .case.")
			return

		font = Glyphs.font
		if font is None:
			self.w.status.set("No font is open.")
			return

		total = 0
		available = 0
		for layer in font.selectedLayers:
			for component in layer.components:
				name = component.componentName
				if not name or name.endswith(suffix):
					continue
				total += 1
				if font.glyphs[name + suffix] is not None:
					available += 1
		self.w.status.set(
			"%i of %i component(s) in the selection have a %s version. "
			"Metric keys pointing to glyphs with a %s version are redirected too."
			% (available, total, suffix, suffix)
		)

	def cancel_callback(self, sender):
		self.w.close()

	def replace_callback(self, sender):
		suffix = normalized_suffix(self.w.suffix.get())
		if suffix is None:
			return

		font = Glyphs.font
		if font is None:
			Message(title=TITLE, message="No font is open.")
			return

		layers = list(font.selectedLayers)
		if not layers:
			Message(title=TITLE, message="No glyphs are selected.")
			return

		Glyphs.defaults[DEFAULTS_KEY] = suffix
		self.w.close()
		replace_components(font, layers, suffix)


ReplaceComponentsWithSuffixedVersions()
