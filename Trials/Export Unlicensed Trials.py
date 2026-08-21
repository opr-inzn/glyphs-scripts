# MenuTitle: Export Unlicensed Trials
# -*- coding: utf-8 -*-

__doc__ = """
Export unlicensed trial fonts for all active non-variable instances.
Uses the OPR unlicensed naming scheme together with Hugo Jourdan's GUI/export flow.
"""

import re
import unicodedata

from vanilla import FloatingWindow, TextBox, TextEditor, PopUpButton, Button
from GlyphsApp import (
	Glyphs,
	GetFolder,
	Message,
	PLAIN,
	TTF,
	OTF,
	WOFF,
	WOFF2,
	INSTANCETYPEVARIABLE,
)


DEFAULT_GLYPHSET = (
	"A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z, "
	"a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z, "
	"zero, one, two, three, four, five, six, seven, eight, nine, space, comma, period, "
	"parenleft, parenright, exclam, question, at, ampersand, .notdef"
)


def sanitize_name(value, for_folder=False, keep_spaces=False):
	"""Normalize a string for filenames, PostScript names, or export folders."""
	if not value:
		return ""

	value = unicodedata.normalize("NFKD", value)
	value = "".join(c for c in value if not unicodedata.combining(c))
	value = value.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
	value = value.replace("_", "-").replace("'", "")
	value = re.sub(r"[^A-Za-z0-9\s-]+", "-", value)
	value = value.strip()
	value = re.sub(r"\s+", " " if (for_folder or keep_spaces) else "-", value)
	value = re.sub(r"-+", "-", value).strip("-").strip()
	return value


def sanitize_folder_family_name(value):
	"""Collapse family names to alphanumerics for export-folder prefixes."""
	return re.sub(r"[^A-Za-z0-9]+", "", sanitize_name(value))


def sanitize_style_name(value):
	"""Normalize style names for file-name segments."""
	return sanitize_name(value)


def normalize_name(value):
	if not value:
		return ""
	value = unicodedata.normalize("NFKD", value)
	value = "".join(c for c in value if not unicodedata.combining(c))
	return re.sub(r"\s+", " ", value.strip().lower())


def clean_family_name(value):
	if not value:
		return ""
	value = sanitize_name(value, keep_spaces=True)
	value = re.sub(r"[\s\-._]+$", "", value)
	return value.strip()


def get_effective_family_name(instance, fallback_family_name=""):
	family_name = None
	try:
		family_name = instance.customParameters["familyName"]
	except Exception:
		pass
	if not family_name:
		try:
			family_name = instance.propertyForKey_languageTag_("familyNames", None)
		except Exception:
			pass
	if not family_name:
		family_name = getattr(instance, "familyName", "")
	return family_name or fallback_family_name or ""


def is_unlicensed_instance(instance, fallback_family_name=""):
	family_name = get_effective_family_name(instance, fallback_family_name)
	return "unlicensed trial" in family_name.lower() if family_name else False


def parse_glyph_names(text_value):
	return [item.strip() for item in text_value.split(",") if item.strip()]


def remove_custom_parameters(instance, parameter_names):
	"""Remove inherited custom parameters so the trial export can force new values."""
	targets = {name.lower() for name in parameter_names}
	try:
		for index in range(len(instance.customParameters) - 1, -1, -1):
			parameter = instance.customParameters[index]
			if getattr(parameter, "name", "").lower() in targets:
				del instance.customParameters[index]
	except Exception:
		for parameter_name in parameter_names:
			try:
				del instance.customParameters[parameter_name]
			except Exception:
				pass


class ExportUnlicensedTrials(object):

	def __init__(self):
		self.defaultsPrefix = "com.opr.ExportUnlicensedTrials."
		self.defaultKeys()

		linePos, inset, lineHeight = 12, 15, 22
		x = Glyphs.defaults[self.defaultsPrefix + "windowPosX"]
		y = Glyphs.defaults[self.defaultsPrefix + "windowPosY"]

		self.w = FloatingWindow((x, y, 400, 200), title="Export unlicensed trials")
		self.w.textBox = TextBox(
			(inset, linePos, -inset, 17),
			"Trial glyphset (comma-separated glyph names)",
			sizeStyle="small",
		)
		self.w.textBox.getNSTextField().setToolTip_("All glyphs need to be separated by a comma")

		linePos += lineHeight
		self.w.textEditor = TextEditor(
			(inset, linePos, -inset, 100),
			text=Glyphs.defaults[self.defaultsPrefix + "glyphset"],
			callback=self.textEditorCallback,
		)

		linePos += 88
		linePos += lineHeight

		self.w.text = TextBox((inset, linePos, -inset, 40), "Export format:", sizeStyle="small")
		items = [TTF, OTF, WOFF, WOFF2]
		self.w.popUpButton = PopUpButton(
			(inset + 85, linePos - 2, -inset - 220, 17),
			items,
			sizeStyle="small",
			callback=self.exportFormatCallback,
		)

		selectedItem = Glyphs.defaults[self.defaultsPrefix + "selectedFormat"]
		if selectedItem in items:
			self.w.popUpButton.setItem(selectedItem)

		linePos += lineHeight
		self.w.buttonFolder = Button(
			(inset, linePos, -inset - 188, 20),
			"Select Save Folder",
			callback=self.buttonFolderCallback,
		)
		self.w.buttonGenerate = Button(
			(inset + 188, linePos, -inset, 20),
			"Generate trials",
			callback=self.buttonGenerateCallback,
		)

		if not Glyphs.defaults[self.defaultsPrefix + "saveFolder"]:
			self.w.buttonGenerate.enable(False)

		self.w.setDefaultButton(self.w.buttonGenerate)
		self.w.bind("close", self.windowClosed)
		self.w.open()

	def defaultKeys(self):
		defaults = {
			"windowPosX": 200,
			"windowPosY": 200,
			"glyphset": DEFAULT_GLYPHSET,
			"selectedFormat": TTF,
			"saveFolder": None,
		}
		for key, value in defaults.items():
			fullKey = self.defaultsPrefix + key
			if Glyphs.defaults[fullKey] is None:
				Glyphs.defaults[fullKey] = value

	def textEditorCallback(self, sender):
		Glyphs.defaults[self.defaultsPrefix + "glyphset"] = sender.get()

	def windowClosed(self, sender):
		windowPosSize = self.w.getPosSize()
		Glyphs.defaults[self.defaultsPrefix + "windowPosX"] = windowPosSize[0]
		Glyphs.defaults[self.defaultsPrefix + "windowPosY"] = windowPosSize[1]

	def exportFormatCallback(self, sender):
		Glyphs.defaults[self.defaultsPrefix + "selectedFormat"] = self.w.popUpButton.getItem()

	def buttonFolderCallback(self, sender):
		saveFolder = GetFolder(message="Select save location", allowsMultipleSelection=False, path=None)
		if saveFolder:
			Glyphs.defaults[self.defaultsPrefix + "saveFolder"] = saveFolder
			self.w.buttonGenerate.enable(True)
		else:
			self.w.buttonGenerate.enable(False)

	def build_unlicensed_instance(self, sourceInstance, fallbackFamilyName):
		baseFamily = clean_family_name(get_effective_family_name(sourceInstance, fallbackFamilyName))
		trialFamily = "%s UNLICENSED TRIAL" % baseFamily
		styleName = sourceInstance.name or ""
		fullName = ("%s %s" % (trialFamily, styleName)).strip()
		fileNameParts = [sanitize_folder_family_name(baseFamily)]
		sanitizedStyleName = sanitize_style_name(styleName)
		if sanitizedStyleName:
			fileNameParts.append(sanitizedStyleName)
		fileNameParts.append("UNLICENSED-TRIAL")
		fileName = "-".join(fileNameParts)

		newInstance = sourceInstance.copy()
		remove_custom_parameters(
			newInstance,
			[
				"familyName",
				"Family Name",
				"fileName",
				"File Name",
				"Export Folder",
			],
		)
		newInstance.setProperty_value_languageTag_("familyNames", trialFamily, None)
		newInstance.setProperty_value_languageTag_("postscriptFullNames", fullName, None)
		newInstance.fontName = fileName
		newInstance.customParameters["fileName"] = fileName
		newInstance.customParameters["Export Folder"] = "%s-UNLICENSED-TRIALS" % sanitize_folder_family_name(baseFamily)
		try:
			newInstance.visible = False
		except Exception:
			pass
		return newInstance, trialFamily, styleName

	def buttonGenerateCallback(self, sender):
		Glyphs.clearLog()
		Glyphs.showMacroWindow()
		print("[Export Unlicensed Trials is running]")

		saveFolder = Glyphs.defaults[self.defaultsPrefix + "saveFolder"]
		if not saveFolder or len(saveFolder) < 5:
			print("Please set saveFolder")
			return

		document = Glyphs.currentDocument
		font = document.font if document else Glyphs.font
		if not font:
			print("No font open.")
			return

		font.disableUpdateInterface()
		temporaryInstances = []
		featureBackup = []
		classBackup = {}
		exportedGlyphsBackup = []
		try:
			print("Save location : %s" % saveFolder)
			selectedGlyphNames = parse_glyph_names(self.w.textEditor.get())
			fontFormat = self.w.popUpButton.getItem()

			for glyph in font.glyphs:
				if glyph.export:
					exportedGlyphsBackup.append(glyph.name)

			for glyphClass in font.classes:
				classBackup[glyphClass.name] = glyphClass.active
				glyphClass.active = False

			for feature in font.features:
				featureBackup.append(feature.copy())

			for glyph in font.glyphs:
				glyph.export = glyph.name in selectedGlyphNames

			while len(font.features) > 0:
				del font.features[0]
			font.updateFeatures()

			if fontFormat in (TTF, OTF):
				fontFormat = PLAIN

			try:
				originals = [
					instance
					for instance in font.instances
					if instance.active
					and instance.type != INSTANCETYPEVARIABLE
					and not is_unlicensed_instance(instance, font.familyName)
				]
			except Exception:
				originals = [
					instance
					for instance in font.instances
					if instance.active and not is_unlicensed_instance(instance, font.familyName)
				]

			print(
				"════════════════════════════════════════════════════════\n"
				"Font : %s\n"
				"Active Instance : %s\n"
				"════════════════════════════════════════════════════════"
				% (font.familyName, len(originals))
			)

			existingTrialInstances = {}
			for instance in font.instances:
				if not is_unlicensed_instance(instance, font.familyName):
					continue
				key = (
					normalize_name(get_effective_family_name(instance, font.familyName)),
					normalize_name(instance.name or ""),
				)
				existingTrialInstances[key] = instance

			for sourceInstance in originals:
				tempInstance, trialFamily, styleName = self.build_unlicensed_instance(sourceInstance, font.familyName)
				trialKey = (normalize_name(trialFamily), normalize_name(styleName))
				exportInstance = existingTrialInstances.get(trialKey)
				if exportInstance:
					print(
						"ℹ️ Using existing unlicensed instance for %s %s\n"
						"--------------------------------------------------------"
						% (trialFamily, styleName)
					)
				else:
					font.instances.append(tempInstance)
					temporaryInstances.append(tempInstance)
					exportInstance = tempInstance

				exportStatement = exportInstance.generate(FontPath=saveFolder, Containers=[fontFormat])
				if exportStatement is not True:
					print(exportStatement)
					print(
						"⚠️ %s %s not generated correctly\n"
						"⚠️ (Export it with Cmd+E to access export report)\n"
						"--------------------------------------------------------"
						% (trialFamily, styleName)
					)
				else:
					print(
						"✅ %s %s generated\n"
						"--------------------------------------------------------"
						% (trialFamily, styleName)
					)

			print("Restoring initial instances... (it can last a minute)")

		finally:
			for tempInstance in reversed(temporaryInstances):
				try:
					font.instances.remove(tempInstance)
				except Exception:
					pass

			for glyph in font.glyphs:
				glyph.export = False
			for glyphName in exportedGlyphsBackup:
				if font.glyphs[glyphName]:
					font.glyphs[glyphName].export = True

			while len(font.features) > 0:
				del font.features[0]
			for feature in featureBackup:
				font.features.append(feature)

			for glyphClass in font.classes:
				glyphClass.active = classBackup.get(glyphClass.name, True)

			font.enableUpdateInterface()

		Message("All exports are done", title="Unlicensed Trial Exports", OKButton=None)


ExportUnlicensedTrials()
