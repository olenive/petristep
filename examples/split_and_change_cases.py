# Here changing the cases of words represents data processing that may be computationally
# expensive or needs to be carried out sequentially for some other reason.

from petri_net import (
    SyncFiringFunctions, SelectToken, SelectTransition, SyncPetriNet, Token, Place, Transition, ArcIn, ArcOut, PetriNet
)
from helpers.print_net import PrintPetriNet
from helpers.graph_net import GraphNet

places = (
    Place(
        id="starting_place",
        name="All Caps",
        tokens=(Token(
            id="1", data="ONE, TWO, ANOTHER TWO, THREE IS THE MAGIC NUMBER", priority_function=lambda data: 1,
        ),),
    ),
    Place(
        id="from_one_to_many",
        name="From comma delimited",
        tokens=tuple(),
    ),
    Place(
        id="middle_place",
        name="Lower Case",
        tokens=tuple(),
    ),
    Place(
        id="final_place",
        name="Snake Case",
        tokens=tuple(),
    ),
)


def tokens_from_comma_delimited(data: str) -> tuple[Token]:
    return tuple(
        Token(id=str(i), data=word, priority_function=lambda data: 1)
        for i, word in enumerate(data.split(", "))
    )


transition_0_1 = Transition(
    id="split_string",
    name="Split string to tokens",
    fire=lambda input_places, output_places: SyncFiringFunctions.move_and_expand_highest_priority_token(
        input_places, output_places, tokens_from_comma_delimited, destination_place_ids=("from_one_to_many",)
    ),
    maximum_firings=1,
    priority_function=lambda input_places, _: SelectToken.total_count(input_places) * 1,
)
transition_1_2 = Transition(
    id="lower_case",
    name="Lower Case",
    fire=lambda input_places, output_places: SyncFiringFunctions.move_and_transform_highest_priority_token(
        input_places, output_places, lambda data: data.lower(), destination_place_ids=("middle_place",)
    ),
    maximum_firings=4,
    priority_function=lambda input_places, _: SelectToken.total_count(input_places) * 100,
)
transition_2_3 = Transition(
    id="snake_case",
    name="Snake Case",
    fire=lambda input_places, output_places: SyncFiringFunctions.move_and_transform_highest_priority_token(
        input_places, output_places, lambda data: data.replace(" ", "_"), destination_place_ids=("final_place",)
    ),
    maximum_firings=4,
    priority_function=lambda input_places, _: SelectToken.total_count(input_places) * 1,
)

starting_petri_net = PetriNet(
    places={place.id: place for place in places},
    transitions={t.id: t for t in (transition_0_1, transition_1_2, transition_2_3)},
    arcs_in={
        ArcIn(place_id=places[0].id, transition_id=transition_0_1.id),
        ArcIn(place_id=places[1].id, transition_id=transition_1_2.id),
        ArcIn(place_id=places[2].id, transition_id=transition_2_3.id),
    },
    arcs_out={
        ArcOut(transition_id=transition_0_1.id, place_id=places[1].id),
        ArcOut(transition_id=transition_1_2.id, place_id=places[2].id),
        ArcOut(transition_id=transition_2_3.id, place_id=places[3].id),
    },
)


def main():
    GraphNet.to_file(starting_petri_net, "graph_before", format="png")

    transition_firing = True
    petri_net = starting_petri_net
    PrintPetriNet.places_and_tokens(petri_net)
    while transition_firing:
        print('\n')
        petri_net, transition_firing = SyncPetriNet.step(
            petri_net, SelectTransition.using_priority_functions,
        )
        PrintPetriNet.places_and_tokens(petri_net)

    GraphNet.to_file(petri_net, "graph_after", format="png")


if __name__ == "__main__":
    main()
