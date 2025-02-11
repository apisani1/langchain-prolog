parent(john, bianca, mary).
parent(john, bianca, michael).
parent(peter, patricia, jennifer).
partner(X, Y) :- parent(X, Y, _).

hello():- write('Hello World'), nl.
