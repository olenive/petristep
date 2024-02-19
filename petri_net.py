import asyncio
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Callable


@dataclass
class Token:
    id: str
    data: Optional[Any]
    priority_function: Callable[[Any], int] = lambda _: 0


@dataclass
class Place:
    id: str
    name: Optional[str]
    tokens: Iterable[Token]


@dataclass
class Transition:
    id: str
    name: Optional[str]
    fire: Callable[[dict[str, Place], dict[str, Place]], tuple[dict[str, Place], dict[str, Place]]]
    maximum_firings: Optional[int] = 1
    firings_count: int = 0
    priority_function: Optional[Callable[[dict[str, Place], dict[str, Place]], int]] = None


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


class Pick:

    def out_token_with_highest_priority(places: dict[str, Place]) -> tuple[Token, dict[str, Place]]:
        tokens = (token for place in places.values() for token in place.tokens)
        tokens_with_priority = ((token, token.priority_function(token.data)) for token in tokens)
        sorted_by_priority = sorted(tokens_with_priority, key=lambda item: item[1], reverse=True)
        token = sorted_by_priority[0][0]
        places_sans_token = {
            place_id: Place(place.id, place.name, tuple(t for t in place.tokens if t != token))
            for place_id, place in places.items()
        }
        return token, places_sans_token


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

    def select_transition_using_priority_functions(net: PetriNet) -> Optional[Transition]:
        priorities = PetriNetOperations.transition_priorities(net)
        for transition_id, priority in priorities.items():
            if priority > 0:
                return net.transitions[transition_id]
        return None

    def prepare_transition_firing(
        net: PetriNet,
        transition_selection_function: Callable[[PetriNet], Optional[Transition]],
        run_checks=True,
    ) -> tuple[dict[str, Place], dict[str, Place]]:
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
