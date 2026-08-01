#MenuTitle: Remove Orphaned Kerning Classes...
# -*- coding: utf-8 -*-
from __future__ import print_function, division, unicode_literals
__doc__ = """
(GUI) Finds kerning classes that are referenced by kerning pairs but are no
longer assigned to glyphs, and replaces each selected orphan with a valid
kerning class.
"""

import vanilla
from AppKit import NSAlert, NSAlertFirstButtonReturn
from GlyphsApp import Glyphs, Message


SCRIPT_NAME = "Remove Orphaned Kerning Classes"


def apiKey(font, key):
	"""Convert an internal glyph ID to a name accepted by the kerning API."""
	if key.startswith("@"):
		return key
	glyph = font.glyphForId_(key)
	return glyph.name if glyph else key


def assignedGroups(font):
	"""
	Groups used on the left of pairs come from glyph.rightKerningGroup and use
	@MMK_L_. Groups used on the right come from glyph.leftKerningGroup and use
	@MMK_R_.
	"""
	groupsOnLeft = set()
	groupsOnRight = set()
	for glyph in font.glyphs:
		if glyph.rightKerningGroup:
			groupsOnLeft.add(glyph.rightKerningGroup)
		if glyph.leftKerningGroup:
			groupsOnRight.add(glyph.leftKerningGroup)
	return groupsOnLeft, groupsOnRight


def orphanedReferences(font):
	groupsOnLeft, groupsOnRight = assignedGroups(font)
	orphans = {}

	for master in font.masters:
		masterKerning = font.kerning.get(master.id, {})
		for left in list(masterKerning.keys()):
			rightPairs = masterKerning[left]
			if rightPairs is None:
				continue
			for right in list(rightPairs.keys()):
				matches = {}

				if left.startswith("@MMK_L_"):
					name = left[len("@MMK_L_"):]
					if name not in groupsOnLeft:
						matches.setdefault(name, set()).add("left")

				if right.startswith("@MMK_R_"):
					name = right[len("@MMK_R_"):]
					if name not in groupsOnRight:
						matches.setdefault(name, set()).add("right")

				for name, sides in matches.items():
					orphans.setdefault(name, []).append({
						"masterID": master.id,
						"masterName": master.name,
						"left": left,
						"right": right,
						"value": rightPairs[right],
						"orphanSides": sides,
					})

	return orphans


def sidesForReferences(references):
	sides = set()
	for reference in references:
		sides.update(reference["orphanSides"])
	return sides


def sideDescription(references):
	sides = sidesForReferences(references)
	if sides == {"left", "right"}:
		return "both sides"
	if "left" in sides:
		return "left side"
	return "right side"


def replacementGroups(font, references):
	groupsOnLeft, groupsOnRight = assignedGroups(font)
	sides = sidesForReferences(references)
	if sides == {"left", "right"}:
		return sorted(groupsOnLeft & groupsOnRight, key=lambda value: value.lower())
	if "left" in sides:
		return sorted(groupsOnLeft, key=lambda value: value.lower())
	return sorted(groupsOnRight, key=lambda value: value.lower())


def replacementKeys(reference, replacement):
	left = reference["left"]
	right = reference["right"]
	if "left" in reference["orphanSides"]:
		left = "@MMK_L_" + replacement
	if "right" in reference["orphanSides"]:
		right = "@MMK_R_" + replacement
	return left, right


def existingValue(font, masterID, left, right):
	masterKerning = font.kerning.get(masterID, {})
	rightPairs = masterKerning.get(left)
	if rightPairs is None or right not in rightPairs:
		return None
	return rightPairs[right]


def confirmationText(orphan, replacement, references):
	lines = [
		"Replace “%s” with “%s”." % (orphan, replacement),
		"Used on: %s" % sideDescription(references),
		"References: %i" % len(references),
		"",
	]
	for reference in references:
		newLeft, newRight = replacementKeys(reference, replacement)
		lines.append(
			"%s: %s × %s = %s\n→ %s × %s"
			% (
				reference["masterName"],
				reference["left"],
				reference["right"],
				reference["value"],
				newLeft,
				newRight,
			)
		)
	return "\n".join(lines)


def confirmReplacement(orphan, replacement, references):
	alert = NSAlert.alloc().init()
	alert.setMessageText_("Replace orphaned kerning class?")
	alert.setInformativeText_(
		confirmationText(orphan, replacement, references)
	)
	alert.addButtonWithTitle_("Replace References")
	alert.addButtonWithTitle_("Cancel")
	return alert.runModal() == NSAlertFirstButtonReturn


class RemoveOrphanedKerningClasses(object):
	def __init__(self):
		self.font = Glyphs.font
		if self.font is None:
			Message(
				title=SCRIPT_NAME,
				message="Open a Glyphs file before running this script.",
				OKButton="OK",
			)
			return

		self.orphans = {}
		self.orphanNames = []
		self.replacementNames = []

		windowWidth = 540
		windowHeight = 205
		margin = 15

		self.w = vanilla.FloatingWindow(
			(windowWidth, windowHeight),
			SCRIPT_NAME,
			minSize=(windowWidth, windowHeight),
			maxSize=(windowWidth + 180, windowHeight),
			autosaveName="com.OPR.RemoveOrphanedKerningClasses.mainwindow",
		)
		self.w.orphanLabel = vanilla.TextBox(
			(margin, 18, 130, 20), "Orphaned class", sizeStyle="regular"
		)
		self.w.orphanPopup = vanilla.PopUpButton(
			(145, 15, -margin, 24),
			[],
			sizeStyle="regular",
			callback=self.orphanChanged,
		)
		self.w.replacementLabel = vanilla.TextBox(
			(margin, 55, 130, 20), "Replace with", sizeStyle="regular"
		)
		self.w.replacementPopup = vanilla.PopUpButton(
			(145, 52, -margin, 24),
			[],
			sizeStyle="regular",
		)
		self.w.summary = vanilla.TextBox(
			(margin, 91, -margin, 45), "", sizeStyle="small"
		)
		self.w.refreshButton = vanilla.Button(
			(margin, -42, 90, 24),
			"Refresh",
			sizeStyle="regular",
			callback=self.refresh,
		)
		self.w.runButton = vanilla.Button(
			(-175, -42, -margin, 24),
			"Replace References",
			sizeStyle="regular",
			callback=self.replaceSelected,
		)
		self.w.setDefaultButton(self.w.runButton)

		self.refresh()
		self.w.open()
		self.w.makeKey()

	def orphanDisplayItems(self):
		items = []
		for name in self.orphanNames:
			references = self.orphans[name]
			items.append(
				"%s — %s — %i reference%s"
				% (
					name,
					sideDescription(references),
					len(references),
					"" if len(references) == 1 else "s",
				)
			)
		return items

	def refresh(self, sender=None):
		self.orphans = orphanedReferences(self.font)
		self.orphanNames = sorted(
			self.orphans.keys(), key=lambda value: value.lower()
		)
		self.w.orphanPopup.setItems(self.orphanDisplayItems())

		hasOrphans = bool(self.orphanNames)
		self.w.orphanPopup.enable(hasOrphans)
		self.w.replacementPopup.enable(hasOrphans)
		self.w.runButton.enable(hasOrphans)

		if hasOrphans:
			self.w.orphanPopup.set(0)
			self.orphanChanged(self.w.orphanPopup)
		else:
			self.replacementNames = []
			self.w.replacementPopup.setItems([])
			self.w.summary.set(
				"No orphaned kerning-class references were found."
			)

	def orphanChanged(self, sender):
		if not self.orphanNames:
			return
		orphan = self.orphanNames[self.w.orphanPopup.get()]
		references = self.orphans[orphan]
		self.replacementNames = replacementGroups(self.font, references)
		self.w.replacementPopup.setItems(self.replacementNames)

		hasReplacements = bool(self.replacementNames)
		self.w.replacementPopup.enable(hasReplacements)
		self.w.runButton.enable(hasReplacements)
		self.w.summary.set(
			"%s is orphaned on the %s and is referenced %i time%s."
			% (
				orphan,
				sideDescription(references),
				len(references),
				"" if len(references) == 1 else "s",
			)
		)

	def replaceSelected(self, sender):
		if not self.orphanNames or not self.replacementNames:
			return

		orphan = self.orphanNames[self.w.orphanPopup.get()]
		replacement = self.replacementNames[self.w.replacementPopup.get()]
		references = list(self.orphans[orphan])

		if not confirmReplacement(orphan, replacement, references):
			return

		replaced = 0
		conflicts = []
		self.font.disableUpdateInterface()
		try:
			for reference in references:
				newLeft, newRight = replacementKeys(reference, replacement)
				currentValue = existingValue(
					self.font, reference["masterID"], newLeft, newRight
				)

				if currentValue is None:
					self.font.setKerningForPair(
						reference["masterID"],
						apiKey(self.font, newLeft),
						apiKey(self.font, newRight),
						reference["value"],
					)
				elif currentValue != reference["value"]:
					conflicts.append(
						"%s: %s × %s already equals %s; kept existing value."
						% (
							reference["masterName"],
							newLeft,
							newRight,
							currentValue,
						)
					)

				self.font.removeKerningForPair(
					reference["masterID"],
					apiKey(self.font, reference["left"]),
					apiKey(self.font, reference["right"]),
				)
				replaced += 1
		finally:
			self.font.enableUpdateInterface()

		Glyphs.clearLog()
		print(SCRIPT_NAME)
		print(confirmationText(orphan, replacement, references))
		if conflicts:
			print("\nConflicts:")
			for conflict in conflicts:
				print("- " + conflict)
		print("\nReplaced %i reference(s)." % replaced)

		self.refresh()

		message = "Replaced %i reference%s from “%s” with “%s”." % (
			replaced,
			"" if replaced == 1 else "s",
			orphan,
			replacement,
		)
		if conflicts:
			message += (
				"\n\n%i existing destination value%s kept. See Macro panel."
				% (len(conflicts), "" if len(conflicts) == 1 else "s")
			)
			Glyphs.showMacroWindow()

		Message(
			title=SCRIPT_NAME,
			message=message,
			OKButton="OK",
		)


RemoveOrphanedKerningClasses()
