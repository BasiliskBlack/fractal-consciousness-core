#!/usr/bin/env python3
# SumeriBin to NeuroLingo Translator
# Part of Obsidian Core

import json
from typing import Dict

class SumeriBinTranslator:
    """Translates between SumeriBin glyphs and NeuroLingo format."""
    
    def __init__(self, glyph_map_path: str = 'sumeribin.json'):
        """Initialize the translator with a glyph map."""
        self.glyph_map = self._load_glyph_map(glyph_map_path)
        self.glyph_to_bin = {v['glyph']: k for k, v in self.glyph_map.items()}
    
    def _load_glyph_map(self, path: str) -> Dict:
        """Load the SumeriBin glyph mapping."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Glyph map not found at {path}")
            return {}
    
    def glyphs_to_binary(self, glyphs: str) -> str:
        """Convert a sequence of SumeriBin glyphs to binary."""
        return ' '.join(self.glyph_to_bin.get(g, '') for g in glyphs)
    
    def binary_to_glyphs(self, binary_str: str) -> str:
        """Convert a binary string to SumeriBin glyphs."""
        binary_list = binary_str.split()
        return ''.join(self.glyph_map.get(b, {}).get('glyph', '') for b in binary_list)
    
    def translate_to_neurolingo(self, glyphs: str) -> Dict:
        """Translate SumeriBin glyphs to NeuroLingo format."""
        binary_seq = self.glyphs_to_binary(glyphs)
        return {
            'input': glyphs,
            'binary_sequence': binary_seq,
            'tokens': [self.glyph_map.get(b, {}) for b in binary_seq.split()],
            'length': len(glyphs)
        }

def main():
    # Example usage
    translator = SumeriBinTranslator()
    
    # Example SumeriBin glyphs
    test_glyphs = "𒀸𒁁𒁉"  # Example glyphs
    
    print(f"Original glyphs: {test_glyphs}")
    
    # Convert to binary
    binary = translator.glyphs_to_binary(test_glyphs)
    print(f"Binary: {binary}")
    
    # Convert back to glyphs
    back_to_glyphs = translator.binary_to_glyphs(binary)
    print(f"Back to glyphs: {back_to_glyphs}")
    
    # Full translation to NeuroLingo format
    translation = translator.translate_to_neurolingo(test_glyphs)
    print("\nNeuroLingo translation:")
    print(json.dumps(translation, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()