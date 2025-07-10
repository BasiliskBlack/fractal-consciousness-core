#!/bin/bash
# Simple shell script to enter SumeriBin glyph mode
echo "Entering SumeriBin glyph shell mode. Type glyphs to interpret."
while true; do
    read -p "𒀸𒁻𒇻𒊺> " input
    python3 -c "import sumeribin; sumeribin.interpret_sumeribin('$input')"
done
