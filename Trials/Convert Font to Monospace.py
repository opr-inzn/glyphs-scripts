# MenuTitle: Convert Font to Monospace
# -*- coding: utf-8 -*-

__doc__ = """
Converts every master and special layer in the open font to one advance width.
Outlines keep their original proportions and are centered when they already
fit. Only outlines wider than the mono width are horizontally squeezed.
Components are decomposed first to prevent nested scaling.
Custom naming overrides are cleared and all masters and exports are named Mono.
"""

import vanilla
from GlyphsApp import Glyphs


DEFAULTS_KEY = "com.officeofpersonalresponsibility.ConvertFontToMonospace.width"

NAMING_PROPERTY_KEYS = {
	"familynames",
	"stylenames",
	"postscriptfontname",
	"postscriptfullnames",
	"compatiblefullnames",
	"preferredfamilynames",
	"preferredsubfamilynames",
	"stylemapfamilynames",
	"stylemapstylenames",
	"variationspostscriptnameprefix",
	"wwsfamilyname",
	"wwssubfamilyname",
}

NAMING_PARAMETER_KEYS = {
	"familyname",
	"stylename",
	"fontname",
	"postscriptfontname",
	"postscriptfullname",
	"fullname",
	"compatiblefullname",
	"preferredfamilyname",
	"preferredsubfamilyname",
	"stylemapfamilyname",
	"stylemapstylename",
	"wwsfamilyname",
	"wwssubfamilyname",
	"filename",
	"nametableentry",
}


def normalized_key(value):
	return "".join(character.lower() for character in str(value or "") if character.isalnum())


def clear_naming_properties(owner):
	"""Remove complete naming fields, including all localized value rows."""
	properties = list(getattr(owner, "properties", []) or [])
	remover = getattr(owner, "removeObjectFromProperties_", None)

	cleared = 0
	for prop in properties:
		key = getattr(prop, "key", None) or getattr(prop, "name", None)
		if normalized_key(key) not in NAMING_PROPERTY_KEYS:
			continue

		if remover is not None:
			remover(prop)
		else:
			owner.properties.remove(prop)
		cleared += 1

	return cleared


def clear_naming_parameters(owner):
	parameters = getattr(owner, "customParameters", None)
	if parameters is None:
		return 0

	cleared = 0
	for parameter in list(parameters):
		name = getattr(parameter, "name", None)
		if normalized_key(name) in NAMING_PARAMETER_KEYS:
			parameters.remove(parameter)
			cleared += 1

	return cleared


def normalize_mono_naming(font):
	cleared = clear_naming_properties(font) + clear_naming_parameters(font)

	for master in font.masters:
		cleared += clear_naming_properties(master)
		cleared += clear_naming_parameters(master)
		master.name = "Mono"

	for instance in font.instances:
		cleared += clear_naming_properties(instance)
		cleared += clear_naming_parameters(instance)
		instance.name = "Mono"
		if hasattr(instance, "fontName"):
			instance.fontName = None

	return cleared


def editable_layers(glyph):
	return [
		layer
		for layer in glyph.layers
		if layer.isMasterLayer or layer.isSpecialLayer
	]


def fit_layer_to_width(layer, mono_width):
	"""Center the outline, squeezing only when its bounds exceed the width."""
	squeezed = False
	if layer.shapes:
		bounds = layer.bounds
		if bounds and bounds.size.width > 0:
			scale_x = min(1.0, mono_width / float(bounds.size.width))
			scaled_width = bounds.size.width * scale_x
			move_x = (mono_width - scaled_width) * 0.5 - bounds.origin.x * scale_x
			layer.applyTransform((scale_x, 0.0, 0.0, 1.0, move_x, 0.0))
			squeezed = scale_x < 1.0
	layer.width = mono_width
	return squeezed


def convert_font(font, mono_width):
	glyph_count = 0
	layer_count = 0
	squeezed_count = 0

	font.disableUpdateInterface()
	try:
		# Resolve every component against the untouched source font first. If a
		# base glyph were scaled before its composites were decomposed, those
		# composites could inherit the horizontal scaling twice.
		for glyph in font.glyphs:
			for layer in editable_layers(glyph):
				if layer.components:
					layer.decomposeComponents()

		for glyph in font.glyphs:
			layers = editable_layers(glyph)
			if not layers:
				continue

			glyph.beginUndo()
			try:
				# Existing metrics keys could restore proportional widths later.
				glyph.leftMetricsKey = None
				glyph.rightMetricsKey = None
				glyph.widthMetricsKey = None

				for layer in layers:
					if fit_layer_to_width(layer, mono_width):
						squeezed_count += 1

					layer_count += 1
			finally:
				glyph.endUndo()

			glyph_count += 1
	finally:
		font.enableUpdateInterface()

	cleared_naming_count = normalize_mono_naming(font)
	Glyphs.redraw()
	return glyph_count, layer_count, squeezed_count, cleared_naming_count


class ConvertFontToMonospace:
	def __init__(self):
		window_width = 360
		window_height = 182
		inset = 16

		self.w = vanilla.FloatingWindow(
			(window_width, window_height),
			"Convert Font to Monospace",
			minSize=(window_width, window_height),
			maxSize=(window_width, window_height),
		)
		self.w.explanation = vanilla.TextBox(
			(inset, 14, -inset, 62),
			"Center all master and special layers in one advance width, squeezing "
			"only outlines that are too wide. Components will be decomposed, metrics "
			"keys and custom naming cleared, and all styles renamed Mono.",
		)
		self.w.width_label = vanilla.TextBox(
			(inset, 84, 110, 22),
			"Mono width:",
		)
		stored_width = Glyphs.defaults[DEFAULTS_KEY] or 600
		try:
			stored_width = int(float(stored_width))
		except (TypeError, ValueError):
			stored_width = 600
		self.w.width_input = vanilla.EditText(
			(120, 80, 90, 24),
			str(stored_width),
			callback=self.validate,
		)
		self.w.units_label = vanilla.TextBox(
			(218, 84, -inset, 22),
			"units",
		)
		self.w.status = vanilla.TextBox(
			(inset, 114, -inset, 20),
			"",
		)
		self.w.convert_button = vanilla.Button(
			(-112, -38, -inset, 24),
			"Convert",
			callback=self.convert,
		)
		self.w.setDefaultButton(self.w.convert_button)
		self.validate(None)
		self.w.open()
		self.w.makeKey()

	def requested_width(self):
		try:
			width = float(self.w.width_input.get().strip())
		except (TypeError, ValueError):
			return None
		if width <= 0 or not width.is_integer():
			return None
		return int(width)

	def validate(self, sender):
		valid = self.requested_width() is not None
		self.w.convert_button.enable(valid)
		self.w.status.set("" if valid else "Enter a whole-number width greater than zero.")

	def convert(self, sender):
		font = Glyphs.font
		mono_width = self.requested_width()
		if font is None:
			self.w.status.set("No font is open.")
			return
		if mono_width is None:
			self.w.status.set("Enter a whole-number width greater than zero.")
			return

		Glyphs.defaults[DEFAULTS_KEY] = mono_width
		(
			glyph_count,
			layer_count,
			squeezed_count,
			cleared_naming_count,
		) = convert_font(font, mono_width)
		self.w.close()

		width_label = "%g" % mono_width
		message = "Converted %i glyphs and %i layers to %s units." % (
			glyph_count,
			layer_count,
			width_label,
		)
		if squeezed_count:
			message += " Squeezed %i over-wide layer(s)." % squeezed_count
		message += " Cleared %i naming override(s); styles are Mono." % cleared_naming_count

		print(message)
		Glyphs.showNotification("Convert Font to Monospace", message)


ConvertFontToMonospace()
