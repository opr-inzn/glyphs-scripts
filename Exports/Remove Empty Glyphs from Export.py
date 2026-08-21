# MenuTitle: Remove Empty Glyphs from Export
# -*- coding: utf-8 -*-
__doc__ = """
Adds a custom parameter to all instances to remove empty glyphs during
export. Excludes glyphs that are intentionally empty (space, separators,
CR, NULL) and glyphs already set to not export. Checks each master
individually and only removes glyphs from instances where they are empty
in ANY contributing master.
"""

# List of glyph names that should be empty
INTENTIONALLY_EMPTY = {
    "space",
    "uni00A0",  # no-break space
    "CR",
    "NULL",
    ".null",
    "nonmarkingreturn",
}


def is_layer_empty(layer):
    """Check if a specific layer is empty"""
    if layer is None:
        return True
    return (
        len(layer.paths) == 0
        and len(layer.components) == 0
        and len(layer.anchors) == 0
    )


def should_skip_glyph(glyph):
    """Check if glyph should be excluded from removal"""
    if glyph.name in INTENTIONALLY_EMPTY:
        return True
    if glyph.category == "Separator":
        return True
    if glyph.export == False:
        return True
    return False


def get_instance_master_ids(instance, font):
    """Get the master IDs that contribute to an instance"""
    master_ids = []
    
    # Check if instance has interpolation data
    if (
        hasattr(instance, "instanceInterpolations")
        and instance.instanceInterpolations is not None
    ):
        # Get masters involved in interpolation
        for master_id in instance.instanceInterpolations.keys():
            master_ids.append(master_id)
    
    if not master_ids:
        # Fallback: check all masters
        master_ids = [m.id for m in font.masters]
    
    return master_ids


def main():
    font = Glyphs.font
    if not font:
        print("No font open")
        Glyphs.showMacroWindow()
        return

    # Process each instance individually
    for instance in font.instances:
        print(f"\nProcessing instance: {instance.name}")
        
        # Get masters that contribute to this instance
        master_ids = get_instance_master_ids(instance, font)
        print(f"  Checking {len(master_ids)} master(s)")
        
        # Find glyphs to remove
        glyphs_to_remove = []
        
        for glyph in font.glyphs:
            # Skip glyphs that should remain
            if should_skip_glyph(glyph):
                continue
            
            # For interpolated instances: remove if empty in ANY master
            # For single master: remove if empty in that master
            is_empty_somewhere = False
            
            for master_id in master_ids:
                layer = glyph.layers[master_id]
                if is_layer_empty(layer):
                    is_empty_somewhere = True
                    break
            
            if is_empty_somewhere:
                glyphs_to_remove.append(glyph.name)
        
        # Update instance parameter
        if glyphs_to_remove:
            instance.customParameters["Remove Glyphs"] = sorted(
                glyphs_to_remove
            )
            print(f"  Will remove {len(glyphs_to_remove)} glyphs")
            # Show first few examples
            if len(glyphs_to_remove) <= 5:
                print(f"  → {', '.join(glyphs_to_remove)}")
            else:
                print(
                    f"  → {', '.join(glyphs_to_remove[:5])} ... and "
                    f"{len(glyphs_to_remove) - 5} more"
                )
        else:
            # Remove parameter if no glyphs to remove
            if "Remove Glyphs" in instance.customParameters:
                del instance.customParameters["Remove Glyphs"]
            print(f"  No glyphs to remove")

    print("\n✓ Done! Empty glyphs will be removed during export.")
    
    # Open Macro Panel to show output
    Glyphs.showMacroWindow()


main()