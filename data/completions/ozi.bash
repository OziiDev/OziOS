# bash completion for ozi
_ozi() {
  local cur prev words cword
  _init_completion 2>/dev/null || { cur="${COMP_WORDS[COMP_CWORD]}"; prev="${COMP_WORDS[COMP_CWORD-1]}"; cword=$COMP_CWORD; words=("${COMP_WORDS[@]}"); }
  local commands="update install remove search review box apps rollback layout effects mode status doctor report clean play winsetup reboot-windows hw help"
  if [ "$cword" -eq 1 ]; then
    COMPREPLY=($(compgen -W "$commands" -- "$cur"))
    return
  fi
  case "${words[1]}" in
    layout)  [ "$cword" -eq 2 ] && COMPREPLY=($(compgen -W "default deck classic board" -- "$cur")) ;;
    effects) [ "$cword" -eq 2 ] && COMPREPLY=($(compgen -W "full light off" -- "$cur")) ;;
    mode)
      case "$cword" in
        2) COMPREPLY=($(compgen -W "game" -- "$cur")) ;;
        3) COMPREPLY=($(compgen -W "on off" -- "$cur")) ;;
      esac ;;
    status)  COMPREPLY=($(compgen -W "--json" -- "$cur")) ;;
    doctor)  COMPREPLY=($(compgen -W "--json --quiet" -- "$cur")) ;;
    report)  COMPREPLY=($(compgen -W "--output --stdout" -- "$cur")) ;;
    clean)
      if [ "$prev" = "--only" ]; then
        COMPREPLY=($(compgen -W "cache journal orphans user" -- "$cur"))
      else
        COMPREPLY=($(compgen -W "--yes --only" -- "$cur"))
      fi ;;
    play)
      if [ "$prev" = "--gpu" ]; then
        COMPREPLY=($(compgen -W "auto integrated discrete" -- "$cur"))
      else
        COMPREPLY=($(compgen -W "--gpu --mangohud --no-gamemode --no-mode --" -- "$cur"))
      fi ;;
    review | box) COMPREPLY=($(compgen -f -- "$cur")) ;;
  esac
}
complete -F _ozi ozi
