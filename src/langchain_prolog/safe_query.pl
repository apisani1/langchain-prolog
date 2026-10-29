% Query validation for langchain-prolog.
%
% Queries reach this library as text, and for PrologTool that text is written by an LLM, so it must never be
% handed to Prolog as-is: a goal such as shell/1 or assertz/1 would run with the privileges of the host process.
%
% prepare_query/6 therefore parses the text into a term, checks every goal in the term against a policy and
% returns the text re-generated from the checked term. Only that text is executed, so whatever the parser read
% is exactly what was checked.
%
% Policy: a goal may be a control construct, a predicate from the allow-list below, a predicate listed by the
% caller, or a predicate defined by a rules file that was loaded through register_rules/1. Predicates of a
% library that a rules file loads are not callable. Anything else (including every module-qualified goal and
% every unbound goal) is refused.

:- module(safe_query,
          [ prepare_query/7,
            register_rules/1
          ]).

:- dynamic rules_root/1.

%!  register_rules(+Spec) is det.
%
%   Mark a rules file, and the files it loads, as trusted to define predicates that queries may call.

register_rules(Spec) :-
    absolute_file_name(Spec, File, [file_type(prolog), access(read)]),
    (   rules_root(File)
    ->  true
    ;   assertz(rules_root(File))
    ).

%!  prepare_query(+Text, +Kind, +Name, +Arity, +Extra, -Status, -Message) is det.
%
%   Status is ok and Message the text to execute, or Status is syntax or denied and Message says why.
%
%   Kind describes the shape the query must have:
%     - any:   any goal that passes the policy;
%     - exact: a single call of Name/Arity;
%     - call:  a single call of Name with any number of arguments.
%   Extra is a list of Name/Arity terms (as text) that are allowed in addition to the allow-list.

prepare_query(Text, Kind, Name, Arity, Extra, Status, Message) :-
    catch(check(Text, Kind, Name, Arity, Extra, Canonical), E, true),
    (   var(E)
    ->  Status = ok,
        Message = Canonical
    ;   E = denied(Reason)
    ->  Status = denied,
        Message = Reason
    ;   Status = syntax,
        syntax_message(E, Message)
    ).

syntax_message(error(syntax_error(What), _), Message) :-
    !,
    format(string(Message), 'Syntax error: ~w', [What]).
syntax_message(E, Message) :-
    format(string(Message), '~p', [E]).

check(Text, Kind, Name, Arity, Extra, Canonical) :-
    parse_query(Text, Goal, Bindings),
    parse_extra(Extra, Allowed),
    check_shape(Kind, Name, Arity, Goal),
    check_goal(Goal, Allowed),
    format(string(Canonical), '~W',
           [ Goal,
             [ quoted(true),
               ignore_ops(false),
               numbervars(false),
               portray(false),
               spacing(next_argument),
               variable_names(Bindings)
             ]
           ]).

% Read exactly one term. Text after the first term (a second clause, say) is refused, not ignored.
parse_query(Text, Goal, Bindings) :-
    end_clause(Text, Clause),
    setup_call_cleanup(
        open_string(Clause, In),
        (   read_term(In, Goal, [variable_names(Bindings)]),
            read_term(In, Rest, []),
            (   Rest == end_of_file
            ->  true
            ;   deny("Only one query is allowed")
            )
        ),
        close(In)).

% Queries are written without the closing full stop that read_term/2 wants; add it, but do not double a
% full stop the caller already wrote. A full stop that follows a symbol character belongs to an atom (=..).
end_clause(Text, Clause) :-
    split_string(Text, "", " \t\r\n", [Trimmed]),
    (   string_concat(Head, ".", Trimmed),
        \+ ( string_length(Head, Len), Len > 0,
             sub_string(Head, _, 1, 0, Last),
             string_code(1, Last, Code),
             memberchk(Code, `#$&*+-./:<=>?@^~\\`) )
    ->  Body = Head
    ;   Body = Trimmed
    ),
    string_concat(Body, " .", Clause).

parse_extra(Extra, Allowed) :-
    maplist(parse_indicator, Extra, Allowed).

parse_indicator(Text, Name/Arity) :-
    term_to_atom(Term, Text),
    (   Term = Name/Arity, atom(Name), integer(Arity), Arity >= 0
    ->  true
    ;   deny("Allowed predicates must have the form name/arity")
    ).

check_shape(any, _, _, _) :- !.
check_shape(exact, Name, Arity, Goal) :-
    !,
    atom_string(Atom, Name),
    (   callable(Goal), goal_name_arity(Goal, Atom, Arity)
    ->  true
    ;   deny_format("Query must be a single call of ~w/~w", [Atom, Arity])
    ).
check_shape(call, Name, _, Goal) :-
    atom_string(Atom, Name),
    (   callable(Goal), goal_name_arity(Goal, Atom, _)
    ->  true
    ;   deny_format("Query must be a single call of ~w", [Atom])
    ).

                /*******************************
                *            POLICY            *
                *******************************/

check_goal(Goal, _) :-
    var(Goal),
    !,
    deny("Unbound goals are not allowed").
check_goal(_:_, _) :-
    !,
    deny("Module-qualified goals are not allowed").
check_goal(Goal, _) :-
    \+ callable(Goal),
    !,
    deny("Query is not callable").
check_goal(Goal, Allowed) :-
    sub_goals(Goal, Subs),
    !,
    maplist(check_sub(Allowed), Subs).
check_goal(Goal, Allowed) :-
    goal_name_arity(Goal, Name, Arity),
    (   safe(Name/Arity)
    ;   memberchk(Name/Arity, Allowed)
    ;   user_predicate(Goal)
    ),
    !.
check_goal(Goal, _) :-
    goal_name_arity(Goal, Name, Arity),
    same_name(Name, Arity, Others),
    (   Others == []
    ->  deny_format("Predicate ~w/~w is not allowed in queries", [Name, Arity])
    ;   maplist(indicator_text, Others, Texts),
        atomic_list_concat(Texts, ', ', Hint),
        deny_format("Predicate ~w/~w is not allowed in queries, but ~w is defined", [Name, Arity, Hint])
    ).

indicator_text(Name/Arity, Text) :-
    format(atom(Text), '~w/~w', [Name, Arity]).

%   same_name(+Name, +Arity, -Others): predicates from the rules files called Name, with another arity.
%   A query that gets the arity wrong is told which arities exist, so that it can correct itself.
same_name(Name, Arity, Others) :-
    findall(Name/A,
            ( current_predicate(Name, user:Head),
              goal_name_arity(Head, Name, A),
              A \== Arity,
              user_predicate(Head)
            ),
            Found),
    sort(Found, Others).

%   hello() is a compound with no arguments, which functor/3 refuses to describe.
goal_name_arity(Goal, Name, Arity) :-
    (   compound(Goal)
    ->  compound_name_arity(Goal, Name, Arity)
    ;   functor(Goal, Name, Arity)
    ).

check_sub(Allowed, Goal) :-
    check_goal(Goal, Allowed).

%   sub_goals(+Goal, -Goals): Goal is a control construct or a meta call; Goals are the goals it runs.
sub_goals((A, B), [A, B]).
sub_goals((A ; B), [A, B]).
sub_goals((A -> B), [A, B]).
sub_goals((A *-> B), [A, B]).
sub_goals(\+ A, [A]).
sub_goals(once(A), [A]).
sub_goals(ignore(A), [A]).
sub_goals(forall(A, B), [A, B]).
sub_goals(findall(_, G, _), [G]).
sub_goals(findall(_, G, _, _), [G]).
sub_goals(aggregate_all(_, G, _), [G]).
sub_goals(aggregate_all(_, _, G, _), [G]).
sub_goals(bagof(_, G0, _), [G]) :- strip_carets(G0, G).
sub_goals(setof(_, G0, _), [G]) :- strip_carets(G0, G).

strip_carets(G, G) :- var(G), !.
strip_carets(_^G0, G) :- !, strip_carets(G0, G).
strip_carets(G, G).

%   Predicates that only compute: none of them runs a goal, touches the file system, the OS or the database.
safe(true/0).
safe(fail/0).
safe(false/0).
safe((!)/0).
safe((=)/2).
safe((\=)/2).
safe((==)/2).
safe((\==)/2).
safe((@<)/2).
safe((@>)/2).
safe((@=<)/2).
safe((@>=)/2).
safe(compare/3).
safe(functor/3).
safe(arg/3).
safe((=..)/2).
safe(copy_term/2).
safe((<)/2).
safe((>)/2).
safe((=<)/2).
safe((>=)/2).
safe((=:=)/2).
safe((=\=)/2).
safe(is/2).
safe(succ/2).
safe(plus/3).
safe(var/1).
safe(nonvar/1).
safe(atom/1).
safe(number/1).
safe(integer/1).
safe(float/1).
safe(atomic/1).
safe(compound/1).
safe(callable/1).
safe(is_list/1).
safe(string/1).
safe(ground/1).
safe(member/2).
safe(memberchk/2).
safe(append/3).
safe(append/2).
safe(length/2).
safe(nth0/3).
safe(nth1/3).
safe(last/2).
safe(reverse/2).
safe(sum_list/2).
safe(sumlist/2).
safe(max_list/2).
safe(min_list/2).
safe(max_member/2).
safe(min_member/2).
safe(list_to_set/2).
safe(sort/2).
safe(sort/4).
safe(msort/2).
safe(delete/3).
safe(subtract/3).
safe(intersection/3).
safe(union/3).
safe(permutation/2).
safe(flatten/2).
safe(select/3).
safe(numlist/3).
safe(between/3).
safe(atom_length/2).
safe(atom_concat/3).
safe(atom_chars/2).
safe(atom_codes/2).
safe(char_code/2).
safe(atom_number/2).
safe(number_codes/2).
safe(sub_atom/5).
safe(upcase_atom/2).
safe(downcase_atom/2).
safe(atom_string/2).
safe(atomic_list_concat/2).
safe(atomic_list_concat/3).
safe(string_concat/3).
safe(string_length/2).
safe(string_chars/2).
safe(string_codes/2).
safe(string_to_atom/2).
safe(sub_string/5).
safe(split_string/4).
safe(number_string/2).

%   user_predicate(+Goal): Goal calls a predicate defined by a trusted rules file.
%   current_predicate/2 does not autoload, so checking a goal never loads a library.
user_predicate(Goal) :-
    current_predicate(_, user:Goal),
    \+ predicate_property(user:Goal, built_in),
    \+ predicate_property(user:Goal, foreign),
    \+ imported_from_library(Goal),
    predicate_property(user:Goal, file(File)),
    trusted_file(File).

%   imported_from_library(+Goal): Goal is exported by a module that a rules file loaded, as opposed to a rules
%   file that is itself a module. Rules may use such a library, but queries may not, wherever it is installed.
imported_from_library(Goal) :-
    predicate_property(user:Goal, imported_from(Module)),
    \+ ( module_property(Module, file(ModuleFile)),
         rules_root(ModuleFile) ).

trusted_file(File) :-
    \+ in_system_library(File),
    loaded_from_root(File, 10).

loaded_from_root(File, _) :-
    rules_root(File),
    !.
loaded_from_root(File, Depth) :-
    Depth > 0,
    Next is Depth - 1,
    (   source_file_property(File, load_context(_, Parent:_, _))
    ;   source_file_property(File, included_in(Parent, _))
    ),
    atom(Parent),
    loaded_from_root(Parent, Next),
    !.

in_system_library(File) :-
    current_prolog_flag(home, Home),
    atom_concat(Home, /, Prefix),
    sub_atom(File, 0, _, _, Prefix).

                /*******************************
                *           HELPERS            *
                *******************************/

deny(Message) :-
    throw(denied(Message)).

deny_format(Format, Args) :-
    format(string(Message), Format, Args),
    deny(Message).
