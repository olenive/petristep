from dataclasses import dataclass
from typing import Any, Iterable, Optional, Callable


@dataclass
class Token:
    id: str
    data: Optional[Any]


@dataclass
class Place:
    id: str
    name: Optional[str]
    tokens: Iterable[Token]


@dataclass
class Transition:
    id: str
    name: Optional[str]
    fire: Callable[[Iterable[Place], Iterable[Place]], tuple[Iterable[Place], Iterable[Place]]]
    maximum_firings: Optional[int] = 1
    firings_count: int = 0


@dataclass(frozen=True)
class ArcIn:
    place_id: str
    transition_id: str
    weight: int = 1


@dataclass(frozen=True)
class ArcOut:
    transition_id: str
    place_id: str
    weight: int = 1


@dataclass
class PetriNet:
    places: dict[str, Place]
    transitions: dict[str, Transition]
    arcs_in: set[ArcIn]
    arcs_out: set[ArcOut]


class TransitionFireingLimitExceeded(Exception):
    pass


class PetriNetOperations:

    def collect_incoming_places(net: PetriNet, transition: Transition) -> dict[str, Place]:
        arcs_to_transition = (arc for arc in net.arcs_in if arc.transition_id == transition.id)
        arc_place_ids = tuple(arc.place_id for arc in arcs_to_transition)
        return {
            place_id: place for place_id, place in net.places.items()
            if place.id in arc_place_ids  # place_id and place.id should be the same.
        }

    def collect_outgoing_places(net: PetriNet, transition: Transition) -> dict[str, Place]:
        arcs_from_transition = (arc for arc in net.arcs_out if arc.transition_id == transition.id)
        arc_place_ids = tuple(arc.place_id for arc in arcs_from_transition)
        return {
            place_id: place for place_id, place in net.places.items()
            if place.id in arc_place_ids  # place_id and place.id should be the same.
        }

    def step(
        net: PetriNet,
        transition_selection_function: Callable[[PetriNet], Optional[Transition]],
    ) -> tuple[PetriNet, bool]:  # The boolean indicates whether a transition was fired.
        # Select a transition to fire.
        transition = transition_selection_function(net)
        if transition is None:  # No transition to fire so the petri net remains unchanged.
            return net, False
        incoming_places = PetriNetOperations.collect_incoming_places(net, transition)
        outgoing_places = PetriNetOperations.collect_outgoing_places(net, transition)
        # Fire the transition.
        if transition.maximum_firings is not None and transition.firings_count >= transition.maximum_firings:
            raise TransitionFireingLimitExceeded(f"Transition {transition.id} has exceeded its maximum firings limit.")
        new_incoming_places, new_outgoing_places = transition.fire(incoming_places, outgoing_places)
        transition.firings_count += 1
        # Update incoming places
        for place_id, place in new_incoming_places.items():
            net.places[place_id] = place
        # Update outgoing places.
        # NOTE: This could overwrite the incoming places if the same place is in both incoming and outgoing places.
        for place_id, place in new_outgoing_places.items():
            net.places[place_id] = place
        return net, True
