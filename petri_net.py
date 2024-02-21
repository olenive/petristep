from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Coroutine, Iterable, Optional, Callable, Union


@dataclass(frozen=True)
class Token:
    id: str
    data: Optional[Any]
    priority: int = 1


@dataclass
class Place:
    id: str
    name: Optional[str]
    tokens: Iterable[Token]


FireFunctionType = Union[
    Callable[[dict[str, Place], dict[str, Place]], tuple[dict[str, Place], dict[str, Place]]],
    Callable[[dict[str, Place], dict[str, Place]], Coroutine[Any, Any, tuple[dict[str, Place], dict[str, Place]]]]
]


@dataclass
class Transition:
    id: str
    name: Optional[str]
    fire: FireFunctionType
    maximum_firings: Optional[int] = 1
    firings_count: int = 0
    priority_function: Optional[Callable[[dict[str, Place], dict[str, Place]], int]] = \
        lambda input_places, _: len(tuple(token for place in input_places.values() for token in place.tokens))


@dataclass(frozen=True)
class ArcIn:
    place_id: str
    transition_id: str


@dataclass(frozen=True)
class ArcOut:
    transition_id: str
    place_id: str


@dataclass
class PetriNet:
    places: dict[str, Place]
    transitions: dict[str, Transition]
    arcs_in: set[ArcIn]
    arcs_out: set[ArcOut]


class TransitionFiringLimitExceeded(Exception):
    pass


class TokenTypeError(Exception):
    pass


class PlaceTypeError(Exception):
    pass


class PetriNetCheck:

    def token(token: Token) -> None:
        if not isinstance(token, Token):
            raise TokenTypeError(f"Expected Token, got {type(token)}.")
        if not isinstance(token.id, str):
            raise TokenTypeError(f"Expected token id to be a str, got {type(token.id)}.")
        if not isinstance(token, Token):
            raise TokenTypeError(f"Expected Token, got {type(token)}.")

    def tokens(tokens: Iterable[Token]) -> None:
        for token in tokens:
            PetriNetCheck.token(token)

    def place(place: Place) -> None:
        if not isinstance(place.id, str):
            raise PlaceTypeError(f"Expected place id to be a str, got {type(place.id)}.")
        if not isinstance(place.name, str):
            raise PlaceTypeError(f"Expected place name to be a str, got {type(place.name)}.")
        if not isinstance(place, Place):
            raise PlaceTypeError(f"Expected Place, got {type(place)}.")
        PetriNetCheck.tokens(place.tokens)

    def places(places: Iterable[Place]) -> None:
        for place in places:
            PetriNetCheck.place(place)


class SelectToken:

    def total_count(places: dict[str, Place]) -> int:
        return sum(len(place.tokens) for place in places.values())

    def with_highest_priority(places: dict[str, Place]) -> Optional[Token]:
        tokens = tuple(token for place in places.values() for token in place.tokens)
        if len(tokens) == 0:
            return None, places
        tokens_with_priority = ((token, token.priority) for token in tokens)
        sorted_by_priority = sorted(tokens_with_priority, key=lambda item: item[1], reverse=True)
        return sorted_by_priority[0][0]


class RemoveToken:

    def with_highest_priority(places: dict[str, Place]) -> tuple[Optional[Token], dict[str, Place]]:
        token = SelectToken.with_highest_priority(places)
        if token is None:
            return None, places
        places_sans_token = {
            place_id: Place(place.id, place.name, tuple(t for t in place.tokens if t != token))
            for place_id, place in places.items()
        }
        return token, places_sans_token


class AddTokens:

    def to_place(tokens: Iterable[Token], place: Place, checks=True) -> Place:
        if checks:
            PetriNetCheck.tokens(tokens)
        resulting_place = Place(place.id, place.name, place.tokens + tuple(tokens))
        if checks:
            PetriNetCheck.place(resulting_place)
        return resulting_place

    def to_output_places(
        tokens: tuple[Token, ...],
        destination_place_ids: Optional[tuple[str, ...]],
        output_places: dict[str, Place],
        checks=True,
    ) -> dict[str, Place]:
        if destination_place_ids is not None:  # Add token only to the specified destination places.
            if not isinstance(destination_place_ids, tuple):
                raise ValueError(f"destination_place_ids should be a tuple, not {type(destination_place_ids)}.")
            out = {}
            for place_id, place in output_places.items():
                if place_id in destination_place_ids:
                    out[place_id] = AddTokens.to_place(tokens, place, checks=checks)
                else:
                    out[place_id] = place
            return out
        else:  # Add token to all output places.
            return {
                place_id: AddTokens.to_place(tokens, place, checks=checks)
                for place_id, place in output_places.items()
            }


class SelectTransition:

    def using_priority_functions(net: PetriNet) -> Optional[Transition]:
        priorities = PetriNetOperations.transition_priorities(net)
        for transition_id, priority in priorities.items():
            if priority > 0:
                return net.transitions[transition_id]
        return None


class SyncFiringFunctions:

    def move_and_transform_highest_priority_token(
        input_places: dict[str, Place],
        output_places: dict[str, Place],
        transform_function: Callable[[Token], Token],
        destination_place_ids: Optional[tuple[str, ...]] = None,
    ) -> tuple[dict[str, Place], dict[str, Place]]:
        """Remove one token from the input places and make a corresponding token in the output places."""
        token_to_move, input_places_sans_token = RemoveToken.with_highest_priority(input_places)
        if token_to_move is None:
            return input_places, output_places
        transformed_data = transform_function(token_to_move)
        new_token = Token(token_to_move.id, transformed_data)
        output_places_with_token = AddTokens.to_output_places(
            (new_token,), destination_place_ids, output_places
        )
        return input_places_sans_token, output_places_with_token

    def move_and_expand_highest_priority_token(
        input_places: dict[str, Place],
        output_places: dict[str, Place],
        expand_function: Callable[[Any], tuple[Token, ...]],
        destination_place_ids: Optional[tuple[str, ...]] = None,
        checks=True,
    ) -> tuple[dict[str, Place], dict[str, Place]]:
        """Remove one token and make many tokens from it."""
        token_to_move, input_places_sans_token = RemoveToken.with_highest_priority(input_places)
        if token_to_move is None:
            return input_places, output_places
        new_tokens = expand_function(token_to_move.data)
        if checks:
            PetriNetCheck.tokens(new_tokens)
        output_places_with_tokens = AddTokens.to_output_places(
            new_tokens, destination_place_ids, output_places
        )
        return input_places_sans_token, output_places_with_tokens

    def route_and_transform_highest_priority_token(
        input_places: dict[str, Place],
        output_places: dict[str, Place],
        routing_function: Callable[[Token], str],
        transform_function: Callable[[Token], Token],
    ) -> tuple[dict[str, Place], dict[str, Place]]:
        """Path a token to a destination place and transform the token."""
        token_to_move, input_places_sans_token = RemoveToken.with_highest_priority(input_places)
        if token_to_move is None:
            return input_places, output_places
        selected_place_id: str = routing_function(token_to_move)
        new_token: Token = transform_function(token_to_move)
        output_places_with_token = AddTokens.to_output_places(
            (new_token,), (selected_place_id,), output_places
        )
        return input_places_sans_token, output_places_with_token


class AsyncFiringFunctions:

    async def move_and_transform_highest_priority_token(
        input_places: dict[str, Place],
        output_places: dict[str, Place],
        asynchronous_transform_function: Callable[[Token], Token],
        destination_place_ids: Optional[tuple[str, ...]] = None,
    ) -> tuple[dict[str, Place], dict[str, Place]]:
        token_to_move, input_places_sans_token = RemoveToken.with_highest_priority(input_places)
        if token_to_move is None:
            return input_places, output_places
        new_token = await asynchronous_transform_function(token_to_move)
        output_places_with_token = AddTokens.to_output_places(
            tokens=(new_token,),
            destination_place_ids=destination_place_ids,
            output_places=output_places,
        )
        return input_places_sans_token, output_places_with_token

    async def move_and_expand_highest_priority_token(
        input_places: dict[str, Place],
        output_places: dict[str, Place],
        asynchronous_expand_function: Callable[[Any], Coroutine[Any, Any, tuple[Token, ...]]],
        destination_place_ids: Optional[tuple[str, ...]] = None,
        checks=True,
    ) -> tuple[dict[str, Place], dict[str, Place]]:
        token_to_move, input_places_sans_token = RemoveToken.with_highest_priority(input_places)
        if token_to_move is None:
            return input_places, output_places
        new_tokens = await asynchronous_expand_function(token_to_move.data)
        if checks:
            PetriNetCheck.tokens(new_tokens)
        output_places_with_tokens = AddTokens.to_output_places(
            new_tokens, destination_place_ids, output_places
        )
        return input_places_sans_token, output_places_with_tokens


class PetriNetOperations:

    def collect_incoming_places(net: PetriNet, transition: Transition, run_checks=True) -> dict[str, Place]:
        arcs_to_transition = (arc for arc in net.arcs_in if arc.transition_id == transition.id)
        arc_place_ids = tuple(arc.place_id for arc in arcs_to_transition)
        places = {
            place_id: place for place_id, place in net.places.items()
            if place.id in arc_place_ids  # place_id and place.id should be the same.
        }
        if run_checks:
            PetriNetCheck.places(places.values())
        return places

    def collect_outgoing_places(net: PetriNet, transition: Transition, run_checks=True) -> dict[str, Place]:
        arcs_from_transition = (arc for arc in net.arcs_out if arc.transition_id == transition.id)
        arc_place_ids = tuple(arc.place_id for arc in arcs_from_transition)
        places = {
            place_id: place for place_id, place in net.places.items()
            if place.id in arc_place_ids  # place_id and place.id should be the same.
        }
        if run_checks:
            PetriNetCheck.places(places.values())
        return places

    def transition_priorities(petri_net: PetriNet) -> dict[str, int]:
        """Use the transition_function associated with each transition to calculate its priority."""
        priorities = {}
        for transition in petri_net.transitions.values():
            if transition.priority_function is not None:
                priority = transition.priority_function(
                    PetriNetOperations.collect_incoming_places(petri_net, transition),
                    PetriNetOperations.collect_outgoing_places(petri_net, transition),
                )
                priorities[transition.id] = priority
        # Return an ordered dictionary sorted by priority values.
        return dict(sorted(priorities.items(), key=lambda item: item[1]))

    def prepare_transition_firing(
        net: PetriNet,
        transition_selection_function: Callable[[PetriNet], Optional[Transition]],
        run_checks=True,
    ) -> tuple[Transition, dict[str, Place], dict[str, Place]]:
        transition = transition_selection_function(net)
        if transition is None:  # No transition to fire so the petri net remains unchanged.
            return None, None, None
        incoming_places = PetriNetOperations.collect_incoming_places(net, transition, run_checks=run_checks)
        outgoing_places = PetriNetOperations.collect_outgoing_places(net, transition, run_checks=run_checks)
        if transition.maximum_firings is not None and transition.firings_count >= transition.maximum_firings:
            raise TransitionFiringLimitExceeded(f"Transition {transition.id} has exceeded its maximum firings limit.")
        return transition, incoming_places, outgoing_places

    def updated_net(
        petri_net: PetriNet,
        transition: Transition,
        new_incoming_places: dict[str, Place],
        new_outgoing_places: dict[str, Place],
    ) -> PetriNet:
        net = deepcopy(petri_net)
        new_transition = deepcopy(transition)
        new_transition.firings_count += 1
        net.transitions[transition.id] = new_transition
        # Update incoming places
        for place_id, place in new_incoming_places.items():
            net.places[place_id] = place
        # Update outgoing places.
        # NOTE: This could overwrite the incoming places if the same place is in both incoming and outgoing places.
        for place_id, place in new_outgoing_places.items():
            net.places[place_id] = place
        return net


class SyncPetriNet:

    def step(
        petri_net: PetriNet,
        transition_selection_function: Callable[[PetriNet], Optional[Transition]],
        run_checks=True,
    ) -> tuple[PetriNet, bool]:  # The boolean indicates whether a transition was fired.
        net = deepcopy(petri_net)
        transition, incoming_places, outgoing_places = PetriNetOperations.prepare_transition_firing(
            net, transition_selection_function, run_checks=run_checks
        )
        if transition is None:  # No transition to fire so the petri net remains unchanged.
            return net, False
        new_incoming_places, new_outgoing_places = transition.fire(incoming_places, outgoing_places)
        net = PetriNetOperations.updated_net(net, transition, new_incoming_places, new_outgoing_places)
        return net, True


class AsyncPetriNet:

    async def step(
        petri_net: PetriNet,
        transition_selection_function: Callable[[PetriNet], Optional[Transition]],
        run_checks=True,
    ) -> tuple[PetriNet, bool]:
        net = deepcopy(petri_net)
        transition, incoming_places, outgoing_places = PetriNetOperations.prepare_transition_firing(
            net, transition_selection_function, run_checks=run_checks
        )
        if transition is None:  # No transition to fire so the petri net remains unchanged.
            return net, False
        new_incoming_places, new_outgoing_places = await transition.fire(incoming_places, outgoing_places)
        net = PetriNetOperations.updated_net(net, transition, new_incoming_places, new_outgoing_places)
        return net, True
