from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from sortedcontainers import SortedSet, SortedDict
from hyperon import Atom, SymbolAtom, ExpressionAtom, MeTTa, OperationAtom, E, S
import uuid
from hyperon.ext import register_atoms

class TrieNode:
    def __init__(self, value: Optional[Atom] = None):
        self.value = value
        self.children: SortedDict[str, 'TrieNode'] = SortedDict()

class SetSpace:
    def __init__(self):
        self.root = TrieNode()
    
    def add(self, expr: ExpressionAtom, value: Atom) -> Optional[Atom]:
        """Add a set and its associated value to the trie
        Returns the old value if one existed, None otherwise"""
        # Get elements from expression and sort them
        elements = expr.get_children()
        sorted_elements = sorted(str(elem) for elem in elements)
        
        current = self.root
        # Add intermediate nodes
        for elem in sorted_elements:
            if elem not in current.children:
                current.children[elem] = TrieNode()
            current = current.children[elem]

        old_value = current.value
        current.value = value
        return old_value
    
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

    def get_all_elements(self) -> List[ExpressionAtom]:
        """Get all unique element combinations that cover all elements with preference for longer paths"""
        def collect_paths(node: TrieNode, current_path: Set[str]) -> List[Tuple[Set[str], Atom]]:
            results = []
            if node.value is not None:
                results.append((current_path.copy(), node.value))
            
            for elem, child in node.children.items():
                current_path.add(elem)
                results.extend(collect_paths(child, current_path))
                current_path.remove(elem)
            return results
        
        # Get all paths and their values
        all_paths = collect_paths(self.root, set())
        if not all_paths:
            return []
            
        # Sort by path length (descending)
        all_paths.sort(key=lambda x: len(x[0]), reverse=True)
        
        # Collect values that cover all elements
        covered = set()
        result_values = []
        
        for path_set, value in all_paths:
            if not path_set.issubset(covered):
                result_values.append(value)
                covered.update(path_set)
                
        return [E(*result_values)]

    def lookup(self, query: ExpressionAtom, partial: bool = False) -> List[Atom]:
        """
        Find minimal sets that together cover all elements in the query.
        Returns list of (set, value) pairs.
        """
        elements = SortedSet(str(elem) for elem in query.get_children())
        result = []
        
        while elements:
            elem = elements.pop(0)
            try:
                match = self._find_best_match(self.root.children[elem], elements, set())
            except KeyError:
                if partial:
                    continue
                else:
                    return []

            if not match:
                if partial:
                    continue
                else:
                    return []
                
            match_set, match_value = match
            result.append(match_value)
            elements.difference_update(match_set)
            
        return result


    def lookup_all_subsets(self, query: ExpressionAtom) -> List[Atom]:
        """Find all trie nodes whose path is a subset of the query.
        Returns list of values for all matching nodes.
        """
        query_set = set(str(elem) for elem in query.get_children())
        results = []
        def traverse(node: TrieNode):
            for key, child in node.children.items():
                if key in query_set:
                    if child.value is not None:
                        results.append(child.value)
                    traverse(child)
        traverse(self.root)
        return results

class SpaceManager:
    def __init__(self):
        self.spaces: Dict[str, SetSpace] = {}
    
    def create_space(self) -> List[Atom]:
        space_name = f"space_{uuid.uuid4().hex[:8]}"
        name = S(space_name)
        self.spaces[space_name] = SetSpace()
        return [name]
    
    def get_space(self, name: SymbolAtom) -> Optional[SetSpace]:
        return self.spaces.get(str(name))
    
    def add_to_space(self, space_name: SymbolAtom, elements: ExpressionAtom, value: Atom) -> List[Atom]:
        space = self.get_space(space_name)
        if space:
            old_value = space.add(elements, value)
            return [old_value] if old_value else [value]
        return []
    
    def lookup_in_space(self, space_name: SymbolAtom, query: ExpressionAtom) -> List[ExpressionAtom]:
        space = self.get_space(space_name)
        if space:
            results = space.lookup(query)
            return [E(*results)] if results else [E()]
        return []

    def partial_lookup_in_space(self, space_name: SymbolAtom, query: ExpressionAtom) -> List[ExpressionAtom]:
        space = self.get_space(space_name)
        if space:
            results = space.lookup(query, partial=True)
            return [E(*results)] if results else [E(E())]
        return []
    
    def get_space_elements(self, space_name: SymbolAtom) -> List[ExpressionAtom]:
        space = self.get_space(space_name)
        if space:
            return space.get_all_elements()
        return []
        
    def pretty_print_space(self, space_name: SymbolAtom) -> List[Atom]:
        space = self.get_space(space_name)
        if space:
            space.pretty_print()
        return []
    
    def lookup_all_subsets_in_space(self, space_name: SymbolAtom, query: ExpressionAtom) -> List[ExpressionAtom]:
        space = self.get_space(space_name)
        if space:
            results = space.lookup_all_subsets(query)
            return [E(*results)] if results else [E()]
        return []

# Global SpaceManager instance
MANAGER = SpaceManager()

# Create operation atoms
create_space_atom = OperationAtom("create-setspace", MANAGER.create_space, ['Atom'], unwrap=False)
add_atom = OperationAtom("add-to-setspace", MANAGER.add_to_space, ['Atom', 'Expression', 'Atom', 'Atom'], unwrap=False)
lookup_atom = OperationAtom("lookup-in-setspace", MANAGER.lookup_in_space, ['Atom', 'Expression', 'Expression'], unwrap=False)
partial_lookup_atom = OperationAtom("partial-lookup-in-setspace", MANAGER.partial_lookup_in_space, ['Atom', 'Expression', 'Expression'], unwrap=False)
elements_atom = OperationAtom("get-setspace-elements", MANAGER.get_space_elements, ['Atom', 'Expression'], unwrap=False)
pretty_print_atom = OperationAtom("pretty-print-setspace", MANAGER.pretty_print_space, ['Atom', 'Atom'], unwrap=False)
lookup_all_subsets_atom = OperationAtom("lookup-all-subsets-in-setspace", MANAGER.lookup_all_subsets_in_space, ['Atom', 'Expression', 'Expression'], unwrap=False)

@register_atoms
def my_atoms():
    return {
        "create-setspace": create_space_atom,
        "add-to-setspace": add_atom,
        "lookup-in-setspace": lookup_atom,
        "partial-lookup-in-setspace": partial_lookup_atom,
        "get-setspace-elements": elements_atom,
        "pretty-print-setspace": pretty_print_atom,
        "lookup-all-subsets-in-setspace": lookup_all_subsets_atom
    }

if __name__ == "__main__":
    # Create a new space
    [space] = MANAGER.create_space()
    print(f"\nCreated space: {space}")
    
    # Add some test data
    print("\nTesting value overwriting:")
    result1 = MANAGER.add_to_space(space, E(S("A")), S("A-Value"))
    print(f"First add of A -> A-Value returns: {result1}")
    
    result2 = MANAGER.add_to_space(space, E(S("A")), S("New-A-Value"))
    print(f"Second add of A -> New-A-Value returns old value: {result2}")
    
    MANAGER.add_to_space(space, E(S("A"), S("B")), S("AB-Value"))
    MANAGER.add_to_space(space, E(S("B"), S("C")), S("BC-Value"))
    MANAGER.add_to_space(space, E(S("A"), S("C")), S("AC-Value"))
    MANAGER.add_to_space(space, E(S("D"), S("E")), S("DE-Value"))
    
    print("\nSpace contents:")
    MANAGER.pretty_print_space(space)
    
    # Test some lookups
    print("\nLookup tests:")
    tests = [
        E(S("A"), S("B")),
        E(S("B"), S("C")),
        E(S("A"), S("B"), S("C")),
        E(S("D"), S("E")),
        E(S("A"), S("D"))  # Should fail
    ]
    
    for test in tests:
        result = MANAGER.lookup_in_space(space, test)
        print(f"\nLooking up: {test}")
        print(f"Result: {result}")
    
    # Get all elements
    print("\nAll elements:")
    elements = MANAGER.get_space_elements(space)
    print(elements)
    
    # Test partial lookups
    print("\nPartial lookup tests:")
    partial_tests = [
        E(S("A"), S("B"), S("C")),  # Should return partial matches
        E(S("A"), S("D")),          # Should return A-Value
        E(S("X"), S("Y")),           # Should return empty
        E(S("A"), S("B"))
    ]
    
    for test in partial_tests:
        result = MANAGER.partial_lookup_in_space(space, test)
        print(f"\nPartial looking up: {test}")
        print(f"Result: {result}")
