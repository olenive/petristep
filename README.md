A minimalistic, Petri Net inspired, tool for data processing.

A Petri Net consists of Place nodes connected via Arcs to Transition nodes.
Tokens in each Place nodes hold data to be processed.
When a Transition fires, tokens in the input and output Places are updated according to a user defined function.
Another user defined function is used to determine the next transition to fire.

The goal is to help the user structure their data processing pipelines and make them extensible.
See the `examples` directory for how this can be used.
Note, this is not intended to a be a general purpose Petri Net simulator.
Note, there are no built in safeguards against infinite loops or deadlocks or problematic updates to both input and output Places.


TODO: explain types and IDs and which IDs need to be unique.
