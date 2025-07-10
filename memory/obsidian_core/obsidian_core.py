"""
Obsidian Core - Symbolic Glyph Neural Network Framework
"""

from glyph_core import apply_echo_and_mutation, build_fractal_glyph_memory
from som_net import som_layer

class ObsidianCore:
    def __init__(self):
        """Initialize the Obsidian Core engine."""
        self.memory_root = None
        self.current_depth = 0
        self.max_depth = 3
        
    def generate_sample_som_layer(self):
        """Generate a sample SOM layer for demonstration."""
        # This creates a 2x2 matrix of coordinate tuples
        return [
            [((2, 3), (3, 5)), ((1, 4), (4, 2))],
            [((5, 6), (6, 3)), ((0, 7), (7, 0))]
        ]
        
    def process_som_layer(self, som_layer_input=None):
        """Process input through the SOM layer and build glyph memory."""
        if som_layer_input is None:
            print("Using sample SOM layer input...")
            som_layer_input = self.generate_sample_som_layer()
            
        print("\nProcessing SOM layer...")
        processed_layer = som_layer(som_layer_input)
        
        print("\nBuilding fractal glyph memory...")
        self.memory_root = build_fractal_glyph_memory(processed_layer)
        
        print("\nApplying echo and mutation...")
        apply_echo_and_mutation(self.memory_root, max_depth=self.max_depth)
        
        return self.memory_root
        
    def print_glyph_tree(self, node=None, depth=0):
        """Print the glyph memory tree structure."""
        if node is None:
            if self.memory_root is None:
                print("No glyph memory available. Process SOM layer first.")
                return
            node = self.memory_root
            
        # Print current node
        indent = "  " * depth
        print(f"{indent}└─ {node.symbol} - {node.meaning}")
        
        # Print children
        for child in node.children:
            self.print_glyph_tree(child, depth + 1)
            
    def run(self):
        """Run the Obsidian Core interactive session."""
        print("=== OBSIDIAN CORE: SYMBOLIC NEURAL ENGINE ===")
        print("Processing sample data...\n")
        
        # Process sample data
        self.process_som_layer()
        
        # Display results
        print("\n=== GLYPH MEMORY TREE ===")
        self.print_glyph_tree()
        
        print("\nObsidian Core session complete.")

def main():
    """Main entry point for the Obsidian Core."""
    core = ObsidianCore()
    core.run()

if __name__ == "__main__":
    main()