#MenuTitle: Rename Kerning Groups...
# -*- coding: utf-8 -*-
from __future__ import print_function, division, unicode_literals
__doc__ = """
(GUI) Lets you rename kerning names and pairs associated with them.
"""

import vanilla
from GlyphsApp import Glyphs

thisFont = Glyphs.font


def apiKeyForKerningKey(key):
	"""Convert an internal glyph ID to a glyph name accepted by the kerning API."""
	if key.startswith("@"):
		return key
	glyph = thisFont.glyphForId_(key)
	return glyph.name if glyph else key


# Build a stable snapshot of all pairs before changing any of them.
# GSFont.kerningDict() was removed; GSFont.kerning is the Glyphs 3 API.
newKernDic = {}
for thisMaster in thisFont.masters:
	kernList = []
	masterKerning = thisFont.kerning.get(thisMaster.id, {})
	for key1 in masterKerning:
		rightKerning = masterKerning[key1]
		if rightKerning is None:
			continue
		for key2 in rightKerning:
			pairInList = [key1, key2, rightKerning[key2]]
			kernList.append(pairInList)
	newKernDic[thisMaster.id] = kernList

# building popup list
# each value contains a list of glyphs involved. groupsL/R[groupName][glyph, glyph, glyph...]
groupsL = {}
groupsR = {}
for thisGlyph in thisFont.glyphs:
	if thisGlyph.leftKerningGroup is not None:
		if thisGlyph.leftKerningGroup not in groupsL:
			groupsL[thisGlyph.leftKerningGroup] = []
		groupsL[thisGlyph.leftKerningGroup].append(thisGlyph.name)

	if thisGlyph.rightKerningGroup is not None:
		if thisGlyph.rightKerningGroup not in groupsR:
			groupsR[thisGlyph.rightKerningGroup] = []
		groupsR[thisGlyph.rightKerningGroup].append(thisGlyph.name)


class RenameKerningGroups(object):
	def __init__(self):
		editX = 180
		editY = 22
		textY = 17
		spaceX = 10
		spaceY = 10
		windowWidth = spaceX * 3 + editX * 2 + 85
		windowHeight = 150

		self.w = vanilla.FloatingWindow(
			(windowWidth, windowHeight),
			"Rename Kerning Groups",
			minSize=(windowWidth, windowHeight),
			maxSize=(windowWidth + 100, windowHeight),
			autosaveName="com.Tosche.RenameKerningGroups.mainwindow"
		)

		self.w.radio = vanilla.RadioGroup((spaceX + 130, spaceY, 120, textY), ["Left", "Right"], isVertical=False, sizeStyle="regular", callback=self.switchList)
		self.w.radio.set(0)
		self.w.text1 = vanilla.TextBox((spaceX, spaceY * 2 + textY, 120, textY), "Rename this Group", sizeStyle="regular")
		self.w.text2 = vanilla.TextBox((spaceX, spaceY * 3 + editY + textY, 120, textY), "to this", sizeStyle="regular")
		self.w.popup = vanilla.PopUpButton((spaceX + 130, spaceY * 2 + textY, -15, editY), sorted(groupsL), sizeStyle="regular")
		self.w.newName = vanilla.EditText((spaceX + 130, spaceY * 3 + editY + textY, -15, editY), "", sizeStyle="regular")
		self.w.runButton = vanilla.Button((-80 - 15, spaceY * 4 + editY * 3, -15, -15), "Run", sizeStyle="regular", callback=self.RenameKerningGroupsMain)
		self.w.setDefaultButton(self.w.runButton)
		self.w.open()
		self.w.makeKey()

	def switchList(self, sender):
		try:
			if self.w.radio.get() == 0:
				self.w.popup.setItems(sorted(groupsL))
			else:
				self.w.popup.setItems(sorted(groupsR))
		except Exception as e:
			print("Rename Kerning Group Error (switchList): %s" % e)

	def RenameKerningGroupsMain(self, sender):
		try:
			newName = self.w.newName.get().strip()
			if not newName:
				raise ValueError("Please enter a new kerning group name.")
			popupNum = self.w.popup.get()

			if self.w.radio.get() == 0:
				popup = sorted(groupsL)[popupNum]
				for glyphName in groupsL[popup]:
					thisFont.glyphs[glyphName].leftKerningGroup = newName
				for master in thisFont.masters:
					for pair in newKernDic[master.id]:
						if pair[1] == "@MMK_R_" + popup:
							leftKey = apiKeyForKerningKey(pair[0])
							thisFont.setKerningForPair(master.id, leftKey, "@MMK_R_" + newName, pair[2])
							thisFont.removeKerningForPair(master.id, leftKey, "@MMK_R_" + popup)
				groupsL[newName] = groupsL.pop(popup)
				self.w.popup.setItems(sorted(groupsL))
				self.w.popup.set(sorted(groupsL).index(newName))
				for master in thisFont.masters:
					for pair in newKernDic[master.id]:
						if pair[1] == "@MMK_R_" + popup:
							pair[1] = "@MMK_R_" + newName

			else:
				popup = sorted(groupsR)[popupNum]
				for glyphName in groupsR[popup]:
					thisFont.glyphs[glyphName].rightKerningGroup = newName
				for master in thisFont.masters:
					for pair in newKernDic[master.id]:
						if pair[0] == "@MMK_L_" + popup:
							rightKey = apiKeyForKerningKey(pair[1])
							thisFont.setKerningForPair(master.id, "@MMK_L_" + newName, rightKey, pair[2])
							thisFont.removeKerningForPair(master.id, "@MMK_L_" + popup, rightKey)
				groupsR[newName] = groupsR.pop(popup)
				self.w.popup.setItems(sorted(groupsR))
				self.w.popup.set(sorted(groupsR).index(newName))
				for master in thisFont.masters:
					for pair in newKernDic[master.id]:
						if pair[0] == "@MMK_L_" + popup:
							pair[0] = "@MMK_L_" + newName

		except Exception as e:
			Glyphs.showMacroWindow()
			print("Rename Kerning Group Error (RenameKerningGroupsMain): %s" % e)


RenameKerningGroups()
