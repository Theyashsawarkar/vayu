#!/usr/bin/env bash
# The launcher (prefix Space): one of the launcher's key tables drawn as a
# centred menu, which-key style. Every key is a `bind -T launch... -N
# "<note>"` in tmux.conf; this script only draws them, so a key added
# there shows here, in prefix ? and in Super+Shift+/ with nothing else
# to update.
#   whichkey.sh <client> <table> [title]   show <table>'s keys as a menu
#   whichkey.sh <client> --replay <key>    press prefix <key> for <client>
#                                          (a launcher entry for a key that
#                                          already exists, e.g. a plugin's)
# Picking a menu item puts the client in <table> and presses the item's
# key, so the menu runs exactly what the key table binds. Esc closes.
# Typing the keys without waiting never shows a menu at all (see below).
#
# Errors to the journal when nothing would show them (tmux `run -b` drops
# stderr): read them with `vayu-logs whichkey.sh`.
[ -t 2 ] || [ "${JOURNAL_STREAM:-}" = "$(stat -Lc %d:%i /proc/self/fd/2 2>/dev/null)" ] || exec 2> >(logger -t whichkey.sh)
c=$1 t=$2

if [ "$t" = --replay ]; then
  tmux send-keys -K -c "$c" "$(tmux show -gv prefix)" "$3"
  exit 0
fi

# The binding put the client in <table> and ran this 0.25 s later: if a key
# came meanwhile, the table already handled it and there's nothing to show.
[ "$(tmux display -p -c "$c" '#{client_key_table}')" = "$t" ] || exit 0
# The menu takes the keys from here; leave the table so Esc (closing the
# menu) doesn't leave the next key going to the launcher.
tmux switch-client -c "$c" -T root

title=${3:-launcher}
items=()
groups=() leaves=() tail=()
while IFS= read -r line; do
  line=${line#"${line%%[! ]*}"}                  # list-keys pads the key column
  [ -n "$line" ] || continue
  key=${line%% *}
  note=${line#"$key"}
  note=${note#"${note%%[! ]*}"}
  [[ $key == \\?* ]] && key=${key:1}           # tmux escapes ; # etc.
  cmd="switch-client -c '$c' -T '$t' ; send-keys -c '$c' -K '$key'"
  name=${note//#/##}                             # menu names are formats
  # groups (they open another menu) first, then the tools, then Space / ?
  if tmux list-keys -T "$t" "$key" 2>/dev/null | grep -q 'whichkey\.sh.* launch'; then
    groups+=("$name  …" "$key" "$cmd")
  elif [ "$key" = Space ] || [ "$key" = '?' ]; then
    tail+=("$name" "$key" "$cmd")
  else
    leaves+=("$name" "$key" "$cmd")
  fi
done < <(tmux list-keys -N -P '' -T "$t" 2>/dev/null)

items=("${groups[@]}")
[ ${#groups[@]} -gt 0 ] && [ ${#leaves[@]} -gt 0 ] && items+=("")
items+=("${leaves[@]}")
[ ${#tail[@]} -gt 0 ] && items+=("" "${tail[@]}")
[ ${#items[@]} -gt 0 ] || exit 0

tmux display-menu -c "$c" -x C -y C -T "#[align=centre] $title " "${items[@]}"
exit 0
