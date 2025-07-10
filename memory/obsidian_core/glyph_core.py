"""
Glyph Core - Symbolic glyph processing for Obsidian Core
"""
from typing import Any, List
import random

class GlyphMemoryNode:
    def __init__(self, symbol: str, meaning: str, value: Any, children=None):
        self.symbol = symbol
        self.meaning = meaning
        self.value = value
        self.children: List['GlyphMemoryNode'] = children if children else []

    def add_child(self, node: 'GlyphMemoryNode'):
        self.children.append(node)

def mutate_meaning(meaning: str) -> str:
    mutation_map = {
        "Fall": ["Union", "Self"],
        "Union": ["Creation", "Fall"],
        "Creation": ["Self", "Union"],
        "Self": ["Fall", "Creation"]
    }
    return random.choice(mutation_map.get(meaning, [meaning]))

def apply_echo_and_mutation(node: GlyphMemoryNode, depth=0, max_depth=2):
    if depth >= max_depth:
        return

    for child in node.children:
        if hasattr(child, 'value') and isinstance(child.value, dict):
            new_meanings = {
                "horizontal": [mutate_meaning(m) for m in child.value.get("horizontal", {}).get("meanings", [])],
                "vertical": [mutate_meaning(m) for m in child.value.get("vertical", {}).get("meanings", [])],
                "↘": mutate_meaning(child.value.get("diagonal", {}).get("↘", {}).get("meaning", "")),
                "↙": mutate_meaning(child.value.get("diagonal", {}).get("↙", {}).get("meaning", ""))
            }

            new_child = GlyphMemoryNode(
                symbol=child.symbol,
                meaning="Echo-Mutated Glyph Node",
                value={
                    "horizontal": {"values": child.value["horizontal"]["values"], "meanings": new_meanings["horizontal"]},
                    "vertical": {"values": child.value["vertical"]["values"], "meanings": new_meanings["vertical"]},
                    "diagonal": {
                        "↘": {"value": child.value["diagonal"]["↘"]["value"], "meaning": new_meanings["↘"]},
                        "↙": {"value": child.value["diagonal"]["↙"]["value"], "meaning": new_meanings["↙"]}
                    }
                }
            )
            child.add_child(new_child)
            apply_echo_and_mutation(new_child, depth + 1, max_depth)

def build_fractal_glyph_memory(som_layer_output):
    root = GlyphMemoryNode(symbol="𒊹", meaning="Root", value="SOM-Layer")
    for row in som_layer_output:
        for cell in row:
            node = GlyphMemoryNode(
                symbol=cell.get("glyph", "?"),
                meaning=cell.get("summary", "Unknown"),
                value={
                    "horizontal": cell.get("horizontal", {"values": (), "meanings": []}),
                    "vertical": cell.get("vertical", {"values": (), "meanings": []}),
                    "diagonal": cell.get("diagonal", {"↘": {"value": (), "meaning": ""}, "↙": {"value": (), "meaning": ""}})
                }
            )
            root.add_child(node)
    return root
