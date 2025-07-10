#!/usr/bin/env python3
# Enhanced Demonstration Script for Obsidian Core

import time
from pathlib import Path
from obsidian_core import ObsidianCore
from sumeribin_to_neurolingo import SumeriBinTranslator

def print_section(title: str, width: int = 50) -> None:
    """Print a section header."""
    print(f"\n{'=' * width}")
    print(f"{title:^{width}}")
    print(f"{'=' * width}")

def load_glyph_file(filepath: str) -> str:
    """Load glyphs from a file, ignoring comments and empty lines."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return ''.join([line[0] for line in f if line.strip() and not line.startswith('#')])

def main():
    print("\n" + "="*60)
    print("OBSIDIAN CORE - GLYPHIC NEURAL ENGINE DEMO".center(60))
    print("="*60)
    
    # Initialize components
    print("\nInitializing components...")
    start_time = time.time()
    core = ObsidianCore()
    translator = SumeriBinTranslator()
    
    # Load and display example glyphs
    print_section("1. GLYPH PROCESSING")
    try:
        glyphs = load_glyph_file('example.sumeri')
        print(f"Loaded {len(glyphs)} glyphs from example.sumeri")
        
        # Show glyph details
        print("\nSample glyphs with meanings:")
        for i, glyph in enumerate(glyphs[:5], 1):  # Show first 5 glyphs
            binary = translator.glyphs_to_binary(glyph).strip()
            print(f"  {i}. {glyph} (Binary: {binary})")
    except Exception as e:
        print(f"Error loading glyphs: {e}")
        return
    
    # Neural Network Training
    print_section("2. NEURAL NETWORK TRAINING")
    try:
        print("Training the model with 100 epochs (this will take a few minutes)...")
        training_start = time.time()
        
        # Train in chunks to show progress
        total_epochs = 100
        chunk_size = 20
        
        for chunk in range(total_epochs // chunk_size):
            chunk_start = time.time()
            core.train_model(epochs=chunk_size)
            chunk_time = time.time() - chunk_start
            epochs_done = (chunk + 1) * chunk_size
            print(f"Completed {epochs_done}/{total_epochs} epochs (took {chunk_time:.1f}s)")
            
            # Show sample generation after each chunk
            sample = core.neural_engine.generate(prompt=glyphs[0], max_length=10)
            print(f"Sample after {epochs_done} epochs: {sample}\n")
        
        training_time = time.time() - training_start
        print(f"\nTraining completed in {training_time/60:.1f} minutes")
    except Exception as e:
        print(f"Error during training: {e}")
        return
    
    # Text Generation
    print_section("3. GLYPH GENERATION")
    try:
        print("Generating glyph sequences...\n")
        
        # Generate with different temperatures
        for temp in [0.7, 1.0, 1.3]:
            print(f"Temperature {temp}:")
            for _ in range(3):  # Generate 3 samples per temperature
                output = core.neural_engine.generate(prompt=glyphs[0], temperature=temp, max_length=15)
                print(f"  • {output}")
            print()  # Add space between temperature groups
    except Exception as e:
        print(f"Error during generation: {e}")
    
    # Model Mutation
    print_section("4. MODEL MUTATION")
    try:
        print("Applying model mutation...")
        mutation_result = core.neural_engine.mutate(intensity=0.15)
        print(f"Mutation result: {mutation_result.get('message', 'Unknown')}")
        
        # Generate after mutation
        print("\nGeneration after mutation:")
        output = core.neural_engine.generate(prompt=glyphs[0], max_length=20)
        print(f"  {output}")
    except Exception as e:
        print(f"Error during mutation: {e}")
    
    # Save the model
    print_section("5. MODEL PERSISTENCE")
    try:
        model_path = "trained_model.pt"
        if core.neural_engine.save(model_path):
            print(f"Model saved to {model_path} ({(Path(model_path).stat().st_size / 1024):.1f} KB)")
        else:
            print("Failed to save model")
    except Exception as e:
        print(f"Error saving model: {e}")
    
    total_time = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"DEMO COMPLETED IN {total_time:.1f} SECONDS".center(60))
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
