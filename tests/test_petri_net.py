from petri_net import (
    PetriNetOperations, Token, Place, Transition, ArcIn, ArcOut, PetriNet
)


class TestPetriNetOperations:

    def net_01():
        return PetriNet(
            places={p.id: p for p in (
                Place(id="p0", name="Place 0", tokens=(Token(id="t0", data="data0"),)),
                Place(id="p1", name="Place 1", tokens=(Token(id="t1", data="data1"),)),
                Place(id="p2", name="Place 2", tokens=(Token(id="t2", data="data2"),)),
            )},
            transitions={t.id: t for t in (
                Transition(
                    id="t0",
                    name="Transition 0",
                    fire=lambda input_places, output_places: (input_places, output_places),
                ),
                Transition(
                    id="t1",
                    name="Transition 1",
                    fire=lambda input_places, output_places: (input_places, output_places),
                ),
            )},
            arcs_in=(
                ArcIn(place_id="p0", transition_id="t0"),
                ArcIn(place_id="p1", transition_id="t1"),
                ArcIn(place_id="p2", transition_id="t1"),
            ),
            arcs_out=(
                ArcOut(transition_id="t0", place_id="p1"),
                ArcOut(transition_id="t1", place_id="p2"),
            ),
        )

    def test_collect_incoming_places(self):
        net = TestPetriNetOperations.net_01()
        transition = net.transitions["t1"]
        assert transition.id == "t1"
        incoming_places = PetriNetOperations.collect_incoming_places(net, transition)
        assert incoming_places == {"p1": net.places["p1"], "p2": net.places["p2"]}

    def test_collect_outgoing_places(self):
        net = TestPetriNetOperations.net_01()
        transition = net.transitions["t1"]
        assert transition.id == "t1"
        outgoing_places = PetriNetOperations.collect_outgoing_places(net, transition)
        assert outgoing_places == {"p2": net.places["p2"]}
