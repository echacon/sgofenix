# utils/reachability.py
from typing import Dict, List, Set, Tuple, Optional, Callable, Any
from collections import deque
from dataclasses import dataclass, field
from models.RedPetri import RedPetri  # para type hints, pero evitamos circular

@dataclass
class StateNode:
    """Nodo del grafo de alcanzabilidad (marcado)"""
    marking: Tuple[Tuple[str, int], ...]  # representación inmutable
    transitions: List[str] = field(default_factory=list)  # transiciones que salen
    cost: float = 0.0
    time: float = 0.0
    parent: Optional['StateNode'] = None
    depth: int = 0

def compute_reachability_graph(
    red: Any,  # objeto PetriNet con places, transitions, arcs
    initial_marking: Dict[str, int],
    transition_duration_func: Callable[[str], float] = lambda t: 0.0,
    transition_cost_func: Callable[[str], float] = lambda t: 0.0,
    max_states: int = 10000,
    max_depth: int = 100
) -> Tuple[Dict[Tuple, StateNode], List[StateNode]]:
    """
    Construye el grafo de alcanzabilidad.
    Retorna: (diccionario {marcado_tuple: nodo}, lista de nodos finales)
    """
    def marking_to_tuple(marking: Dict[str, int]) -> Tuple[Tuple[str, int], ...]:
        return tuple((p, marking.get(p, 0)) for p in sorted(marking.keys()))
    
    def tuple_to_marking(tup):
        return {p: cnt for p, cnt in tup}
    
    # Precomputar entradas y salidas de cada transición
    entradas = {}
    salidas = {}
    for tid in red.transitions:
        entradas[tid] = {}
        salidas[tid] = {}
        for arc in red.arcs.values():
            if arc.target == tid:
                entradas[tid][arc.source] = arc.peso
            elif arc.source == tid:
                salidas[tid][arc.target] = arc.peso
    
    def enabled_transitions(marking: Dict[str, int]) -> List[str]:
        enabled = []
        for tid in red.transitions:
            ok = True
            for lugar, peso in entradas[tid].items():
                if marking.get(lugar, 0) < peso:
                    ok = False
                    break
            if ok:
                enabled.append(tid)
        return enabled
    
    def fire(marking: Dict[str, int], tid: str) -> Dict[str, int]:
        new_mark = marking.copy()
        for lugar, peso in entradas[tid].items():
            new_mark[lugar] = new_mark.get(lugar, 0) - peso
            if new_mark[lugar] <= 0:
                del new_mark[lugar]
        for lugar, peso in salidas[tid].items():
            new_mark[lugar] = new_mark.get(lugar, 0) + peso
        return new_mark
    
    start_tuple = marking_to_tuple(initial_marking)
    start_node = StateNode(marking=start_tuple, depth=0)
    state_map = {start_tuple: start_node}
    queue = deque([start_node])
    final_nodes = []
    
    while queue and len(state_map) < max_states:
        node = queue.popleft()
        if node.depth >= max_depth:
            continue
        current_marking = tuple_to_marking(node.marking)
        # Verificar si es final (definimos luego)
        for tid in enabled_transitions(current_marking):
            new_marking = fire(current_marking, tid)
            new_tuple = marking_to_tuple(new_marking)
            if new_tuple not in state_map:
                new_node = StateNode(
                    marking=new_tuple,
                    parent=node,
                    depth=node.depth + 1,
                    cost=node.cost + transition_cost_func(tid),
                    time=node.time + transition_duration_func(tid)
                )
                state_map[new_tuple] = new_node
                queue.append(new_node)
            else:
                # ya existe, pero podemos registrar la transición adicional
                pass
            # Agregar la transición al nodo origen
            if tid not in node.transitions:
                node.transitions.append(tid)
    
    # Identificar nodos finales: aquellos que no tienen transiciones habilitadas
    for node in state_map.values():
        mark = tuple_to_marking(node.marking)
        if not enabled_transitions(mark):
            final_nodes.append(node)
    
    return state_map, final_nodes