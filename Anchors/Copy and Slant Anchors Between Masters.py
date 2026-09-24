# MenuTitle: Copy and Slant Anchors Between Masters
# -*- coding: utf-8 -*-
"""Copy all anchors of selected glyphs from an upright to another master.

Slant uses the target master’s Italic Angle and half its x-height:
x_new = x_source + tan(angle) * (y_source - xHeight / 2).
Y positions are copied unchanged. Existing same-name anchors are updated;
missing anchors are added. Other target anchors and outlines are preserved.
Only the two chosen master layers are involved, not special layers.
"""

import math
import traceback
from AppKit import NSPoint
from GlyphsApp import Glyphs, Message
from vanilla import Window, TextBox, PopUpButton, Button

TITLE = "Copy and Slant Anchors"


def slant_parameters(master):
    angle = float(master.italicAngle)
    height = float(master.xHeight)
    if not math.isfinite(angle) or abs(angle) >= 90:
        raise ValueError("The target master needs an italic angle between −90° and 90°.")
    if not math.isfinite(height) or height <= 0:
        raise ValueError("Set a positive x-height in the target master’s metrics first.")
    return math.tan(math.radians(angle)), height / 2.0


def slanted_position(position, slope, pivot):
    return NSPoint(position.x + slope * (position.y - pivot), position.y)


def selected_glyphs(font):
    result, seen = [], set()
    for layer in font.selectedLayers:
        glyph = layer.parent
        if glyph is not None and glyph.name not in seen:
            seen.add(glyph.name)
            result.append(glyph)
    return result


def copy_anchors(font, glyphs, source, target):
    if source.id == target.id:
        raise ValueError("Choose two different masters.")
    if abs(float(source.italicAngle)) > 0.001:
        raise ValueError("Choose an upright source master with an italic angle of 0°.")
    slope, pivot = slant_parameters(target)
    plan, skipped = [], []
    for glyph in glyphs:
        source_layer = glyph.layers[source.id]
        target_layer = glyph.layers[target.id]
        if source_layer is None or target_layer is None:
            skipped.append("%s: missing master layer" % glyph.name)
            continue
        if not len(source_layer.anchors):
            skipped.append("%s: no source anchors" % glyph.name)
            continue
        anchors = []
        for anchor in source_layer.anchors:
            copied = anchor.copy()
            copied.position = slanted_position(anchor.position, slope, pivot)
            anchors.append(copied)
        plan.append((glyph, target_layer, anchors))

    backups = [(layer, [a.copy() for a in layer.anchors]) for _, layer, _ in plan]
    begun = []
    font.disableUpdateInterface()
    try:
        for glyph, layer, anchors in plan:
            glyph.beginUndo()
            begun.append(glyph)
            for anchor in anchors:
                existing = layer.anchorForName_(anchor.name)
                if existing is None:
                    layer.addAnchor_(anchor)
                else:
                    existing.setPosition_(anchor.position)
    except Exception:
        for layer, anchors in backups:
            layer.anchors = anchors
        raise
    finally:
        try:
            for glyph in reversed(begun):
                glyph.endUndo()
        finally:
            font.enableUpdateInterface()
    return sum(len(anchors) for _, _, anchors in plan), len(plan), skipped


class CopyAndSlantAnchors:
    def __init__(self):
        self.font = Glyphs.font
        if self.font is None:
            Message(TITLE, "Open a font first.")
            return
        self.masters = list(self.font.masters)
        if len(self.masters) < 2:
            Message(TITLE, "This script needs at least two masters in the same font.")
            return
        current = next((i for i, m in enumerate(self.masters)
                        if m.id == (self.font.selectedLayers[0].master if self.font.selectedLayers else self.font.selectedFontMaster).id), 0)
        source = next((i for i, m in enumerate(self.masters) if abs(m.italicAngle) < 0.001), 0)
        target = current if current != source else next(
            (i for i, m in enumerate(self.masters) if i != source and abs(m.italicAngle) > 0.001),
            next(i for i in range(len(self.masters)) if i != source))
        self.w = Window((420, 224), TITLE)
        names = [m.name for m in self.masters]
        self.w.sourceLabel = TextBox((15, 18, 105, 20), "From upright:")
        self.w.source = PopUpButton((125, 15, -15, 24), names)
        self.w.source.set(source)
        self.w.targetLabel = TextBox((15, 54, 105, 20), "To italic:")
        self.w.target = PopUpButton((125, 51, -15, 24), names, callback=self.metrics_changed)
        self.w.target.set(target)
        self.w.metrics = TextBox((15, 91, -15, 30), "", sizeStyle="small")
        self.w.note = TextBox((15, 126, -15, 42),
            "Copies all anchors for the selected glyphs. Matching names are\n"
            "updated; missing anchors are added. Y positions stay unchanged.", sizeStyle="small")
        self.w.cancel = Button((15, 185, 90, 24), "Cancel", callback=lambda sender: self.w.close())
        self.w.apply = Button((-165, 185, 150, 24), "Copy anchors", callback=self.apply)
        self.w.setDefaultButton(self.w.apply)
        self.metrics_changed(None)
        self.w.open()
        self.w.makeKey()

    def metrics_changed(self, sender):
        master = self.masters[self.w.target.get()]
        try:
            _, pivot = slant_parameters(master)
            self.w.metrics.set("Italic angle: %g°     Slant origin: ½ x-height = %g" %
                               (master.italicAngle, pivot))
        except ValueError as error:
            self.w.metrics.set(str(error))

    def apply(self, sender):
        try:
            if Glyphs.font != self.font:
                raise ValueError("Return to the font this window was opened for.")
            glyphs = selected_glyphs(self.font)
            if not glyphs:
                raise ValueError("Select the glyphs whose anchors you want to copy.")
            source = self.masters[self.w.source.get()]
            target = self.masters[self.w.target.get()]
            count, glyph_count, skipped = copy_anchors(self.font, glyphs, source, target)
            for entry in skipped:
                print("Skipped " + entry)
            result = "Copied %d anchors in %d glyphs." % (count, glyph_count)
            if skipped:
                result += " Skipped %d glyphs; see Macro Panel." % len(skipped)
            print("%s → %s: %s" % (source.name, target.name, result))
            Glyphs.redraw()
            Glyphs.showNotification(TITLE, result)
            self.w.close()
        except ValueError as error:
            Message(TITLE, str(error))
        except Exception:
            Glyphs.showMacroWindow()
            print(traceback.format_exc())
            Message(TITLE, "Copy failed. Original target anchors were restored. See Macro Panel.")


if __name__ == "__main__":
    copyAndSlantAnchorsWindow = CopyAndSlantAnchors()
