# bash completion for ozi
_ozi() {
  local cur prev words cword
  _init_completion 2>/dev/null || { cur="${COMP_WORDS[COMP_CWORD]}"; prev="${COMP_WORDS[COMP_CWORD-1]}"; cword=$COMP_CWORD; words=("${COMP_WORDS[@]}"); }
  local commands="update install remove search review box apps rollback layout theme look quick effects mode status doctor report clean play gaming help"
  if [ "$cword" -eq 1 ]; then
    COMPREPLY=($(compgen -W "$commands" -- "$cur"))
    return
  fi
  case "${words[1]}" in
    layout)  [ "$cword" -eq 2 ] && COMPREPLY=($(compgen -W "default deck classic board" -- "$cur")) ;;
    effects) [ "$cword" -eq 2 ] && COMPREPLY=($(compgen -W "full light off" -- "$cur")) ;;
    theme)
      case "$cword" in
        2) COMPREPLY=($(compgen -W "cyan aurora ember mint rose frost auto --json" -- "$cur")) ;;
        *) [ "${words[2]}" = auto ] && COMPREPLY=($(compgen -W "off --day --night" -- "$cur")) ;;
      esac ;;
    quick)
      case "$cword" in
        2) COMPREPLY=($(compgen -W "volume mute wifi bluetooth night dnd --json" -- "$cur")) ;;
        3) case "${words[2]}" in
             mute) COMPREPLY=($(compgen -W "on off toggle" -- "$cur")) ;;
             wifi | bluetooth | night | dnd) COMPREPLY=($(compgen -W "on off" -- "$cur")) ;;
           esac ;;
      esac ;;
    look)
      case "$cword" in
        2) COMPREPLY=($(compgen -W "preset radius outline glow titlebar gaps tiling blur speed --json" -- "$cur")) ;;
        3) case "${words[2]}" in
             preset) COMPREPLY=($(compgen -W "fluid tiling light" -- "$cur")) ;;
             glow | titlebar | tiling | blur) COMPREPLY=($(compgen -W "on off" -- "$cur")) ;;
             speed) COMPREPLY=($(compgen -W "off fast normal relaxed" -- "$cur")) ;;
           esac ;;
      esac ;;
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
    gaming)  COMPREPLY=($(compgen -W "--yes" -- "$cur")) ;;
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
