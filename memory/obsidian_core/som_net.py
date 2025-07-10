"""
Self-Organizing Map (SOM) Network for Obsidian Core
"""
import numpy as np
from typing import List, Tuple, Dict, Any
import random

def som_layer(som_input: List[List[Tuple[Tuple[int, int], Tuple[int, int]]]]) -> List[List[Dict[str, Any]]]:
    """
    Process the input through a Self-Organizing Map layer.
    
    Args:
        som_input: Input matrix of coordinate tuples
        
    Returns:
        Processed SOM layer with glyph information and symbolic meanings
    """
    # Sumerian cuneiform glyphs for our symbolic system
    GLYPHS = [
        ("𒀸", "AN", "Heaven/Source"),
        ("𒁁", "A", "Water/Beginning"),
        ("𒁉", "IM", "Storm/Breath"),
        ("𒁹", "BI", "Two/Divide"),
        ("𒁺", "BA", "House/Gate"),
        ("𒁻", "ZA", "Spirit/Flow"),
        ("𒁿", "GI", "Tree/Growth"),
        ("𒃻", "DU", "Walk/Build"),
        ("𒄀", "KU", "Fix/Anchor"),
        ("𒄁", "DIB", "Cross/Escape"),
        ("𒅆", "E", "Temple/Order"),
        ("𒌵", "P", "Speak/Release"),
        ("𒇻", "ZI", "Soul/Life"),
        ("𒌨", "DA", "Fire/Drive"),
        ("𒉌", "SA", "Cut/Divide"),
        ("𒊺", "EN", "Lord/Override")
    ]
    
    # Core symbolic meanings for the matrix
    SYMBOLIC_MEANINGS = ["Fall", "Union", "Creation", "Self"]
    
    result = []
    
    for i, row in enumerate(som_input):
        processed_row = []
        for j, ((x, y), (a, b)) in enumerate(row):
            # Calculate some basic features
            magnitude = (x**2 + y**2 + a**2 + b**2) ** 0.5
            angle = np.arctan2(y, x) if x != 0 else 0
            
            # Select a glyph based on position and value
            glyph_idx = (i * len(som_input[0]) + j) % len(GLYPHS)
            glyph, name, glyph_meaning = GLYPHS[glyph_idx]
            
            # Create symbolic interpretations
            horizontal_meaning = SYMBOLIC_MEANINGS[(x + y) % len(SYMBOLIC_MEANINGS)]
            vertical_meaning = SYMBOLIC_MEANINGS[(a + b) % len(SYMBOLIC_MEANINGS)]
            diag1_meaning = SYMBOLIC_MEANINGS[(x + a) % len(SYMBOLIC_MEANINGS)]
            diag2_meaning = SYMBOLIC_MEANINGS[(y + b) % len(SYMBOLIC_MEANINGS)]
            
            # Create the cell structure
            cell = {
                "glyph": glyph,
                "name": name,
                "position": (i, j),
                "values": {"x": x, "y": y, "a": a, "b": b},
                "features": {"magnitude": magnitude, "angle": angle},
                "summary": f"{glyph_meaning} ({name})",
                "horizontal": {
                    "values": (x, y),
                    "meanings": [horizontal_meaning, f"{name} in X-Y"]
                },
                "vertical": {
                    "values": (a, b),
                    "meanings": [vertical_meaning, f"{name} in A-B"]
                },
                "diagonal": {
                    "↘": {"value": (x, b), "meaning": diag1_meaning},
                    "↙": {"value": (y, a), "meaning": diag2_meaning}
                }
            }
            processed_row.append(cell)
        result.append(processed_row)
    
    return result
