from petri_net import PetriNet


class PrintPetriNet:

    def places(net: PetriNet) -> None:
        print("Places:")
        for _, p in net.places.items():
            print(f"  {p.id}: {p.name}")

    def places_and_tokens(net: PetriNet) -> None:
        print("Places and Tokens:")
        for _, p in net.places.items():
            print(f"  {p.id}: {p.name}")
            for t in p.tokens:
                print(f"    {t.id}: {t.data}")
