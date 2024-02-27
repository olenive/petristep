# Here changing the cases of words represents data processing that may be computationally
# expensive or needs to be carried out sequentially for some other reason.

from pathlib import Path

from petri_net import New, SelectTransition, SyncPetriNet, SyncTransition, Token, Place, ArcIn
from helpers.print_net import PrintPetriNet
from helpers.graph_net import GraphNet


def tokens_from_comma_delimited(token: Token) -> tuple[Token]:
    return tuple(
        Token(id=str(i), data=word, priority=1)
        for i, word in enumerate(token.data.split(", "))
    )


def routing_function(token: Token) -> tuple[str]:
    number_of_words = len(token.data.split(' '))
    if number_of_words <= 1:
        return "Go Left",
    if number_of_words == 2:
        return "Go Down",
    else:
        return "Go Right",


nodes_and_edges = (
    # Create a place holding the initial token.
    Place(
        id="starting_place",
        name="All Caps",
        tokens=(
            Token(id="1", data="ONE, TWO, ANOTHER TWO, THREE IS THE MAGIC NUMBER",),
        ),
    ),

    # Split by comma into separate tokens.
    ArcIn("starting_place", "to_many_tokens"),
    SyncTransition.expand("to_many_tokens", tokens_from_comma_delimited, 1, 1),
    *New.arc_out_and_empty_place("to_many_tokens", "From comma delimited"),

    # Pick a path.
    ArcIn("From comma delimited", "pick_direction"),
    SyncTransition.fork("pick_direction", lambda token: token, routing_function, 4, 2),
    *New.arc_out_and_empty_place("pick_direction", "Go Left"),
    *New.arc_out_and_empty_place("pick_direction", "Go Down"),
    *New.arc_out_and_empty_place("pick_direction", "Go Right"),

    # Join the paths.
    ArcIn("Go Left", "lower_case"),
    ArcIn("Go Down", "lower_case"),
    ArcIn("Go Right", "lower_case"),
    SyncTransition.flip("lower_case", lambda t: Token(t.id, t.data.lower()), 4, 3),
    *New.arc_out_and_empty_place("lower_case", "Lower Case"),

    # Convert to snake case.
    ArcIn("Lower Case", "snake_case"),
    SyncTransition.flip("snake_case", lambda t: Token(t.id, t.data.replace(' ', '_')), 4, 4),
    *New.arc_out_and_empty_place("snake_case", "Snake Case"),
)

starting_petri_net = New.petri_net(nodes_and_edges)


def main(save_graphs_to_files: bool = False):
    if save_graphs_to_files:
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
        if save_graphs_to_files:
            GraphNet.to_file(petri_net, graphs_dir/f"{step_count:03}_step", format="svg")

    if save_graphs_to_files:
        GraphNet.to_file(petri_net, graphs_dir/"after", format="svg")


if __name__ == "__main__":
    main()
