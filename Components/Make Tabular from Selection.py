# MenuTitle: Make Tabular from Selection
# -*- coding: utf-8 -*-
"""Create .tf alternates containing the selected base glyph as a component.

Inspired by Toshi Omagari’s “Make .case alternates from selected glyphs”.
Creates one component in every master, retaining the source position and width.
Automatic alignment is disabled so the new glyphs can be spaced independently.
Existing .tf glyphs and selections already containing a .tf suffix are skipped.
This creates the alternates; it does not assign a common tabular width.
"""

import traceback

from GlyphsApp import Glyphs, GSGlyph, GSComponent, Message


TITLE = "Make Tabular from Selection"


def main():
    font = Glyphs.font
    if font is None:
        Message(TITLE, "Open a font first.")
        return

    sources, seen = [], set()
    for layer in font.selectedLayers or []:
        glyph = layer.parent
        if glyph is not None and glyph.name not in seen:
            seen.add(glyph.name)
            sources.append(glyph)
    if not sources:
        Message(TITLE, "Select the glyphs to make .tf alternates from.")
        return

    created, skipped = [], []
    font.disableUpdateInterface()
    try:
        for source in sources:
            if "tf" in source.name.split(".")[1:]:
                skipped.append("%s: already has a .tf suffix" % source.name)
                continue
            name = source.name + ".tf"
            if font.glyphs[name] is not None:
                skipped.append("%s: already exists" % name)
                continue
            if any(source.layers[master.id] is None for master in font.masters):
                skipped.append("%s: missing a source master layer" % source.name)
                continue

            target = GSGlyph(name, autoName=False)
            target.export = source.export
            font.glyphs.append(target)
            try:
                for master in font.masters:
                    layer = target.layers[master.id]
                    component = GSComponent(source.name)
                    component.automaticAlignment = False
                    layer.components.append(component)
                    layer.width = source.layers[master.id].width
            except Exception:
                # Remove an incomplete new glyph if building a master fails.
                del font.glyphs[name]
                raise
            created.append(name)
            print("Created %s from %s in all masters." % (name, source.name))
    finally:
        font.enableUpdateInterface()

    for reason in skipped:
        print("Skipped %s." % reason)
    Glyphs.showNotification(
        TITLE,
        "Created %d .tf glyph(s). Skipped %d. Details in the Macro Panel."
        % (len(created), len(skipped)),
    )


try:
    main()
except Exception:
    Glyphs.showMacroWindow()
    traceback.print_exc()
    Message(TITLE, "Could not finish creating .tf glyphs. See the Macro Panel for details.")
