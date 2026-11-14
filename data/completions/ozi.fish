# fish completion for ozi
set -l commands update install remove search review box apps rollback layout effects mode status doctor report clean play winsetup reboot-windows hw help
complete -c ozi -f
complete -c ozi -n "not __fish_seen_subcommand_from $commands" -a "$commands"
complete -c ozi -n "__fish_seen_subcommand_from layout" -a "default deck classic board"
complete -c ozi -n "__fish_seen_subcommand_from effects" -a "full light off"
complete -c ozi -n "__fish_seen_subcommand_from mode" -a "game"
complete -c ozi -n "__fish_seen_subcommand_from mode; and __fish_seen_subcommand_from game" -a "on off"
complete -c ozi -n "__fish_seen_subcommand_from status" -l json -d "machine-readable output"
complete -c ozi -n "__fish_seen_subcommand_from doctor" -l json -d "machine-readable output"
complete -c ozi -n "__fish_seen_subcommand_from doctor" -l quiet -d "only warnings and problems"
complete -c ozi -n "__fish_seen_subcommand_from report" -l output -r -d "where to write the report"
complete -c ozi -n "__fish_seen_subcommand_from report" -l stdout -d "print instead of writing a file"
complete -c ozi -n "__fish_seen_subcommand_from clean" -l yes -d "do it"
complete -c ozi -n "__fish_seen_subcommand_from clean" -l only -x -a "cache journal orphans user"
complete -c ozi -n "__fish_seen_subcommand_from play" -l gpu -x -a "auto integrated discrete"
complete -c ozi -n "__fish_seen_subcommand_from play" -l mangohud -d "performance overlay"
complete -c ozi -n "__fish_seen_subcommand_from play" -l no-gamemode
complete -c ozi -n "__fish_seen_subcommand_from play" -l no-mode
complete -c ozi -n "__fish_seen_subcommand_from review box" -F
