# bash completion for ozi-pkg
_ozi_pkg() {
  local cur="${COMP_WORDS[COMP_CWORD]}" prev="${COMP_WORDS[COMP_CWORD-1]}"
  local commands="review install get uninstall aur search upgrade undo list perms run remove"
  local rights="--network --no-network --gpu --no-gpu --sound --no-sound --camera --no-camera --devices --no-devices --x11 --no-x11 --nested-sandbox --no-nested-sandbox --files --folder"
  if [ "$COMP_CWORD" -eq 1 ]; then
    COMPREPLY=($(compgen -W "$commands" -- "$cur"))
    return
  fi
  if [ "$prev" = "--files" ]; then
    COMPREPLY=($(compgen -W "none chosen home" -- "$cur"))
    return
  fi
  case "${COMP_WORDS[1]}" in
    review)  COMPREPLY=($(compgen -W "--json" -- "$cur") $(compgen -f -- "$cur")) ;;
    install) COMPREPLY=($(compgen -W "--yes --force $rights" -- "$cur") $(compgen -f -- "$cur")) ;;
    aur)     COMPREPLY=($(compgen -W "--yes --force" -- "$cur")) ;;
    perms)   COMPREPLY=($(compgen -W "$rights" -- "$cur")) ;;
  esac
}
complete -F _ozi_pkg ozi-pkg
