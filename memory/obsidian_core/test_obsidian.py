#!/usr/bin/env python3
# Test script for Obsidian Core

import unittest
from obsidian_core import ObsidianCore
from sumeribin_to_neurolingo import SumeriBinTranslator

class TestObsidianCore(unittest.TestCase):
    def setUp(self):
        self.core = ObsidianCore()
        self.translator = SumeriBinTranslator()
    
    def test_glyph_loading(self):
        """Test loading glyphs from a file."""
        result = self.core.load_glyphs('example.sumeri')
        self.assertTrue(result)
    
    def test_translation(self):
        """Test SumeriBin to binary translation."""
        test_glyphs = "𒀸𒁁"  # AN A
        binary = self.translator.glyphs_to_binary(test_glyphs)
        self.assertIn(" ", binary)  # Should contain a space between binary codes
    
    def test_neurolingo_init(self):
        """Test NeuroLingo engine initialization."""
        self.assertIsNotNone(self.core.neural_engine)

if __name__ == "__main__":
    unittest.main()
