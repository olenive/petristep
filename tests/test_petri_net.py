from petri_net import (
    PetriNetOperations, Pick, Token, Place, Transition, ArcIn, ArcOut, PetriNet
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


class TestPick:

    def test_out_token_with_highest_priority(self):
        t0 = Token(id="t0", data="data0", priority_function=lambda data: 1)
        t1 = Token(id="t1", data="data1", priority_function=lambda data: 2)
        t2 = Token(id="t2", data="data2", priority_function=lambda data: 3)
        t3 = Token(id="t3", data="data3", priority_function=lambda data: 4)
        t4 = Token(id="t4", data="data4", priority_function=lambda data: 5)
        t5 = Token(id="t5", data="data5", priority_function=lambda data: 6)
        places = {
            "p0": Place(
                id="p0",
                name="Place 0",
                tokens=(t0, t1, t2),
            ),
            "p1": Place(
                id="p1",
                name="Place 1",
                tokens=(t3, t4, t5),
            ),
        }
        expected_places_sans_token = {
            "p0": Place(
                id="p0",
                name="Place 0",
                tokens=(t0, t1, t2),
            ),
            "p1": Place(
                id="p1",
                name="Place 1",
                tokens=(t3, t4),
            ),
        }
        picked_token, places_sans_token = Pick.out_token_with_highest_priority(places)
        assert picked_token == t5
        assert places_sans_token == expected_places_sans_token
