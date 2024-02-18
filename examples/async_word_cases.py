# Here changing the cases of words represents data processing that may be computationally
# expensive or needs to be carried out sequentially for some other reason.


import asyncio
from typing import Optional, Iterable

from petri_net import AsyncPetriNet, Token, Place, Transition, ArcIn, ArcOut, PetriNet
from helpers.print_net import PrintPetriNet
from helpers.graph_net import GraphNet


initial_tokens = (
    Token("1", "ONE"),
    Token("2", "TWO"),
    Token("2", "ANOTHER TWO"),
    Token("3", "THREE IS THE MAGIC NUMBER"),
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


def select_token_by_id(places: dict[str, Place]) -> Optional[Token]:
    # Pick the first token according to sorted token ids.
    all_tokens = (t for p in places.values() for t in p.tokens)
    sorted_tokens = sorted(all_tokens, key=lambda t: t.id)
    return sorted_tokens[0] if sorted_tokens else None


def place_without_token(place: Place, token: Token) -> Place:
    return Place(place.id, place.name, tuple(t for t in place.tokens if t != token))


async def lower_case(text: str) -> str:
    await asyncio.sleep(0.01)  # Simulate waiting for data.
    return text.lower()


async def snake_case(text: str) -> str:
    await asyncio.sleep(0.01)  # Simulate waiting for data.
    return text.replace(" ", "_")


async def fire_transition_from_0_to_1(
    input_places: dict[str, Place], output_places: dict[str, Place]
) -> tuple[dict[str, Place], dict[str, Place]]:
    token_to_move = select_token_by_id(input_places)
    if token_to_move is None:
        return input_places, output_places
    input_places_sans_token = {p.id: place_without_token(p, token_to_move) for _, p in input_places.items()}
    lower_case_data = await lower_case(token_to_move.data)
    transformed_token = Token(token_to_move.id, lower_case_data)
    output_places_with_token = {
        p.id: Place(p.id, p.name, p.tokens + (transformed_token,)) for _, p in output_places.items()
    }
    return input_places_sans_token, output_places_with_token


async def fire_transition_from_1_to_2(
    input_places: Iterable[Place], output_places: Iterable[Place]
) -> tuple[dict[str, Place], dict[str, Place]]:
    token_to_move = select_token_by_id(input_places)
    if token_to_move is None:
        return input_places, output_places
    input_places_sans_token = {p.id: place_without_token(p, token_to_move) for _, p in input_places.items()}
    snake_case_data = await snake_case(token_to_move.data)
    transformed_token = Token(token_to_move.id, snake_case_data)
    output_places_with_token = {
        p.id: Place(p.id, p.name, p.tokens + (transformed_token,)) for _, p in output_places.items()
    }
    return input_places_sans_token, output_places_with_token


transition_from_0_to_1 = Transition(
    id="lower_case",
    name="Lower Case",
    fire=fire_transition_from_0_to_1,
    maximum_firings=4,
)

transition_from_1_to_2 = Transition(
    id="snake_case",
    name="Snake Case",
    fire=fire_transition_from_1_to_2,
    maximum_firings=4,
)


def transition_selection_function(net: PetriNet) -> Optional[Transition]:
    # More complicated user defined logic could be used here.
    if len(net.places["starting_place"].tokens) > 0:
        return transition_from_0_to_1
    elif len(net.places["middle_place"].tokens) > 0:
        return transition_from_1_to_2
    return None


petri_net = PetriNet(
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


GraphNet.to_png(petri_net, "graph")


async def main(petri_net):
    transition_firing = True
    PrintPetriNet.places_and_tokens(petri_net)
    while transition_firing:
        print('\n')
        petri_net, transition_firing = await AsyncPetriNet.step(petri_net, transition_selection_function)
        PrintPetriNet.places_and_tokens(petri_net)


asyncio.run(main(petri_net=petri_net))
