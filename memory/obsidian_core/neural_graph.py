from typing import List, Tuple, Dict
from glyph_core import GlyphMemoryNode

# === Neural-Symbolic Glyph Node ===
class NeuralGlyphNode:
    def __init__(self, id: int, symbol: str, meaning: str, activation: float = 1.0):
        self.id = id
        self.symbol = symbol
        self.meaning = meaning
        self.activation = activation
        self.edges: List[Tuple['NeuralGlyphNode', float]] = []

    def connect(self, other: 'NeuralGlyphNode', weight: float = 1.0):
        self.edges.append((other, weight))

    def propagate(self):
        for target_node, weight in self.edges:
            signal = self.activation * weight
            target_node.activation += signal

    def decay(self, factor: float = 0.9):
        self.activation *= factor

    def __repr__(self):
        return f"[{self.id}] {self.symbol} ({self.meaning}) → act: {self.activation:.3f}"

# === Convert Fractal Glyph Memory to Neural Graph ===
def glyph_memory_to_neural_graph(root: GlyphMemoryNode) -> Dict[int, NeuralGlyphNode]:
    node_map = {}
    node_counter = [0]

    def traverse(glyph_node: GlyphMemoryNode, parent_id: int = None):
        idx = node_counter[0]
        node = NeuralGlyphNode(
            id=idx,
            symbol=glyph_node.symbol,
            meaning=glyph_node.meaning,
            activation=1.0
        )
        node_map[idx] = node
        node_counter[0] += 1

        if parent_id is not None:
            parent_node = node_map[parent_id]
            parent_node.connect(node, weight=1.0)

        for child in glyph_node.children:
            traverse(child, idx)

    traverse(root)
    return node_map

# === Propagate Across Network ===
def propagate_network(graph: Dict[int, NeuralGlyphNode], decay: float = 0.9, cycles: int = 1):
    for _ in range(cycles):
        for node in graph.values():
            node.propagate()
        for node in graph.values():
            node.decay(decay)

# === Debug Print ===
def print_network_state(graph: Dict[int, NeuralGlyphNode]):
    for node in graph.values():
        print(node)
        for target_node, weight in node.edges:
            print(f"    ↳ connects to [{target_node.id}] with weight {weight}")

# === MAIN (Optional test harness) ===
if __name__ == "__main__":
    from obsidian_core import fractal_memory  # Ensure obsidian_core.py builds the fractal memory first

    graph = glyph_memory_to_neural_graph(fractal_memory)
    propagate_network(graph, decay=0.95, cycles=3)
    print("=== OBSIDIAN NEURAL GLYPH GRAPH ===")
    print_network_state(graph)

