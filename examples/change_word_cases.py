# Here changing the cases of words represents data processing that may be computationally
# expensive or needs to be carried out sequentially for some other reason.

from petri_net import (
    SyncFiringFunctions, SelectToken, SelectTransition, SyncPetriNet, Token, Place, Transition, ArcIn, ArcOut, PetriNet
)
from helpers.print_net import PrintPetriNet
from helpers.graph_net import GraphNet


initial_tokens = (
    Token("1", "ONE", priority=1),
    Token("2", "TWO", priority=2),
    Token("2", "ANOTHER TWO", priority=3),
    Token("3", "THREE IS THE MAGIC NUMBER", priority=4),
)

place_0 = Place(
    id="starting_place",
    name="All Caps",
    tokens=initial_tokens,
)
place_1 = Place(
    id="middle_place",
    name="Lower Case",
    tokens=tuple(),
)
place_2 = Place(
    id="final_place",
    name="Snake Case",
    tokens=tuple(),
)

transition_from_0_to_1 = Transition(
    id="lower_case",
    name="Lower Case",
    fire=lambda input_places, output_places: SyncFiringFunctions.move_and_transform_highest_priority_token(
        input_places, output_places, lambda t: Token(t.id, t.data.lower()),
    ),
    maximum_firings=4,
    priority_function=lambda input_places, _: SelectToken.total_count(input_places) * 100,
)
transition_from_1_to_2 = Transition(
    id="snake_case",
    name="Snake Case",
    fire=lambda input_places, output_places: SyncFiringFunctions.move_and_transform_highest_priority_token(
        input_places, output_places, lambda t: Token(t.id, t.data.replace(" ", "_")),
    ),
    maximum_firings=4,
    priority_function=lambda input_places, _: SelectToken.total_count(input_places) * 1,
)

starting_petri_net = PetriNet(
    places={place.id: place for place in (place_0, place_1, place_2)},
    transitions={t.id: t for t in (transition_from_0_to_1, transition_from_1_to_2)},
    arcs_in={
        ArcIn(place_id=place_0.id, transition_id=transition_from_0_to_1.id),
        ArcIn(place_id=place_1.id, transition_id=transition_from_1_to_2.id),
    },
    arcs_out={
        ArcOut(transition_id=transition_from_0_to_1.id, place_id=place_1.id),
        ArcOut(transition_id=transition_from_1_to_2.id, place_id=place_2.id),
    },
)


def main(save_graphs_to_files: bool = False):
    if save_graphs_to_files:
        GraphNet.to_file(starting_petri_net, "graph_before", format="png")

    transition_firing = True
    petri_net = starting_petri_net
    while transition_firing:
        print('\n')
        petri_net, transition_firing = SyncPetriNet.step(
            petri_net, SelectTransition.using_priority_functions,
        )
        PrintPetriNet.places_and_tokens(petri_net)

    if save_graphs_to_files:
        GraphNet.to_file(petri_net, "graph_after", format="png")


if __name__ == "__main__":
    main()
