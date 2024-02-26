A minimalistic, Petri Net inspired, tool for data processing.

A Petri Net consists of Place nodes connected via Arcs to Transition nodes.
Tokens in each Place nodes hold data to be processed.
When a Transition fires, tokens in the input and output Places are updated according to a user defined function.
Another user defined function is used to determine the next transition to fire.

The goal is to help the user structure their data processing pipelines and make them extensible.
See the `examples` directory for how this can be used.
Note, this is not intended to a be a general purpose Petri Net simulator.

## When not to use this
If your data processing can be composed from pure function calls, you probably don't want to use this.
1. There is considerable overhead in setting up the Petri net.
2. Operations on the Petri Net produce complex mutable state.
The Petri Net formalism is powerful and should be used with care. Cycles, deadlocks and infinite loops are all possible and can be difficult to debug.

## When to use this
You may want to use this if you have to deal with a complex stateful processes.
Petri Nets lend themselves to visualisation and can be used to help structure complex data processing pipelines.
If the outcomes of individual data processing steps are not easily predictable or not deterministic, the Petri Net structure can encode how different cases are handled and how the order of processing is determined.
The formalism of Tokens, Places and Transitions may be helpful in creating interfaces between different stages of the process.
Such interfaces can compartmentalise data transformation steps making it easier to reason about the overall process.
I have found this to be useful for a process that requires a lot of calls to external resources with data taking possible paths depending on the response from those resources.


# Example


# Concepts

## Uniqunes

Place and Transition nodes must be unique.

Tokens don't need to be unique(???)

## Transition Priority
You can provide your own transition selection function or use one of the library functions.

Each transition can in turn have a priority function associated with it. When using library functions the transition for which the priority is computed to be the highest will be selected to fire next.
*** If a transition priority is computed to be zero, the transition does not fire ***


## Arc Direction
Arcs between Places and Transitions can be either input (ArcIn) or output arcs (ArcOut). This is used to help structure the Petri net. However, given that transitions can call arbitrary functions and affect both the input and output Places, information can flow in both directions. This is important to note because it means that infinite loops or futile cycles are possible.

TODO: explain types and IDs and which IDs need to be unique.
TODO: Add example graph PNGs
