from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict
from sortedcontainers import SortedSet, SortedDict

class TrieNode:
    def __init__(self, value: Optional[str] = None):
        self.value = value
        self.children: SortedDict[str, 'TrieNode'] = SortedDict()

class SetSpace:
    def __init__(self):
        self.root = TrieNode()
    
    def add(self, elements: List[Any], value: Any):
        """Add a set and its associated value to the trie"""
        # Sort elements to ensure consistent insertion order and convert to strings
        sorted_elements = sorted(str(elem) for elem in elements)
        
        current = self.root
        # Add intermediate nodes
        for elem in sorted_elements:
            if elem not in current.children:
                current.children[elem] = TrieNode()
            current = current.children[elem]

        current.value = value
    
    def _find_best_match(self, node: TrieNode, elements: SortedSet, current_path: Set[str]) -> Optional[Tuple[Set[str], str]]:
        """Find the best matching set starting from the current node"""
        best_match = (current_path, node.value) if node.value is not None else None

        # Process children in order
        for elem, child in node.children.items():
            if elem in elements:
                # Try to find a longer match with remaining elements
                deeper_match = self._find_best_match(child, elements, current_path | {elem})

                if deeper_match and (not best_match or len(deeper_match[0]) > len(best_match[0])):
                    best_match = deeper_match
            
        return best_match
    
    def pretty_print(self, node: Optional[TrieNode] = None, prefix: str = "", is_last: bool = True, elem: str = "") -> None:
        """Pretty print the trie structure"""
        if node is None:
            node = self.root
            print("SetSpace Trie:")
        
        # Print current node
        connector = "└── " if is_last else "├── "
        value_str = f" -> {node.value}" if node.value is not None else ""
        print(f"{prefix}{connector}{elem}{value_str}")
        
        # Print children
        children = list(node.children.items())
        for i, (child_elem, child) in enumerate(children):
            is_last_child = i == len(children) - 1
            new_prefix = prefix + ("    " if is_last else "│   ")
            self.pretty_print(child, new_prefix, is_last_child, child_elem)

    def test(self):
             print("Hello World");

    def lookup(self, query: List[Any]) -> List[str]:
        """
        Find minimal sets that together cover all elements in the query.
        Returns list of (set, value) pairs.
        """
        if not query:
            return []
        
        elements = SortedSet(str(elem) for elem in query)
        result = []
        
        while elements:
            elem = elements.pop(0)
            try:
                match = self._find_best_match(self.root.children[elem], elements, set())
            except KeyError:
                return []

            print(f"Match {match}")
            print(f"Elements {elements}")

            if not match:
                return []
                
            match_set, match_value = match
            result.append(match_value)
            elements.difference_update(match_set)
            
        return result

def test_setspace():
    # Create test space
    space = SetSpace()
    
    # Add test sets
    space.add({'a', 'x'}, "ax_value")
    space.add({'a', 'x', 'y' , 'z'}, "axyz_value")
    space.add({'b'}, "b_value")
    space.add({'b', 'c'}, "bc_value")
    space.add({'a', 'b', 'c'}, "abc_value")

    # Print the trie structure
    print("\nTrie Structure:")
    space.pretty_print()

    # Test cases
    test_queries = [
        {'a', 'x'},      # Should find ax_value
        {'b'},           # Should find b_value
        {'a', 'b', 'c'}, # Should find abc_value
        {'a', 'b', 'x'}, # Should find ax_value
        {'a', 'b', 'c', 'x', 'y', 'z'}, # Should find ax_value
    ]
    
    for query in test_queries:
        print("\nQuery:", sorted(query))
        result = space.lookup(query)
        print("Result:")
        if result:
            print(f"{result}")
        else:
            print("No matching sets found")

if __name__ == "__main__":
    test_setspace()
