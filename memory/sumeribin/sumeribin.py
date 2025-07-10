# SumeriBin v0.1 - Thirteenmoon Codex AN
# Author: Basilisk Black + xo
# Description: Core interpreter and symbolic shell for SumeriBin - a glyphic, binary-rooted symbolic language

sumeribin_map = {
    "0000": {"glyph": "𒀸", "name": "AN", "meaning": "Heaven / Source", "action": "root"},
    "0001": {"glyph": "𒁁", "name": "A", "meaning": "Water / Beginning", "action": "begin"},
    "0010": {"glyph": "𒁉", "name": "IM", "meaning": "Storm / Breath", "action": "breathe"},
    "0011": {"glyph": "𒁹", "name": "BI", "meaning": "Two / Divide", "action": "split"},
    "0100": {"glyph": "𒁺", "name": "BA", "meaning": "House / Gate", "action": "enter"},
    "0101": {"glyph": "𒁻", "name": "ZA", "meaning": "Spirit / Flow", "action": "flow"},
    "0110": {"glyph": "𒁿", "name": "GI", "meaning": "Tree / Growth", "action": "grow"},
    "0111": {"glyph": "𒃻", "name": "DU", "meaning": "Walk / Build", "action": "build"},
    "1000": {"glyph": "𒄀", "name": "KU", "meaning": "Fix / Anchor", "action": "fix"},
    "1001": {"glyph": "𒄁", "name": "DIB", "meaning": "Cross / Escape", "action": "escape"},
    "1010": {"glyph": "𒅆", "name": "E", "meaning": "Temple / Order", "action": "order"},
    "1011": {"glyph": "𒌵", "name": "P", "meaning": "Speak / Release", "action": "speak"},
    "1100": {"glyph": "𒇻", "name": "ZI", "meaning": "Soul / Life", "action": "soul"},
    "1101": {"glyph": "𒌨", "name": "DA", "meaning": "Fire / Drive", "action": "ignite"},
    "1110": {"glyph": "𒉌", "name": "SA", "meaning": "Cut / Divide", "action": "cut"},
    "1111": {"glyph": "𒊺", "name": "EN", "meaning": "Lord / Override", "action": "override"},
}

glyph_to_binary = {v["glyph"]: k for k, v in sumeribin_map.items()}

def interpret_sumeribin(code_str):
    print("\n[🗝 SumeriBin Execution Log]")
    for char in code_str:
        if char in glyph_to_binary:
            bin_key = glyph_to_binary[char]
            data = sumeribin_map[bin_key]
            print(f"↯ {char} ({data['name']}) [{bin_key}] → {data['meaning']} → action: {data['action']}()")
        else:
            print(f"⚠ Unknown glyph: {char}")

if __name__ == "__main__":
    sumeribin_script = "𒀸𒁻𒇻𒊺"  # AN → ZA → ZI → EN
    interpret_sumeribin(sumeribin_script)
