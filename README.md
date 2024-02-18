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
1. There is considerable overhead in setting up the Petri Net.
2. Operations on the Petri Net produce complex mutable state.
The Petri Net formalism is powerful and should be used with care. Cycles, deadlocks and infinite loops are all possible and can be difficult to debug.

## When to use this
You may want to use this if you have to deal with a complex stateful processes.
Petri Nets lend themselves to visualisation and can be used to help structure complex data processing pipelines.
If the outcomes of individual data processing steps are not easily predictable or not deterministic, the Petri Net structure can encode how different cases are handled and how the order of processing is determined.
The formalism of Tokens, Places and Transitions may be helpful in creating interfaces between different stages of the process.
Such interfaces can compartmentalise data transformation steps making it easier to reason about the overall process.



TODO: explain types and IDs and which IDs need to be unique.
