from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Coroutine, Iterable, Optional, Callable, Union


@dataclass(frozen=True)
class Token:
    id: str
    data: Optional[Any]
    priority: int = 1
    summary_function: Optional[Callable[[Any], str]] = lambda data: data
    # The summary_function can be used for data-specific formatting.


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

    def selected_places_exist(selected_place_ids: tuple[str, ...], places: dict[str, Place]) -> None:
        for place_id in selected_place_ids:
            if place_id not in places:
                raise ValueError(f"Place \"{place_id}\" not found in selected places.")


class SelectToken:

    def total_count(places: dict[str, Place]) -> int:
        return sum(len(place.tokens) for place in places.values())

    def with_highest_priority(places: dict[str, Place]) -> Optional[Token]:
        tokens = tuple(token for place in places.values() for token in place.tokens)
        if len(tokens) == 0:
            return None
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
            out = dict()
            for place_id, place in output_places.items():
                if place_id in destination_place_ids:
                    out[place_id] = AddTokens.to_place(tokens, place, checks=checks)
                else:
                    out[place_id] = place
            if len(out) == 0 and len(tokens) > 0 and len(destination_place_ids) > 0:
                raise RuntimeError("Not expecting an empty output.")
            return out
        else:  # Add token to all output places.
            out = {
                place_id: AddTokens.to_place(tokens, place, checks=checks)
                for place_id, place in output_places.items()
            }
            if len(out) == 0 and len(tokens) > 0 and len(destination_place_ids) > 0:
                raise RuntimeError("Not expecting an empty output.")
            return out


class TransitionPriorityFunction:

    def _constant_if_any_input_tokens(input_places, _, value: int) -> int:
        if SelectToken.total_count(input_places) > 0:
            return value
        return 0

    def constant_if_any_input_tokens(value: int) -> Callable[[dict[str, Place], dict[str, Place]], int]:
        return lambda input_places, _: TransitionPriorityFunction._constant_if_any_input_tokens(input_places, _, value)

    def _equal_to_input_token_count(input_places, _) -> int:
        return SelectToken.total_count(input_places)

    def equal_to_input_token_count() -> Callable[[dict[str, Place], dict[str, Place]], int]:
        return lambda input_places, _: TransitionPriorityFunction._equal_to_input_token_count(input_places, _)


class SelectTransition:

    def using_priority_functions(net: PetriNet) -> Optional[Transition]:
        transitions_and_priorities: dict[str, int] = PetriNetOperations.transition_priorities(net)
        transition_id, priority = sorted(transitions_and_priorities.items(), key=lambda item: item[1])[-1]
        if priority <= 0:
            return None
        return net.transitions[transition_id]


class SyncFiringFunctions:

    def move_and_transform_highest_priority_token(
        input_places: dict[str, Place],
        output_places: dict[str, Place],
        transform_function: Callable[[Token], Token],
        checks=True,
    ) -> tuple[dict[str, Place], dict[str, Place]]:
        """Remove one token from the input places and make a corresponding token in the output places."""
        token_to_move, input_places_sans_token = RemoveToken.with_highest_priority(input_places)
        if token_to_move is None:
            return input_places, output_places
        if checks:
            PetriNetCheck.token(token_to_move)
        new_token = transform_function(token_to_move)
        if checks:
            PetriNetCheck.token(new_token)
        # new_token = Token(token_to_move.id, transformed_data)
        if new_token is None:
            return input_places, output_places
        if checks:
            PetriNetCheck.token(new_token)
        output_places_with_token = AddTokens.to_output_places(
            (new_token,),
            None,  # Output to all destinations.
            output_places
        )
        return input_places_sans_token, output_places_with_token

    def move_and_expand_highest_priority_token(
        input_places: dict[str, Place],
        output_places: dict[str, Place],
        expand_function: Callable[[Any], tuple[Token, ...]],
        checks=True,
    ) -> tuple[dict[str, Place], dict[str, Place]]:
        """Remove one token and make many tokens from it."""
        token_to_move, input_places_sans_token = RemoveToken.with_highest_priority(input_places)
        if token_to_move is None:
            return input_places, output_places
        if checks:
            PetriNetCheck.token(token_to_move)
        new_tokens = expand_function(token_to_move)
        if checks:
            PetriNetCheck.tokens(new_tokens)
        output_places_with_tokens = AddTokens.to_output_places(
            new_tokens,
            None,  # Output to all destinations.
            output_places,
        )
        return input_places_sans_token, output_places_with_tokens

    def route_and_transform_highest_priority_token(
        input_places: dict[str, Place],
        output_places: dict[str, Place],
        transform_function: Callable[[Token], Token],
        routing_function: Callable[[Token], tuple[str, ...]],
        checks=True,
    ) -> tuple[dict[str, Place], dict[str, Place]]:
        """Path a token to a destination place and transform the token."""
        token_to_move, input_places_sans_token = RemoveToken.with_highest_priority(input_places)
        if token_to_move is None:
            return input_places, output_places
        if checks:
            PetriNetCheck.token(token_to_move)
        new_token: Token = transform_function(token_to_move)
        if new_token is None:
            return input_places, output_places
        if checks:
            PetriNetCheck.token(new_token)
        selected_place_ids: tuple[str, ...] = routing_function(new_token)
        PetriNetCheck.selected_places_exist(selected_place_ids, output_places)
        if checks:
            if not isinstance(selected_place_ids, tuple):
                raise ValueError(f"routing_function should return a tuple, not {type(selected_place_ids)}.")
            for place_id in selected_place_ids:
                if not isinstance(place_id, str):
                    raise ValueError(f"routing_function should return a tuple of str, not {type(place_id)}.")
        output_places_with_token = AddTokens.to_output_places(
            (new_token,), selected_place_ids, output_places
        )
        return input_places_sans_token, output_places_with_token


class AsyncFiringFunctions:

    async def move_and_transform_highest_priority_token(
        input_places: dict[str, Place],
        output_places: dict[str, Place],
        transform_function: Callable[[Token], Token],
        checks=True,
    ) -> tuple[dict[str, Place], dict[str, Place]]:
        token_to_move, input_places_sans_token = RemoveToken.with_highest_priority(input_places)
        if token_to_move is None:
            return input_places, output_places
        if checks:
            PetriNetCheck.token(token_to_move)
        new_token = await transform_function(token_to_move)
        if checks:
            PetriNetCheck.token(new_token)
        if new_token is None:
            return input_places_sans_token, output_places
        if checks:
            PetriNetCheck.token(new_token)
        output_places_with_token: dict[str, Place] = AddTokens.to_output_places(
            tokens=(new_token,),
            destination_place_ids=None,  # Output to all destinations.
            output_places=output_places,
        )
        return input_places_sans_token, output_places_with_token

    async def move_and_expand_highest_priority_token(
        input_places: dict[str, Place],
        output_places: dict[str, Place],
        expand_function: Callable[[Any], Coroutine[Any, Any, tuple[Token, ...]]],
        checks=True,
    ) -> tuple[dict[str, Place], dict[str, Place]]:
        token_to_move, input_places_sans_token = RemoveToken.with_highest_priority(input_places)
        if token_to_move is None:
            return input_places, output_places
        new_tokens = await expand_function(token_to_move)
        if checks:
            PetriNetCheck.tokens(new_tokens)
        output_places_with_tokens = AddTokens.to_output_places(
            new_tokens,
            None,  # Output to all destinations.
            output_places,
        )
        return input_places_sans_token, output_places_with_tokens

    async def route_and_transform_highest_priority_token(
        input_places: dict[str, Place],
        output_places: dict[str, Place],
        transform_function: Callable[[Token], Token],
        routing_function: Callable[[Token], tuple[str, ...]],
        checks=True,
    ) -> tuple[dict[str, Place], dict[str, Place]]:
        """Path a token to a destination place and transform the token."""
        token_to_move, input_places_sans_token = RemoveToken.with_highest_priority(input_places)
        if token_to_move is None:
            return input_places, output_places
        if checks:
            PetriNetCheck.token(token_to_move)
        new_token = await transform_function(token_to_move)
        if new_token is None:
            return input_places, output_places
        if checks:
            PetriNetCheck.token(new_token)
        selected_place_ids: tuple[str, ...] = await routing_function(new_token)
        PetriNetCheck.selected_places_exist(selected_place_ids, output_places)
        if checks:
            if not isinstance(selected_place_ids, tuple):
                raise ValueError(f"routing_function should return a tuple, not {type(selected_place_ids)}.")
            for place_id in selected_place_ids:
                if not isinstance(place_id, str):
                    raise ValueError(f"routing_function should return a tuple of str, not {type(place_id)}.")
        output_places_with_token = AddTokens.to_output_places(
            (new_token,), selected_place_ids, output_places
        )
        return input_places_sans_token, output_places_with_token


class TransitionMaking:

    def priority_function_from_args(
        priority: Optional[int],
        priority_function: Optional[Callable[[dict[str, Place], dict[str, Place]], int]],
    ) -> Callable[[dict[str, Place], dict[str, Place]], int]:
        if priority is not None and priority_function is not None:
            raise ValueError("Only one of priority or priority_function can be provided.")
        if priority is None and priority_function is None:
            raise ValueError("Either priority or priority_function must be provided.")
        if priority is not None:
            return TransitionPriorityFunction.constant_if_any_input_tokens(priority)
        return priority_function


class SyncTransition:
    """Wrappers to reduce the amount of syntax needed when declaring Transitions."""

    def flip(
        id: str,
        transform_function: Callable[[Token], Token],
        maximum_firings: Optional[int] = 1,
        priority: Optional[int] = None,
        priority_function: Optional[Callable[[dict[str, Place], dict[str, Place]], int]] = None,
        name: Optional[str] = None,
    ) -> Transition:
        """Remove a token from an input place and add a token to the output place, transforming the data."""
        return Transition(
            id=id,
            name=name if name is not None else id,
            fire=lambda input_places, output_places: SyncFiringFunctions.move_and_transform_highest_priority_token(
                input_places, output_places, transform_function=transform_function,
            ),
            maximum_firings=maximum_firings,
            priority_function=TransitionMaking.priority_function_from_args(priority, priority_function),
        )

    def fork(
        id: str,
        transform_function: Callable[[Token], Token],
        routing_function: Callable[[Token], tuple[str, ...]],
        maximum_firings: Optional[int] = 1,
        priority: Optional[int] = None,
        priority_function: Optional[Callable[[dict[str, Place], dict[str, Place]], int]] = None,
        name: Optional[str] = None,
    ) -> Transition:
        """Remove a token from the input places, transform data, and add tokens to output places.

        The routing function is applied to the transformed token to determine which output places to add tokens to.
        """
        return Transition(
            id=id,
            name=name if name is not None else id,
            fire=lambda input_places, output_places: SyncFiringFunctions.route_and_transform_highest_priority_token(
                input_places, output_places, transform_function=transform_function, routing_function=routing_function,
            ),
            maximum_firings=maximum_firings,
            priority_function=TransitionMaking.priority_function_from_args(priority, priority_function),
        )

    def expand(
        id: str,
        expand_function: Callable[[Token], tuple[Token, ...]],
        maximum_firings: Optional[int] = 1,
        priority: Optional[int] = None,
        priority_function: Optional[Callable[[dict[str, Place], dict[str, Place]], int]] = None,
        name: Optional[str] = None,
    ) -> Transition:
        """Remove a token from the input places and add multiple tokens to the output places."""
        return Transition(
            id=id,
            name=name if name is not None else id,
            fire=lambda input_places, output_places: SyncFiringFunctions.move_and_expand_highest_priority_token(
                input_places, output_places, expand_function=expand_function,
            ),
            maximum_firings=maximum_firings,
            priority_function=TransitionMaking.priority_function_from_args(priority, priority_function),
        )


class AsyncTransition:
    """Wrappers to reduce the amount of syntax needed when declaring Transitions."""

    def flip(
        id: str,
        async_transform_function: Callable[[Token], Token],
        maximum_firings: Optional[int] = 1,
        priority: Optional[int] = None,
        priority_function: Optional[Callable[[dict[str, Place], dict[str, Place]], int]] = None,
        name: Optional[str] = None,
    ) -> Transition:
        """Remove a token from an input place and add a token to the output place, transforming the data."""

        async def async_fire(
            input_places: dict[str, Place],
            output_places: dict[str, Place]
        ) -> tuple[dict[str, Place], dict[str, Place]]:
            return await AsyncFiringFunctions.move_and_transform_highest_priority_token(
                input_places, output_places, transform_function=async_transform_function,
            )

        return Transition(
            id=id,
            name=name if name is not None else id,
            fire=async_fire,
            maximum_firings=maximum_firings,
            priority_function=TransitionMaking.priority_function_from_args(priority, priority_function),
        )

    def fork(
        id: str,
        async_transform_function: Callable[[Token], Token],
        async_routing_function: Callable[[Token], tuple[str, ...]],
        maximum_firings: Optional[int] = 1,
        priority: Optional[int] = None,
        priority_function: Optional[Callable[[dict[str, Place], dict[str, Place]], int]] = None,
        name: Optional[str] = None,
    ) -> Transition:
        """Remove a token from the input places, transform data, and add tokens to output places.

        The routing function is applied to the transformed token to determine which output places to add tokens to.
        """

        async def async_fire(
            input_places: dict[str, Place],
            output_places: dict[str, Place]
        ) -> tuple[dict[str, Place], dict[str, Place]]:
            return await AsyncFiringFunctions.route_and_transform_highest_priority_token(
                input_places,
                output_places,
                transform_function=async_transform_function,
                routing_function=async_routing_function,
            )

        return Transition(
            id=id,
            name=name if name is not None else id,
            fire=async_fire,
            maximum_firings=maximum_firings,
            firings_count=0,
            priority_function=TransitionMaking.priority_function_from_args(priority, priority_function),
        )

    def expand(
        id: str,
        async_expand_function: Callable[[Token], Coroutine[Any, Any, tuple[Token, ...]]],
        maximum_firings: Optional[int] = 1,
        priority: Optional[int] = None,
        priority_function: Optional[Callable[[dict[str, Place], dict[str, Place]], int]] = None,
        name: Optional[str] = None,
    ) -> Transition:
        """Remove a token from the input places and add multiple tokens to the output places."""

        async def async_fire(
            input_places: dict[str, Place],
            output_places: dict[str, Place]
        ) -> tuple[dict[str, Place], dict[str, Place]]:
            return await AsyncFiringFunctions.move_and_expand_highest_priority_token(
                input_places, output_places, expand_function=async_expand_function,
            )

        return Transition(
            id=id,
            name=name if name is not None else id,
            fire=async_fire,
            maximum_firings=maximum_firings,
            firings_count=0,
            priority_function=TransitionMaking.priority_function_from_args(priority, priority_function),
        )


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
        # Check that the places exist.
        if run_checks:
            PetriNetCheck.selected_places_exist(arc_place_ids, net.places)
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
            raise TransitionFiringLimitExceeded(
                f"Transition {transition.id} has exceeded its maximum firings limit."
            )
        return transition, incoming_places, outgoing_places

    def update_net(
        petri_net: PetriNet,
        transition: Transition,
        new_incoming_places: dict[str, Place],
        new_outgoing_places: dict[str, Place],
    ) -> None:
        new_transition = deepcopy(transition)
        new_transition.firings_count += 1
        petri_net.transitions[transition.id] = new_transition
        # Update incoming places
        for place_id, place in new_incoming_places.items():
            petri_net.places[place_id] = place
        # Update outgoing places.
        # NOTE: This could overwrite the incoming places if the same place is in both incoming and outgoing places.
        for place_id, place in new_outgoing_places.items():
            petri_net.places[place_id] = place


class SyncPetriNet:

    def step(
        petri_net: PetriNet,
        transition_selection_function: Callable[[PetriNet], Optional[Transition]],
        run_checks=True,
        verbose=True,
    ) -> bool:  # The boolean indicates whether a transition was fired.
        transition, incoming_places, outgoing_places = PetriNetOperations.prepare_transition_firing(
            petri_net, transition_selection_function, run_checks=run_checks
        )
        if transition is None:  # No transition to fire so the petri net remains unchanged.
            return False
        new_incoming_places, new_outgoing_places = transition.fire(incoming_places, outgoing_places)
        if new_incoming_places == incoming_places and new_outgoing_places == outgoing_places:
            if verbose:
                print(f"Transition {transition.id} did not change the petri net.")
            return False
        PetriNetOperations.update_net(petri_net, transition, new_incoming_places, new_outgoing_places)
        return True


class AsyncPetriNet:

    async def step(
        petri_net: PetriNet,
        transition_selection_function: Callable[[PetriNet], Optional[Transition]],
        run_checks=True,
        verbose=True,
    ) -> bool:
        transition, incoming_places, outgoing_places = PetriNetOperations.prepare_transition_firing(
            petri_net, transition_selection_function, run_checks=run_checks
        )
        if verbose:
            if transition is not None:
                print(f"\nFiring Transition: {transition.name}")
        if transition is None:  # No transition to fire so the petri net remains unchanged.
            return False
        new_incoming_places, new_outgoing_places = await transition.fire(incoming_places, outgoing_places)
        if new_incoming_places == incoming_places and new_outgoing_places == outgoing_places:
            if verbose:
                print(f"Transition {transition.id} did not change the petri net.")
            return False
        PetriNetOperations.update_net(petri_net, transition, new_incoming_places, new_outgoing_places)
        return True


class New:

    def empty_place(id: str, name: Optional[str] = None) -> Place:
        return Place(
            id=id,
            name=name if name is not None else id,
            tokens=(),
        )

    def arc_out_and_empty_place(
        transition_id: str, place_id: str, place_name: Optional[str] = None
    ) -> tuple[ArcOut, Place]:
        return (ArcOut(transition_id, place_id), New.empty_place(place_id))

    def petri_net(
        nodes_and_edges: Iterable[Union[Place, Transition, ArcIn, ArcOut]],
        existing_net: Optional[PetriNet] = None,
    ) -> PetriNet:
        if existing_net is None:
            places = {part.id: part for part in nodes_and_edges if isinstance(part, Place)}
            transitions = {part.id: part for part in nodes_and_edges if isinstance(part, Transition)}
            arcs_in = {part for part in nodes_and_edges if isinstance(part, ArcIn)}
            arcs_out = {part for part in nodes_and_edges if isinstance(part, ArcOut)}
        else:
            cp = deepcopy(existing_net)
            places = {**cp.places, **{part.id: part for part in nodes_and_edges if isinstance(part, Place)}}
            transitions = {
                **cp.transitions, **{part.id: part for part in nodes_and_edges if isinstance(part, Transition)}
            }
            arcs_in = cp.arcs_in.union({part for part in nodes_and_edges if isinstance(part, ArcIn)})
            arcs_out = cp.arcs_out.union({part for part in nodes_and_edges if isinstance(part, ArcOut)})
        # Check places.
        for place in places.values():
            PetriNetCheck.place(place)
            PetriNetCheck.tokens(place.tokens)

        # Check arcs.
        for arc_in in arcs_in:
            if arc_in.place_id not in places:
                raise ValueError(f"ArcIn place_id \"{arc_in.place_id}\" not found in places.")
            if arc_in.transition_id not in transitions:
                raise ValueError(f"ArcIn transition_id \"{arc_in.transition_id}\" not found in transitions.")
        for arc_out in arcs_out:
            if arc_out.place_id not in places:
                raise ValueError(f"ArcOut place_id \"{arc_out.place_id}\" not found in places.")
            if arc_out.transition_id not in transitions:
                raise ValueError(f"ArcOut transition_id \"{arc_out.transition_id}\" not found in transitions.")

        return PetriNet(places, transitions, arcs_in, arcs_out)
