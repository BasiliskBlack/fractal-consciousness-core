# Obsidian Core

A glyph-driven neural-symbolic AI engine based on SumeriBin and NeuroLingo.

## Features

- **Glyph Processing**: Interpret and process SumeriBin glyphs
- **Neural Integration**: Connect symbolic glyphs with neural networks
- **CLI Interface**: Interactive command-line interface for exploration
- **Extensible**: Plugin system for adding new functionality

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/obsidian_core.git
   cd obsidian_core
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Start the interactive CLI:
```bash
python obsidian_core.py
```

Available commands:
- `load <file>`: Load glyphs from a file
- `train [epochs]`: Train the model (default: 100 epochs)
- `generate [prompt]`: Generate output with optional prompt
- `mutate [0.0-1.0]`: Mutate the model with given intensity
- `help`: Show help message
- `exit`: Exit the program

## Example

```bash
# Load glyphs from a file
obsidian> load example.sumeri

# Train the model for 50 epochs
obsidian> train 50

# Generate output with a prompt
obsidian> generate "create a new sequence"
```

## Project Structure

- `obsidian_core.py`: Main CLI interface
- `mock_neurolingo_engine.py`: Mock implementation of the NeuroLingo engine
- `sumeribin_to_neurolingo.py`: Translator between SumeriBin and NeuroLingo formats
- `sumeribin.json`: Glyph definitions and mappings
- `example.sumeri`: Sample SumeriBin glyph sequence

## License

MIT License - See LICENSE for details.
