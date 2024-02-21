from graphviz import Digraph

from petri_net import PetriNet


class GraphNet:

    def to_file(petri_net: PetriNet, file_path: str, include_token_ids=True, format="png") -> None:
        delim = ": "
        nl = "\n"
        dot = Digraph()
        for (place_id, place) in petri_net.places.items():
            if include_token_ids:
                place_name_and_tokens = (
                    f"{place.name}\n"
                    f"{''.join([t.id + delim + str(t.data) + nl  for t in place.tokens])}"
                )
                dot.node(place.id, place_name_and_tokens, shape="box", style="rounded")
            else:
                dot.node(place.id, place.name)
        for (transition_id, transition) in petri_net.transitions.items():
            dot.node(transition_id, transition.name, shape="box")
        for arc in petri_net.arcs_in:
            dot.edge(arc.place_id, arc.transition_id)
        for arc in petri_net.arcs_out:
            dot.edge(arc.transition_id, arc.place_id)
        dot.render(file_path, format=format, cleanup=True)
