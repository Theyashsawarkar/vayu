#!/usr/bin/env bash
# tmux-resurrect save/restore without its status-line chatter.
#   resurrect.sh save | restore
#
# resurrect reports through `tmux display-message` (a "Saving..." spinner,
# "Tmux environment saved!", "Tmux restore complete!"), which lands in the
# top-left of the bar. Here its scripts run with a `tmux` shim first on
# PATH that drops those messages (queries like `display-message -p` still
# pass through), and the result goes to mako like every other tmux
# notification. continuum's auto-restore is pointed at this script too
# (tmux.conf); the 15-minute auto-save (tmux-autosave.timer) runs save.sh
# quietly without this.

dir=~/.tmux/plugins/tmux-resurrect/scripts
last=$(tmux show -gqv @resurrect-dir); last=${last:-$HOME/.tmux/resurrect}/last
notify() { notify-send -a tmux -i utilities-terminal 'tmux' "$1"; }

shim=$(mktemp -d)
trap 'rm -rf "$shim"' EXIT
cat > "$shim/tmux" <<EOF
#!/usr/bin/env bash
case "\$1" in
  display-message|display)
    case " \$* " in *" -p"*) ;; *) exit 0 ;; esac ;;
esac
exec $(command -v tmux) "\$@"
EOF
chmod +x "$shim/tmux"
export PATH="$shim:$PATH"

case ${1:-restore} in
  save)
    "$dir/save.sh" quiet && notify 'Sessions saved' || notify 'Session save failed'
    ;;
  restore)
    [ -e "$last" ] || { notify 'Nothing to restore: no saved sessions yet'; exit 0; }
    "$dir/restore.sh" && notify 'Sessions restored' || notify 'Session restore failed'
    ;;
esac
exit 0
