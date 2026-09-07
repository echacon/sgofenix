# utils/global_reachability.py
from typing import Dict, List, Tuple, Set, Optional
from collections import deque
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class GlobalState:
    """Estado global: marcados de cada red y cola de mensajes."""
    markings: Tuple[Tuple[str, Tuple[Tuple[str, int], ...]], ...]  # (red, marcado_tuple)
    mailbox: Tuple[Tuple[str, str], ...]  # (red_destino, evento)
    depth: int = 0
    parent: Optional['GlobalState'] = None
    transition_info: Optional[str] = None

def compute_global_reachability(
    redes: Dict[str, object],          # nombre -> objeto PetriNet (con places, transitions, arcs)
    encadenamiento: Dict[Tuple[str, str], List[Tuple[str, str]]],  # (red_origen, trans_id) -> [(red_dest, evento)]
    initial_markings: Dict[str, Dict[str, int]],   # red -> marking inicial
    final_places: Dict[str, List[str]],            # red -> lista de lugares finales
    max_states: int = 10000,
    max_depth: int = 100
) -> Tuple[bool, str, Optional[GlobalState]]:
    """
    BFS sobre el espacio de estados global de las redes comunicantes.
    Retorna: (alcanzable, mensaje, estado_final_opt)
    """
    # Precomputar entradas/salidas por transición para cada red
    net_data = {}
    for name, net in redes.items():
        entradas = {}
        salidas = {}
        for tid in net.transitions:
            entradas[tid] = {}
            salidas[tid] = {}
            for arc in net.arcs.values():
                if arc.target == tid:
                    entradas[tid][arc.source] = arc.peso
                elif arc.source == tid:
                    salidas[tid][arc.target] = arc.peso
        net_data[name] = {
            'net': net,
            'entradas': entradas,
            'salidas': salidas,
            'initial': initial_markings[name],
            'final_places': final_places.get(name, [])
        }

    def marking_to_tuple(mark: Dict[str, int]) -> Tuple[Tuple[str, int], ...]:
        return tuple((p, mark.get(p, 0)) for p in sorted(mark.keys()))

    def tuple_to_marking(tup):
        return {p: cnt for p, cnt in tup}

    # Estado inicial
    init_markings_tuple = tuple(
        (name, marking_to_tuple(net_data[name]['initial']))
        for name in sorted(redes.keys())
    )
    init_mailbox = ()
    start_state = GlobalState(markings=init_markings_tuple, mailbox=init_mailbox, depth=0)

    visited: Set[Tuple[Tuple, Tuple]] = set()
    queue = deque([start_state])

    while queue and len(visited) < max_states:
        state = queue.popleft()
        key = (state.markings, state.mailbox)
        if key in visited:
            continue
        visited.add(key)

        # Convertir a dicts para manipular
        curr_markings = {name: tuple_to_marking(tup) for name, tup in state.markings}
        curr_mailbox = list(state.mailbox)

        # Verificar si es estado final
        all_terminated = True
        for name, data in net_data.items():
            mark = curr_markings[name]
            # Se considera terminada si algún lugar final tiene token
            if not any(mark.get(p, 0) > 0 for p in data['final_places']):
                all_terminated = False
                break
        if all_terminated and len(curr_mailbox) == 0:
            return True, "Se alcanzó estado global final", state

        # Generar sucesores
        # 1. Transiciones automáticas (trigger=None) y externas (trigger=200) en cada red
        for name, data in net_data.items():
            net = data['net']
            mark = curr_markings[name]
            for tid, trans in net.transitions.items():
                trigger = getattr(trans, 'trigger', None)
                if trigger is None or trigger == '200':  # automática o evento externo
                    # Verificar habilitación
                    ent = data['entradas'][tid]
                    ok = all(mark.get(lugar, 0) >= peso for lugar, peso in ent.items())
                    if not ok:
                        continue
                    # Disparar
                    new_mark = dict(mark)
                    for lugar, peso in ent.items():
                        new_mark[lugar] -= peso
                        if new_mark[lugar] <= 0:
                            del new_mark[lugar]
                    for lugar, peso in data['salidas'][tid].items():
                        new_mark[lugar] = new_mark.get(lugar, 0) + peso
                    new_mark_tuple = marking_to_tuple(new_mark)
                    new_markings_list = list(state.markings)
                    # Reemplazar la red correspondiente
                    for i, (n, _) in enumerate(new_markings_list):
                        if n == name:
                            new_markings_list[i] = (name, new_mark_tuple)
                            break
                    new_markings = tuple(new_markings_list)
                    # Generar mensajes si la transición produce encadenamiento
                    new_mailbox = list(state.mailbox)
                    key_enc = (name, tid)
                    if key_enc in encadenamiento:
                        for dest_net, event in encadenamiento[key_enc]:
                            new_mailbox.append((dest_net, event))
                    # Añadir a la cola
                    child = GlobalState(
                        markings=new_markings,
                        mailbox=tuple(new_mailbox),
                        depth=state.depth + 1,
                        parent=state,
                        transition_info=f"{name}.{trans.nombre or tid}"
                    )
                    if child.depth <= max_depth:
                        queue.append(child)

        # 2. Consumo de mensajes (trigger=201)
        for name, data in net_data.items():
            net = data['net']
            mark = curr_markings[name]
            # Buscar transiciones con trigger=201
            for tid, trans in net.transitions.items():
                if getattr(trans, 'trigger', None) != '201':
                    continue
                event_name = trans.nombre
                # Buscar el mensaje en la cola
                for idx, (dest, evt) in enumerate(curr_mailbox):
                    if dest == name and evt == event_name:
                        # Verificar habilitación
                        ent = data['entradas'][tid]
                        ok = all(mark.get(lugar, 0) >= peso for lugar, peso in ent.items())
                        if not ok:
                            continue
                        # Disparar
                        new_mark = dict(mark)
                        for lugar, peso in ent.items():
                            new_mark[lugar] -= peso
                            if new_mark[lugar] <= 0:
                                del new_mark[lugar]
                        for lugar, peso in data['salidas'][tid].items():
                            new_mark[lugar] = new_mark.get(lugar, 0) + peso
                        new_mark_tuple = marking_to_tuple(new_mark)
                        new_markings_list = list(state.markings)
                        for i, (n, _) in enumerate(new_markings_list):
                            if n == name:
                                new_markings_list[i] = (name, new_mark_tuple)
                                break
                        new_markings = tuple(new_markings_list)
                        # Consumir mensaje
                        new_mailbox = list(curr_mailbox)
                        new_mailbox.pop(idx)
                        child = GlobalState(
                            markings=new_markings,
                            mailbox=tuple(new_mailbox),
                            depth=state.depth + 1,
                            parent=state,
                            transition_info=f"MSG:{name}.{trans.nombre or tid}"
                        )
                        if child.depth <= max_depth:
                            queue.append(child)
                        break  # solo consumir un mensaje por transición para evitar explosión

    return False, f"Límite de estados alcanzado ({max_states}) sin llegar a estado final", None