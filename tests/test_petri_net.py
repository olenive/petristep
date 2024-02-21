from petri_net import (
    AddTokens, PetriNetOperations, SelectToken, SyncFiringFunctions, Token, Place, Transition, ArcIn, ArcOut, PetriNet
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


class TestAddTokens:

    def test_to_output_places_with_one_to_many_token_split(self):
        tokens = (
            Token(id='0', data="ONE", priority=1),
            Token(id='1', data="TWO", priority=2),
            Token(id='2', data="ANOTHER TWO", priority=3),
            Token(id='3', data="THREE IS THE MAGIC NUMBER", priority=4),
        )
        output_places = {'from_one_to_many': Place(id='from_one_to_many', name='From comma delimited', tokens=())}
        expected_output_places = {
            'from_one_to_many': Place(id='from_one_to_many', name='From comma delimited', tokens=tokens)
        }
        result_output_places = AddTokens.to_output_places(
            tokens=tokens,
            destination_place_ids=("from_one_to_many",),
            output_places=output_places,
            checks=True,
        )
        assert result_output_places == expected_output_places

    def test_to_output_places_with_selecting_an_output_place(self):
        t0 = Token(id="1", data="ONE", priority=1)
        output_places = {
            "class_a": Place(id="class_a", name="Go Left", tokens=()),
            "class_b": Place(id="class_b", name="Go Down", tokens=()),
            "class_c": Place(id="class_c", name="Go Right", tokens=()),
        }
        expected_output_places = {
            "class_a": Place(id="class_a", name="Go Left", tokens=()),
            "class_b": Place(id="class_b", name="Go Down", tokens=()),
            "class_c": Place(id="class_c", name="Go Right", tokens=(t0,)),
        }
        result_output_places = AddTokens.to_output_places(
            (t0,), ("class_c",), output_places
        )
        assert result_output_places == expected_output_places


class TestSyncFiringFunctions:

    def test_route_and_transform_highest_priority_token(self):

        def routing_function(token: Token) -> str:
            number_of_words = len(token.data.split(" "))
            if number_of_words <= 1:
                return "class_a"
            if number_of_words == 2:
                return "class_b"
            else:
                return "class_c"

        t0 = Token(id="1", data="ONE", priority=1)
        t1 = Token(id="2", data="TWO", priority=2)
        t2 = Token(id="2", data="ANOTHER TWO", priority=3)
        t3 = Token(id="3", data="THREE IS THE MAGIC NUMBER", priority=4)
        input_place = Place(
            id="to_many_tokens",
            name="From comma delimited",
            tokens=(t0, t1, t2, t3),
        )
        output_place_a = Place(id="class_a", name="Go Left", tokens=())
        output_place_b = Place(id="class_b", name="Go Down", tokens=())
        output_place_c = Place(id="class_c", name="Go Right", tokens=())
        # Expected input place after activating the firing function.
        expected_input_place_1 = {
            "to_many_tokens": Place(id="to_many_tokens", name="From comma delimited", tokens=(t0, t1, t2)),
        }
        expected_output_places_1 = {
            "class_a": Place(id="class_a", name="Go Left", tokens=()),
            "class_b": Place(id="class_b", name="Go Down", tokens=()),
            "class_c": Place(id="class_c", name="Go Right", tokens=(t3,)),
        }
        expected_input_place_2 = {
            "to_many_tokens": Place(id="to_many_tokens", name="From comma delimited", tokens=(t0, t1)),
        }
        expected_output_places_2 = {
            "class_a": Place(id="class_a", name="Go Left", tokens=()),
            "class_b": Place(id="class_b", name="Go Down", tokens=(t2,)),
            "class_c": Place(id="class_c", name="Go Right", tokens=(t3,)),
        }
        expected_input_place_3 = {
            "to_many_tokens": Place(id="to_many_tokens", name="From comma delimited", tokens=(t0,)),
        }
        expected_output_places_3 = {
            "class_a": Place(id="class_a", name="Go Left", tokens=(t1,)),
            "class_b": Place(id="class_b", name="Go Down", tokens=(t2,)),
            "class_c": Place(id="class_c", name="Go Right", tokens=(t3,)),
        }
        expected_input_place_4 = {
            "to_many_tokens": Place(id="to_many_tokens", name="From comma delimited", tokens=()),
        }
        expected_output_places_4 = {
            "class_a": Place(id="class_a", name="Go Left", tokens=(t1, t0)),
            "class_b": Place(id="class_b", name="Go Down", tokens=(t2,)),
            "class_c": Place(id="class_c", name="Go Right", tokens=(t3,)),
        }
        result_input_place_1, result_output_places_1 = SyncFiringFunctions.route_and_transform_highest_priority_token(
            input_places={input_place.id: input_place},
            output_places={p.id: p for p in (output_place_a, output_place_b, output_place_c)},
            routing_function=routing_function,
            transform_function=lambda x: x,
        )
        assert result_input_place_1 == expected_input_place_1
        assert result_output_places_1 == expected_output_places_1
        result_input_place_2, result_output_places_2 = SyncFiringFunctions.route_and_transform_highest_priority_token(
            input_places=result_input_place_1,
            output_places=result_output_places_1,
            routing_function=routing_function,
            transform_function=lambda x: x,
        )
        assert result_input_place_2 == expected_input_place_2
        assert result_output_places_2 == expected_output_places_2
        result_input_place_3, result_output_places_3 = SyncFiringFunctions.route_and_transform_highest_priority_token(
            input_places=result_input_place_2,
            output_places=result_output_places_2,
            routing_function=routing_function,
            transform_function=lambda x: x,
        )
        assert result_input_place_3 == expected_input_place_3
        assert result_output_places_3 == expected_output_places_3
        result_input_place_4, result_output_places_4 = SyncFiringFunctions.route_and_transform_highest_priority_token(
            input_places=result_input_place_3,
            output_places=result_output_places_3,
            routing_function=routing_function,
            transform_function=lambda x: x,
        )
        assert result_input_place_4 == expected_input_place_4
        assert result_output_places_4 == expected_output_places_4
