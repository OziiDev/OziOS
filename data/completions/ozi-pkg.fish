# fish completion for ozi-pkg
set -l commands review install get uninstall aur search upgrade undo list perms run remove
complete -c ozi-pkg -f
complete -c ozi-pkg -n "not __fish_seen_subcommand_from $commands" -a "$commands"
complete -c ozi-pkg -n "__fish_seen_subcommand_from install aur" -l yes
complete -c ozi-pkg -n "__fish_seen_subcommand_from install aur" -l force
complete -c ozi-pkg -n "__fish_seen_subcommand_from review" -l json
complete -c ozi-pkg -n "__fish_seen_subcommand_from review install" -F
