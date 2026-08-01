# MenuTitle: Copy Font Info to Other Font
# -*- coding: utf-8 -*-
"""
Copy font information from one open font to another.

The target font's family/postscript naming fields and axis definitions are
deliberately preserved. Glyphs, layers, and kerning are not touched.
"""

from __future__ import print_function, unicode_literals

import copy
from collections import Counter

import vanilla
from GlyphsApp import Glyphs, Message


NAME_PROPERTY_KEYS = {
	"familynames",
	"postscriptfontname",
	"postscriptfullnames",
	"compatiblefullnames",
	"preferredfamilynames",
	"stylemapfamilynames",
	"wwsfamilyname",
}

NAME_PARAMETER_KEYS = {
	"familyname",
	"fontname",
	"postscriptfontname",
	"fullname",
}

AXIS_PARAMETER_KEYS = {
	"axis",
	"axes",
	"axismappings",
	"axislocation",
}

COPY_OPTIONS = (
	("metadata", "General metadata, version, UPM, grid, and settings"),
	("properties", "Font properties, excluding naming fields"),
	("custom_parameters", "Custom parameters, excluding name/axis parameters"),
	("masters", "Master settings"),
	("master_guides", "Master guides"),
	("instances", "Instances"),
	("features", "Features"),
	("prefixes", "Feature prefixes"),
	("classes", "Classes"),
	("user_data", "Font and master user data"),
)


class FontInfoCopier(object):

	def __init__(self):
		self.fonts = list(Glyphs.fonts)
		if len(self.fonts) < 2:
			Message(
				title="Copy Font Info",
				message="Open at least two fonts: one source and one target.",
			)
			return

		self.font_labels = self.unique_font_labels()
		current_index = self.index_for_font(Glyphs.font)
		target_index = 0 if current_index != 0 else 1

		self.w = vanilla.Window((520, 460), "Copy Font Info – Glyphs 4")
		self.w.sourceLabel = vanilla.TextBox((20, 20, 125, 22), "Source font")
		self.w.source = vanilla.PopUpButton((150, 16, -20, 24), self.font_labels)
		self.w.source.set(current_index)

		self.w.targetLabel = vanilla.TextBox((20, 56, 125, 22), "Target font")
		self.w.target = vanilla.PopUpButton((150, 52, -20, 24), self.font_labels)
		self.w.target.set(target_index)

		self.w.note = vanilla.TextBox(
			(20, 94, -20, 40),
			"Select what to copy. The target family/name fields and axis definitions "
			"are always preserved. Glyphs, layers, and kerning are never touched.",
			sizeStyle="small",
		)
		self.w.optionsLabel = vanilla.TextBox((20, 142, -20, 20), "Copy:")
		self.option_controls = {}
		for index, (key, label) in enumerate(COPY_OPTIONS):
			y = 166 + (index * 24)
			control = vanilla.CheckBox((20, y, -20, 20), label)
			control.set(True)
			self.option_controls[key] = control
			setattr(self.w, "option_%s" % key, control)

		self.w.cancelButton = vanilla.Button(
			(-205, -38, 85, 24), "Cancel", callback=self.cancel_callback
		)
		self.w.copyButton = vanilla.Button(
			(-110, -38, 90, 24), "Copy", callback=self.copy_callback
		)
		self.w.setDefaultButton(self.w.copyButton)
		self.w.open()
		self.w.makeKey()

	def unique_font_labels(self):
		raw_labels = [self.font_label(font) for font in self.fonts]
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

	def font_label(self, font):
		family_name = getattr(font, "familyName", None) or "Untitled"
		file_path = getattr(font, "filepath", None)
		if file_path:
			try:
				file_name = file_path.lastPathComponent()
			except Exception:
				file_name = str(file_path).split("/")[-1]
			return "%s (%s)" % (family_name, file_name)
		return str(family_name)

	def index_for_font(self, font):
		for index, open_font in enumerate(self.fonts):
			if open_font == font:
				return index
		return 0

	def cancel_callback(self, sender):
		self.w.hide()

	def copy_callback(self, sender):
		source_font = self.fonts[self.w.source.get()]
		target_font = self.fonts[self.w.target.get()]

		if source_font == target_font:
			Message(title="Copy Font Info", message="Choose two different fonts.")
			return

		options = {
			key: control.get() for key, control in self.option_controls.items()
		}
		if not any(options.values()):
			Message(title="Copy Font Info", message="Select at least one category to copy.")
			return

		Glyphs.clearLog()
		Glyphs.showMacroWindow()
		print("COPY FONT INFO TO OTHER FONT\n")
		print("Source: %s" % self.font_label(source_font))
		print("Target: %s" % self.font_label(target_font))
		print("Preserved: target name fields and axes")
		print()

		# Do not disable the target interface here. In Glyphs 4, Font Info's
		# NSArrayController relies on the KVO notifications emitted while these
		# values change; suppressing interface updates also suppresses that path.
		result = self.copy_font_info(source_font, target_font, options)

		self.w.hide()
		self.report(result, source_font, target_font)

	def copy_font_info(self, source_font, target_font, options):
		result = {
			"scalar_values": 0,
			"properties": 0,
			"custom_parameters": 0,
			"masters": 0,
			"instances": 0,
			"features": 0,
			"prefixes": 0,
			"classes": 0,
			"warnings": [],
		}

		if options.get("metadata"):
			print("Copying general metadata...")
			# Localized string fields must go through setProperty below. Directly
			# assigning e.g. font.manufacturer can bypass GSFont KVO notifications.
			self.copy_localized_metadata(source_font, target_font, result)

			# These are the remaining regular Font Info accessors. Do not include
			# familyName, familyNames, fontName, or fullName: the target keeps its identity.
			font_attributes = (
				"versionMajor",
				"versionMinor",
				"date",
				"note",
				"gridMain",
				"gridSubDivision",
				"disablesNiceNames",
				"disablesAutomaticAlignment",
				"keepAlternatesTogether",
			)
			for attribute in font_attributes:
				self.copy_attribute(source_font, target_font, attribute, result)

			# Glyphs has exposed both .upm and .unitsPerEm over different API versions.
			if hasattr(source_font, "upm") and hasattr(target_font, "upm"):
				self.copy_attribute(source_font, target_font, "upm", result)
			else:
				self.copy_attribute(source_font, target_font, "unitsPerEm", result)

		if options.get("user_data"):
			print("Copying font user data...")
			self.copy_user_data(source_font, target_font, result)
		if options.get("custom_parameters"):
			print("Copying custom parameters...")
			self.copy_custom_parameters(source_font, target_font, result)
		if options.get("properties"):
			print("Copying font properties...")
			self.copy_properties(source_font, target_font, result)
		if options.get("masters"):
			print("Copying master settings...")
			self.copy_masters(
				source_font,
				target_font,
				result,
				copy_properties=options.get("properties"),
				copy_custom_parameters=options.get("custom_parameters"),
				copy_guides=options.get("master_guides"),
				copy_user_data=options.get("user_data"),
			)
		elif options.get("master_guides"):
			print("Copying master guides...")
			self.copy_master_guides(source_font, target_font, result)
		if options.get("instances"):
			print("Copying instances...")
			self.copy_instances(source_font, target_font, result)
		if options.get("features"):
			print("Copying features...")
			self.copy_collection(source_font, target_font, "features", result)
		if options.get("prefixes"):
			print("Copying feature prefixes...")
			self.copy_collection(source_font, target_font, "featurePrefixes", result)
		if options.get("classes"):
			print("Copying classes...")
			self.copy_collection(source_font, target_font, "classes", result)

		return result

	def copy_localized_metadata(self, source, target, result):
		"""Copy localized metadata through GSFont's KVO-safe property setter."""
		localized_fields = (
			("copyright", "copyrights"),
			("designer", "designers"),
			("designerURL", "designerURL"),
			("manufacturer", "manufacturers"),
			("manufacturerURL", "manufacturerURL"),
			("license", "licenses"),
			("licenseURL", "licenseURL"),
		)
		setter = getattr(target, "setProperty_value_languageTag_", None)
		if setter is None:
			for attribute, unused_property_key in localized_fields:
				self.copy_attribute(source, target, attribute, result)
			return

		for attribute, property_key in localized_fields:
			if not hasattr(source, attribute):
				continue
			try:
				setter(property_key, self.clone_value(getattr(source, attribute)), None)
				result["scalar_values"] += 1
			except Exception as error:
				result["warnings"].append(
					"Could not copy font.%s through %s: %s"
					% (attribute, property_key, error)
				)

	def copy_attribute(self, source, target, attribute, result, object_label="font"):
		if not hasattr(source, attribute) or not hasattr(target, attribute):
			return
		value = self.clone_value(getattr(source, attribute))
		try:
			setattr(target, attribute, value)
			result["scalar_values"] += 1
		except Exception as error:
			# Some Glyphs 4 Python properties report as read-only even though their
			# Objective-C setter is available, e.g. gridMain and keepAlternatesTogether.
			setter_name = "set%s%s_" % (attribute[0].upper(), attribute[1:])
			setter = getattr(target, setter_name, None)
			if setter:
				try:
					setter(value)
					result["scalar_values"] += 1
					return
				except Exception as setter_error:
					error = setter_error
			result["warnings"].append(
				"Could not copy %s.%s: %s" % (object_label, attribute, error)
			)

	def copy_user_data(self, source, target, result):
		if not hasattr(source, "userData") or not hasattr(target, "userData"):
			return
		try:
			target.userData = self.clone_value(source.userData)
		except Exception as error:
			result["warnings"].append("Could not copy font userData: %s" % error)

	def copy_custom_parameters(self, source, target, result):
		source_parameters = list(getattr(source, "customParameters", []) or [])
		target_parameters = getattr(target, "customParameters", None)
		if target_parameters is None:
			return

		# Preserve target parameters that encode the excluded name or axis data.
		preserved = []
		for parameter in list(target_parameters):
			if self.is_excluded_parameter(getattr(parameter, "name", None)):
				preserved.append(parameter)

		self.clear_collection(target_parameters)
		for parameter in preserved:
			target_parameters.append(parameter)
		for parameter in source_parameters:
			if self.is_excluded_parameter(getattr(parameter, "name", None)):
				continue
			target_parameters.append(self.clone_object(parameter))
			result["custom_parameters"] += 1

	def is_excluded_parameter(self, name):
		key = self.normalized_key(name)
		return key in NAME_PARAMETER_KEYS or key in AXIS_PARAMETER_KEYS

	def copy_properties(self, source, target, result):
		source_properties = list(getattr(source, "properties", []) or [])
		target_properties = getattr(target, "properties", None)
		if target_properties is None:
			return

		# Do not replace or remove GSFontInfoProperty objects. Glyphs 4's Font Info
		# NSArrayController observes derived keys such as manufacturers, and changing
		# the property object's identity breaks that observer. setProperty updates the
		# existing value in place and sends the required KVO notifications.
		for prop in source_properties:
			if self.is_name_property(self.property_key(prop)):
				continue
			if self.copy_property_object(prop, target):
				result["properties"] += 1

	def property_key(self, prop):
		return getattr(prop, "key", None) or getattr(prop, "name", None)

	def is_name_property(self, name):
		return self.normalized_key(name) in NAME_PROPERTY_KEYS

	def copy_masters(
		self,
		source,
		target,
		result,
		copy_properties=True,
		copy_custom_parameters=True,
		copy_guides=True,
		copy_user_data=True,
	):
		source_masters = list(getattr(source, "masters", []) or [])
		target_masters = list(getattr(target, "masters", []) or [])
		if len(source_masters) != len(target_masters):
			result["warnings"].append(
				"Master count differs (source %i, target %i); matched masters were copied by order."
				% (len(source_masters), len(target_masters))
			)

		master_attributes = (
			"name",
			"weight",
			"width",
			"custom",
			"weightValue",
			"widthValue",
			"customValue",
			"defaultItalicAngle",
			"ascender",
			"capHeight",
			"descender",
			"xHeight",
			"italicAngle",
		)

		for index in range(min(len(source_masters), len(target_masters))):
			source_master = source_masters[index]
			target_master = target_masters[index]
			for attribute in master_attributes:
				self.copy_attribute(
					source_master,
					target_master,
					attribute,
					result,
					object_label="master %i" % (index + 1),
				)
			if copy_guides:
				self.copy_master_collection(source_master, target_master, "guides", result)
			if copy_properties:
				self.copy_master_collection(source_master, target_master, "properties", result)
			if copy_custom_parameters:
				self.copy_master_collection(source_master, target_master, "customParameters", result)
			if copy_user_data:
				self.copy_attribute(source_master, target_master, "userData", result, "master %i" % (index + 1))
			result["masters"] += 1

	def copy_master_guides(self, source, target, result):
		source_masters = list(getattr(source, "masters", []) or [])
		target_masters = list(getattr(target, "masters", []) or [])
		for index in range(min(len(source_masters), len(target_masters))):
			self.copy_master_collection(
				source_masters[index], target_masters[index], "guides", result
			)

	def copy_master_collection(self, source, target, attribute, result):
		source_values = getattr(source, attribute, None)
		target_values = getattr(target, attribute, None)
		if source_values is None or target_values is None:
			return
		if attribute == "properties":
			for value in list(source_values):
				self.copy_property_object(value, target)
			return
		self.clear_collection(target_values)
		for value in list(source_values):
			target_values.append(self.clone_object(value))

	def copy_property_object(self, source_property, target):
		"""Copy one GSFontInfoProperty through its KVO-safe setter."""
		property_key = self.property_key(source_property)
		if not property_key:
			return False

		setter = getattr(target, "setProperty_value_languageTag_", None)
		if setter is None:
			add_method = getattr(target, "addProperty_", None)
			if add_method:
				add_method(self.clone_object(source_property))
			else:
				getattr(target, "properties").append(self.clone_object(source_property))
			return True

		values = getattr(source_property, "values", None)
		try:
			values = list(values or [])
		except Exception:
			values = []

		if values:
			for value_object in values:
				value = getattr(value_object, "value", None)
				language_tag = getattr(value_object, "languageTag", None)
				setter(property_key, self.clone_value(value), language_tag)
		else:
			# GSInfoValueSingle.defaultValue is an Objective-C selector in Glyphs 4,
			# whereas .value is the actual stored string/value.
			single_value = getattr(source_property, "value", None)
			if single_value is not None:
				setter(property_key, self.clone_value(single_value), None)
		return True

	def copy_instances(self, source, target, result):
		source_instances = list(getattr(source, "instances", []) or [])
		target_instances = getattr(target, "instances", None)
		if target_instances is None:
			return

		source_masters = list(getattr(source, "masters", []) or [])
		target_masters = list(getattr(target, "masters", []) or [])
		master_id_map = {}
		for index in range(min(len(source_masters), len(target_masters))):
			master_id_map[getattr(source_masters[index], "id", None)] = getattr(target_masters[index], "id", None)

		self.clear_collection(target_instances)
		for source_instance in source_instances:
			target_instance = self.clone_object(source_instance)
			try:
				target_instance.font = target
			except Exception:
				pass
			self.remap_instance_interpolations(
				source_instance, target_instance, master_id_map
			)
			target_instances.append(target_instance)
			result["instances"] += 1

	def remap_instance_interpolations(self, source_instance, target_instance, master_id_map):
		if not getattr(source_instance, "manualInterpolation", False):
			try:
				target_instance.updateInterpolationValues()
			except Exception:
				pass
			return

		interpolations = getattr(source_instance, "instanceInterpolations", None)
		if not interpolations:
			return
		mapped = {}
		for source_id, value in interpolations.items():
			target_id = master_id_map.get(source_id)
			if target_id:
				mapped[target_id] = value
		try:
			target_instance.instanceInterpolations = mapped
		except Exception:
			pass

	def copy_collection(self, source, target, attribute, result):
		source_values = getattr(source, attribute, None)
		target_values = getattr(target, attribute, None)
		if source_values is None or target_values is None:
			return
		self.clear_collection(target_values)
		for value in list(source_values):
			target_values.append(self.clone_object(value))
		count_key = {
			"features": "features",
			"featurePrefixes": "prefixes",
			"classes": "classes",
		}.get(attribute)
		if count_key:
			result[count_key] = len(source_values)

	def clear_collection(self, collection):
		while len(collection) > 0:
			del collection[0]

	def normalized_key(self, value):
		if value is None:
			return ""
		return "".join(character for character in str(value).lower() if character.isalnum())

	def clone_object(self, value):
		try:
			return value.copy()
		except Exception:
			return self.clone_value(value)

	def clone_value(self, value):
		if value is None or isinstance(value, (str, int, float, bool)):
			return value
		if isinstance(value, (list, tuple)):
			return [self.clone_value(item) for item in value]
		try:
			return copy.deepcopy(value)
		except Exception:
			try:
				return value.copy()
			except Exception:
				return value

	def report(self, result, source, target):
		print("Done.")
		print("  Scalar font values: %i" % result["scalar_values"])
		print("  Font properties: %i" % result["properties"])
		print("  Custom parameters: %i" % result["custom_parameters"])
		print("  Masters matched: %i" % result["masters"])
		print("  Instances: %i" % result["instances"])
		print("  Features: %i" % result["features"])
		print("  Feature prefixes: %i" % result["prefixes"])
		print("  Classes: %i" % result["classes"])

		if result["warnings"]:
			print("\nWarnings:")
			for warning in sorted(set(result["warnings"])):
				print("  %s" % warning)

		message = (
			"Copied font info from %s to %s.\n\n"
			"The target name fields and axes were preserved."
			% (self.font_label(source), self.font_label(target))
		)
		if result["warnings"]:
			message += "\nSee the Macro Window for warnings."
		Message(title="Copy Font Info", message=message)


copyFontInfoController = FontInfoCopier()
