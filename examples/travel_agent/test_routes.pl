:- module(routes_tests, [
    run_tests/0,
    test_route/3          % +From, +To, +Options
]).

:- use_module(routes).

% Main test runner
run_tests :-
    format('~nRunning Route Planner Tests~n'),
    format('========================~n'),
    run_basic_tests,
    run_transport_type_tests,
    run_constraint_tests,
    run_combined_constraint_tests,
    run_edge_case_tests.

% Basic route finding tests
run_basic_tests :-
    format('~nBasic Route Tests:~n'),
    format('----------------~n'),
    % Direct routes
    test_route(london, paris, []),
    test_route(paris, rome, []),
    % Multi-stop routes
    test_route(london, rome, []),
    test_route(paris, lisbon, []),
    % Long routes
    test_route(london, athens, []).

% Transport type restriction tests
run_transport_type_tests :-
    format('~nTransport Type Tests:~n'),
    format('-------------------~n'),
    % Single transport type
    test_route(london, paris, [transport_type([train])]),
    test_route(paris, rome, [transport_type([plane])]),
    % Multiple transport types
    test_route(london, athens, [transport_type([plane, train])]),
    test_route(paris, lisbon, [transport_type([train, plane])]),
    % All transport types
    test_route(rome, athens, [transport_type([ferry, plane, train])]).

% Constraint tests
run_constraint_tests :-
    format('~nConstraint Tests:~n'),
    format('----------------~n'),
    % Time constraints
    test_route(london, athens, [max_time(8)]),
    test_route(paris, lisbon, [max_time(5)]),
    % Cost constraints
    test_route(london, rome, [max_cost(400)]),
    test_route(paris, athens, [max_cost(300)]),
    % Changes constraints
    test_route(london, athens, [max_changes(2)]),
    test_route(paris, lisbon, [max_changes(1)]).

% Combined constraint tests
run_combined_constraint_tests :-
    format('~nCombined Constraint Tests:~n'),
    format('------------------------~n'),
    % Time and transport type
    test_route(london, paris, [max_time(3), transport_type(train)]),
    % Cost and transport type
    test_route(paris, rome, [max_cost(200), transport_type(plane)]),
    % Time, cost and changes
    test_route(london, athens, [max_time(10), max_cost(500), max_changes(2)]),
    % All constraints
    test_route(paris, lisbon, [
        max_time(8),
        max_cost(400),
        max_changes(2),
        transport_type(train)
    ]).

% Edge case tests
run_edge_case_tests :-
    format('~nEdge Case Tests:~n'),
    format('---------------~n'),
    % Non-existent direct routes
    test_route(london, lisbon, []),
    % Impossible constraints
    test_route(london, athens, [max_time(2)]),
    test_route(paris, lisbon, [max_cost(100)]),
    % Conflicting constraints
    test_route(london, rome, [max_time(3), transport_type(train)]).

% Test helper predicate
test_route(From, To, Options) :-
    format('~nTesting route: ~w to ~w~n', [From, To]),
    format('Options: ~w~n', [Options]),

    % Test all routes
    format('All routes:~n'),
    (   query_route(all, From, To, Options, AllRoutes)
    ->  print_routes(AllRoutes)
    ;   format('No routes found~n')
    ),

    % Test fastest route
    format('~nFastest route:~n'),
    (   query_route(fastest, From, To, Options, [FastestRoute])
    ->  print_route(FastestRoute)
    ;   format('No fastest route found~n')
    ),

    % Test cheapest route
    format('~nCheapest route:~n'),
    (   query_route(cheapest, From, To, Options, [CheapestRoute])
    ->  print_route(CheapestRoute)
    ;   format('No cheapest route found~n')
    ),

    % Print statistics
    route_stats(From, To),
    format('~n').

% Helper predicates for printing
print_routes([]).
print_routes([Route|Rest]) :-
    print_route(Route),
    print_routes(Rest).

print_route(Dict) :-
    format('Route: ~w~n', [Dict.get(route)]),
    format('Time: ~2f hours~n', [Dict.get(time)]),
    format('Cost: €~2f~n', [Dict.get(cost)]),
    format('Transport:~n'),
    forall(
        member(T, Dict.get(transport)),
        format('  - ~w: ~2f hours, €~2f~n',
               [T.get(type), T.get(time), T.get(cost)])
    ),
    format('~n').
