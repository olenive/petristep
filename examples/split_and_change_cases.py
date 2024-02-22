# Here changing the cases of words represents data processing that may be computationally
# expensive or needs to be carried out sequentially for some other reason.

from pathlib import Path

from petri_net import (
    SyncFiringFunctions, SelectToken, SelectTransition, SyncPetriNet, Token, Place, Transition, ArcIn, ArcOut, PetriNet
)
from helpers.print_net import PrintPetriNet
from helpers.graph_net import GraphNet

places = (
    Place(
        id="starting_place",
        name="All Caps",
        tokens=(
            Token(id="1", data="ONE, TWO, ANOTHER TWO, THREE IS THE MAGIC NUMBER",),
        ),
    ),
    Place(
        id="to_many_tokens",
        name="From comma delimited",
        tokens=tuple(),
    ),
    Place(
        id="class_a",
        name="Go Left",
        tokens=tuple(),
    ),
    Place(
        id="class_b",
        name="Go Down",
        tokens=tuple(),
    ),
    Place(
        id="class_c",
        name="Go Right",
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
places = {place.id: place for place in places}


def tokens_from_comma_delimited(data: str) -> tuple[Token]:
    return tuple(
        Token(id=str(i), data=word, priority=1)
        for i, word in enumerate(data.split(", "))
    )


def routing_function(token: Token) -> tuple[str]:
    number_of_words = len(token.data.split(' '))
    if number_of_words <= 1:
        return "class_a",
    if number_of_words == 2:
        return "class_b",
    else:
        return "class_c",


transitions = (
    Transition(
        id="split_string",
        name="Split string to tokens",
        fire=lambda input_places, output_places: SyncFiringFunctions.move_and_expand_highest_priority_token(
            input_places, output_places, tokens_from_comma_delimited, #destination_place_ids=("to_many_tokens",)
        ),
        maximum_firings=1,
        priority_function=lambda input_places, _: SelectToken.total_count(input_places) * 1,
    ),
    Transition(
        id="pick_direction",
        name="Pick a direction",
        fire=lambda input_places, output_places: SyncFiringFunctions.route_and_transform_highest_priority_token(
            input_places,
            output_places,
            routing_function=routing_function,
            transform_function=lambda t: t,
        ),
        maximum_firings=4,
        priority_function=lambda input_places, _: SelectToken.total_count(input_places) * 1,
    ),
    Transition(
        id="lower_case",
        name="Lower Case",
        fire=lambda input_places, output_places: SyncFiringFunctions.move_and_transform_highest_priority_token(
            input_places, output_places, lambda t: t.data.lower(),
        ),
        maximum_firings=4,
        priority_function=lambda input_places, _: SelectToken.total_count(input_places) * 100,
    ),
    Transition(
        id="snake_case",
        name="Snake Case",
        fire=lambda input_places, output_places: SyncFiringFunctions.move_and_transform_highest_priority_token(
            input_places, output_places, lambda t: t.data.replace(" ", "_"),
        ),
        maximum_firings=4,
        priority_function=lambda input_places, _: SelectToken.total_count(input_places) * 1,
    ),
)
transitions = {t.id: t for t in transitions}

arcs = (
    ArcIn(place_id="starting_place", transition_id="split_string"),
    ArcOut(transition_id="split_string", place_id="to_many_tokens"),
    ArcIn(place_id="to_many_tokens", transition_id="pick_direction"),
    ArcOut(transition_id="pick_direction", place_id="class_a"),
    ArcOut(transition_id="pick_direction", place_id="class_b"),
    ArcOut(transition_id="pick_direction", place_id="class_c"),
    ArcIn(place_id="class_a", transition_id="lower_case"),
    ArcIn(place_id="class_b", transition_id="lower_case"),
    ArcIn(place_id="class_c", transition_id="lower_case"),
    ArcOut(transition_id="lower_case", place_id="middle_place"),
    ArcIn(place_id="middle_place", transition_id="snake_case"),
    ArcOut(transition_id="snake_case", place_id="final_place"),
)

starting_petri_net = PetriNet(
    places=places,
    transitions=transitions,
    arcs_in={x for x in arcs if isinstance(x, ArcIn)},
    arcs_out={x for x in arcs if isinstance(x, ArcOut)},
)


def main(plot_graphs: bool = False):
    if plot_graphs:
        graphs_dir = Path("graphs")
        graphs_dir.mkdir(exist_ok=True, parents=True)
        GraphNet.to_file(starting_petri_net, graphs_dir/"000_before", format="svg")
    transition_firing = True
    petri_net = starting_petri_net
    PrintPetriNet.places_and_tokens(petri_net)
    step_count = 0
    while transition_firing:
        step_count += 1
        print('\n')
        petri_net, transition_firing = SyncPetriNet.step(
            petri_net, SelectTransition.using_priority_functions,
        )
        PrintPetriNet.places_and_tokens(petri_net)
        if plot_graphs:
            GraphNet.to_file(petri_net, graphs_dir/f"{step_count:03}_step", format="svg")

    if plot_graphs:
        GraphNet.to_file(petri_net, graphs_dir/"after", format="svg")


if __name__ == "__main__":
    main()
