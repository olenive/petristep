from graphviz import Digraph
from warnings import warn

from petri_net import PetriNet, Token


class GraphNet:

    def format_data_dict(data: dict, max_characters_per_field: int) -> str:
        return "\n".join(
            f"{k}: {v[:max_characters_per_field]}{'...' if len(v) > max_characters_per_field else ''}"
            for k, v in data.items()
        )
    
    def format_token_data(token: Token, max_characters_per_field: int) -> str:
        delim = ": "
        if token.data is None:
            formatted_data = ""
        elif isinstance(token.data, dict):
            formatted_data = GraphNet.format_data_dict(token.data, max_characters_per_field)
        else:
            formatted_data = str(token.data)
        return token.id + delim + formatted_data + "\n"

    def to_file(
        petri_net: PetriNet, file_path: str, include_token_ids=True, format="png", max_characters_per_field=100
    ) -> None:
        dot = Digraph()
        for (place_id, place) in petri_net.places.items():
            if include_token_ids:
                tokens_info = [GraphNet.format_token_data(t, max_characters_per_field) for t in place.tokens]
                place_name_and_tokens = (
                    f"{place.name}\n"
                    f"{''.join(tokens_info)}"
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
