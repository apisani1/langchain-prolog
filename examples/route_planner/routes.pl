:- module(routes, [
    query_route/5,          % Main interface
    route_stats/2           % Route statistics
]).

% Transport connections with time (hours), cost (euros), and transport type
connection(london, paris, transport(train, 2.5, 150)).
connection(london, paris, transport(plane, 1.5, 200)).
connection(paris, rome, transport(plane, 2, 180)).
connection(paris, barcelona, transport(plane, 1.5, 120)).
connection(paris, madrid, transport(train, 2, 150)).
connection(barcelona, madrid, transport(train, 3, 80)).
connection(madrid, lisbon, transport(train, 4, 90)).
connection(rome, athens, transport(ferry, 8, 120)).
connection(rome, athens, transport(plane, 1.5, 160)).
connection(barcelona, rome, transport(plane, 2, 140)).

% Bidirectional connections. This is optional.
valid_connection(A, B, Transport) :-
    (   connection(A, B, Transport)
    ;   connection(B, A, Transport)
    ).

% Query type definitions
valid_query_type(all).        % All routes
valid_query_type(fastest).    % Fastest route only
valid_query_type(cheapest).   % Cheapest route only

% Main interface predicate
query_route(QueryType, From, To, Options, Results) :-
    must_be(atom, QueryType),
    must_be(atom, From),
    must_be(atom, To),
    must_be(list, Options),

    % Validate query type
    (   valid_query_type(QueryType)
    ->  true
    ;   throw(error(invalid_query_type(QueryType), _))
    ),

    % Execute query based on type
    execute_query(QueryType, From, To, Options, Results).

% Execute different types of queries
execute_query(QueryType, From, To, Options, Results) :-
    findall(
        Dict,
        (   route(From, To, Route, details(Time, Cost, Transport)),
            apply_options(Options, Time, Cost, Transport),
            maplist(transport_to_dict, Transport, TransportList),
            Dict = _{
                'route': Route,
                'time': Time,
                'cost': Cost,
                'transport': TransportList
            }
        ),
        AllRoutes
    ),
    % Select routes based on query type
    select_routes(QueryType, AllRoutes, Results).

% Select routes based on query type
select_routes(all, [Route|Rest], [Route|Rest]).
select_routes(fastest, Routes, [FastestRoute]) :-
    find_fastest_route(Routes, FastestRoute).
select_routes(cheapest, Routes, [CheapestRoute]) :-
    find_cheapest_route(Routes, CheapestRoute).

% Find fastest route
find_fastest_route([Route|Rest], FastestRoute) :-
    Route.get(time) = Time,
    find_fastest_route(Rest, Time, Route, FastestRoute).

find_fastest_route([], _, FastestSoFar, FastestSoFar).
find_fastest_route([Route|Rest], MinTime, CurrentBest, FastestRoute) :-
    Route.get(time) = Time,
    (   Time < MinTime
    ->  find_fastest_route(Rest, Time, Route, FastestRoute)
    ;   find_fastest_route(Rest, MinTime, CurrentBest, FastestRoute)
    ).

% Find cheapest route
find_cheapest_route([Route|Rest], CheapestRoute) :-
    Route.get(cost) = Cost,
    find_cheapest_route(Rest, Cost, Route, CheapestRoute).

find_cheapest_route([], _, CheapestSoFar, CheapestSoFar).
find_cheapest_route([Route|Rest], MinCost, CurrentBest, CheapestRoute) :-
    Route.get(cost) = Cost,
    (   Cost < MinCost
    ->  find_cheapest_route(Rest, Cost, Route, CheapestRoute)
    ;   find_cheapest_route(Rest, MinCost, CurrentBest, CheapestRoute)
    ).

% Route finding with constraints
route(From, To, Route, Details) :-
    find_route(From, To, [From], Route, [], Details).

% Base case: direct connection
find_route(From, To, _, [From,To], TransportList,
          details(Time, Cost, FinalTransport)) :-
    valid_connection(From, To, transport(Type, Time, Cost)),
    append(TransportList, [transport(Type, Time, Cost)], FinalTransport).

% Recursive case with cycle detection
find_route(From, To, Visited, [From|Route], AccTransport,
          details(TotalTime, TotalCost, FinalTransport)) :-
    valid_connection(From, Next, transport(Type, Time, Cost)),
    \+ member(Next, Visited),  % Prevent cycles
    \+ member(To, Visited),  % Prevent redudant paths
    length(Visited, Len),
    Len < 5,  % Limit path length to prevent excessive searching
    append(AccTransport, [transport(Type, Time, Cost)], NewTransport),
    find_route(Next, To, [Next|Visited], Route, NewTransport,
              details(RestTime, RestCost, FinalTransport)),
    TotalTime is Time + RestTime,
    TotalCost is Cost + RestCost.

% Apply filtering options
apply_options([], _, _, _) :- !.
apply_options(Options, Time, Cost, Transport) :-
    % Time constraint
    \+ (
        member(max_time(MaxTime), Options),
        Time > MaxTime
    ),
    % Cost constraint
    \+ (
        member(max_cost(MaxCost), Options),
        Cost > MaxCost
    ),
    % Changes constraint
    \+ (
        member(max_changes(MaxChanges), Options),
        length(Transport, Changes),
        Changes > MaxChanges + 1
    ),
    % Transport type constraint
    \+ (
        member(transport_type(PreferredTypeList), Options),
        has_nonpreferred_transport_type(Transport, PreferredTypeList)
    ).

% Helper predicate to check if route has required transport type
has_nonpreferred_transport_type(Transport, PreferredTypeList) :-
    member(transport(TransportType, _, _), Transport),
    \+ member(TransportType, PreferredTypeList).

% Convert transport term to dict
transport_to_dict(transport(Type, Time, Cost), Dict) :-
    Dict = _{
        'type': Type,
        'time': Time,
        'cost': Cost
    }.

% Route statistics
route_stats(From, To) :-
    findall(Details, route(From, To, _, Details), AllDetails),
    AllDetails \= [],
    findall(Time, member(details(Time,_,_), AllDetails), Times),
    findall(Cost, member(details(_,Cost,_), AllDetails), Costs),
    min_list(Times, MinTime),
    max_list(Times, MaxTime),
    sum_list(Times, TotalTime),
    length(Times, Count),
    AvgTime is TotalTime / Count,
    min_list(Costs, MinCost),
    max_list(Costs, MaxCost),
    sum_list(Costs, TotalCost),
    AvgCost is TotalCost / Count,
    format('~nRoute Statistics:~n'),
    format('Number of routes: ~w~n', [Count]),
    format('Time range: ~2f - ~2f hours (avg: ~2f)~n',
           [MinTime, MaxTime, AvgTime]),
    format('Cost range: €~2f - €~2f (avg: €~2f)~n',
           [MinCost, MaxCost, AvgCost]).
