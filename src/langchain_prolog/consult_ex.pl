% Consult a file and throw an exception if there are any errors.
% Thanks to Jan Wielemaker for this code.
% https://swi-prolog.discourse.group/uploads/short-url/9HaBWEyjPwod9QzimzPZ1OxzHIu.pl

:- module(consult_ex,
          [ consult_ex/1
          ]).

:- meta_predicate
    consult_ex(:).

consult_ex(M:Spec) :-
    nb_setval(consult_errors, 0),
    absolute_file_name(Spec, FullFile,
		       [ file_type(prolog),
			 access(read)
		       ]),
    setup_call_cleanup(
        asserta((user:thread_message_hook(_Term,error,_Lines) :-
                    consult_ex:track_messages(FullFile)), Ref),
        consult(M:FullFile),
        erase(Ref)),
    nb_getval(consult_errors, N),
    (   N =:= 0
    ->  true
    ;   unload_file(FullFile),
        throw(error(consult_error(FullFile),_))
    ).

:- public
    track_messages/1.

track_messages(FullFile) :-
    source_location(FullFile, _Line),
    nb_getval(consult_errors, N0),
    N is N0+1,
    nb_setval(consult_errors, N),
    fail.                               % print normally

		 /*******************************
		 *          MESSAGES		*
		 *******************************/

:- multifile prolog:error_message//1.

prolog:error_message(consult_error(File)) -->
    [ 'Could not load file ~p due to errors'-[File] ].
