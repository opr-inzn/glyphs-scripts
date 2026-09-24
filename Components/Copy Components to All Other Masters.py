# MenuTitle: Copy Components to All Other Masters
# -*- coding: utf-8 -*-
"""Copy selected glyphs’ component setup from one master to all other masters.

Replaces target master-layer shapes and hints with copies of source components.
Component order, transforms, alignment and smart-component settings are copied.
References resolve in each target master. Target anchors and metric keys stay.
Automatic alignment handles spacing; manually positioned layers retain their
existing target width. Source layers containing paths are skipped. Special
layers and backgrounds are not changed.
"""

import traceback
from GlyphsApp import Glyphs, Message
from vanilla import Window, TextBox, PopUpButton, Button

TITLE = "Copy Components to All Other Masters"


def selected_glyphs(font):
    glyphs, seen = [], set()
    for layer in font.selectedLayers:
        glyph = layer.parent
        if glyph is not None and glyph.name not in seen:
            seen.add(glyph.name)
            glyphs.append(glyph)
    return glyphs


def make_plan(font, glyphs, source_id):
    plan, skipped = [], []
    for glyph in glyphs:
        source = glyph.layers[source_id]
        if source is None or not len(source.components):
            skipped.append("%s: no source components" % glyph.name)
            continue
        if len(source.shapes) != len(source.components):
            skipped.append("%s: source also contains paths or other shapes" % glyph.name)
            continue
        for master in font.masters:
            if master.id == source_id:
                continue
            target = glyph.layers[master.id]
            if target is None:
                skipped.append("%s, %s: missing target layer" % (glyph.name, master.name))
                continue
            components = [component.copy() for component in source.components]
            for component in components:
                base = font.glyphs[component.componentName]
                if base is None or base.layers[master.id] is None:
                    raise ValueError("%s, %s: missing component layer for %s." %
                                     (glyph.name, master.name, component.componentName))
            plan.append((glyph, target, master, components))

    # Check the proposed graph in each target master before changing any layer.
    for master in font.masters:
        entries = [entry for entry in plan if entry[2].id == master.id]
        if not entries:
            continue
        graph = {}
        for glyph in font.glyphs:
            layer = glyph.layers[master.id]
            graph[glyph.name] = [c.componentName for c in layer.components] if layer is not None else []
        for glyph, _, _, components in entries:
            graph[glyph.name] = [c.componentName for c in components]
        done, visiting = set(), set()
        def visit(name):
            if name in visiting:
                raise ValueError("Component cycle involving %s in %s. Nothing was copied." % (name, master.name))
            if name in done:
                return
            visiting.add(name)
            for child in graph.get(name, []):
                visit(child)
            visiting.remove(name)
            done.add(name)
        for glyph, _, _, _ in entries:
            visit(glyph.name)
    return plan, skipped


def restore(layer, backup):
    original = backup.copy()
    layer.hints = []
    layer.shapes = list(original.shapes)
    layer.hints = list(original.hints)
    layer.width = original.width


def apply_plan(font, plan):
    backups = [(layer, layer.copy()) for _, layer, _, _ in plan]
    begun, seen = [], set()
    font.disableUpdateInterface()
    try:
        for glyph, layer, master, components in plan:
            if glyph.name not in seen:
                glyph.beginUndo()
                begun.append(glyph)
                seen.add(glyph.name)
            width = layer.width
            settings = [(c.automaticAlignment, c.alignment, tuple(c.transform)) for c in components]
            layer.hints = []
            layer.shapes = components
            # Attachment can change alignment state; restore the copied settings.
            for component, (automatic, alignment, transform) in zip(layer.components, settings):
                component.automaticAlignment = automatic
                component.alignment = alignment
                component.transform = transform
            layer.width = width
            layer.alignComponents()
    except Exception:
        for layer, backup in backups:
            restore(layer, backup)
        raise
    finally:
        try:
            for glyph in reversed(begun):
                glyph.endUndo()
        finally:
            font.enableUpdateInterface()


class CopyComponentsToAllMasters:
    def __init__(self):
        self.font = Glyphs.font
        if self.font is None:
            Message(TITLE, "Open a font first.")
            return
        self.masters = list(self.font.masters)
        if len(self.masters) < 2:
            Message(TITLE, "This script needs at least two masters.")
            return
        self.w = Window((430, 185), TITLE)
        self.w.sourceLabel = TextBox((15, 19, 95, 20), "Copy from:")
        self.w.source = PopUpButton((115, 15, -15, 24), [m.name for m in self.masters])
        self.w.source.set(next((i for i, m in enumerate(self.masters)
                               if m.id == (self.font.selectedLayers[0].master if self.font.selectedLayers else self.font.selectedFontMaster).id), 0))
        self.w.note = TextBox((15, 55, -15, 75),
            "Copies the selected glyphs’ components to every other master.\n"
            "Replaces target shapes and hints; keeps anchors and metric keys.\n"
            "Source layers with paths are skipped. Special layers stay unchanged.", sizeStyle="small")
        self.w.cancel = Button((15, 146, 85, 24), "Cancel", callback=lambda sender: self.w.close())
        self.w.apply = Button((-205, 146, 190, 24), "Copy to other masters", callback=self.apply)
        self.w.setDefaultButton(self.w.apply)
        self.w.open()
        self.w.makeKey()

    def apply(self, sender):
        try:
            if Glyphs.font != self.font:
                raise ValueError("Return to the font this window was opened for.")
            glyphs = selected_glyphs(self.font)
            if not glyphs:
                raise ValueError("Select the glyphs whose components you want to copy.")
            master = self.masters[self.w.source.get()]
            plan, skipped = make_plan(self.font, glyphs, master.id)
            for entry in skipped:
                print("Skipped " + entry)
            if not plan:
                raise ValueError("No component-only source layers to copy. Details are in the Macro Panel.")
            apply_plan(self.font, plan)
            for glyph, _, target, components in plan:
                print("%s: %s → %s (%d components)" % (glyph.name, master.name, target.name, len(components)))
            result = "Copied %d glyphs into %d master layers." % (len({g.name for g, _, _, _ in plan}), len(plan))
            if skipped:
                result += " Skipped %d; see Macro Panel." % len(skipped)
            Glyphs.redraw()
            Glyphs.showNotification(TITLE, result)
            self.w.close()
        except ValueError as error:
            Message(TITLE, str(error))
        except Exception:
            Glyphs.showMacroWindow()
            print(traceback.format_exc())
            Message(TITLE, "Copy failed. Original target layers were restored. See Macro Panel.")


if __name__ == "__main__":
    copyComponentsToAllMastersWindow = CopyComponentsToAllMasters()
