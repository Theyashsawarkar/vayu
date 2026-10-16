#!/usr/bin/env bash
# Pull request popup (prefix G): read, review, merge and close the PRs of
# the repo in the current pane without opening the browser.
#   gh-pr.sh                      run inside the repo (the popup sets -d)
#
# Vim-style: it opens in normal mode (letters are commands); / searches,
# Enter or Esc leaves search. The GitHub account comes from the repo's
# `git config github.user` (set per folder with includeIf), else gh's
# active account.
#
# keybind: Tmux/PR popup | j / k | Move to the next / previous PR
# keybind: Tmux/PR popup | g / G | Jump to the first / last PR
# keybind: Tmux/PR popup | 1 / 2 / 3 / 4 | Show the overview / diff / checks / comments
# keybind: Tmux/PR popup | Tab | Cycle the preview (overview, diff, checks, comments)
# keybind: Tmux/PR popup | J / K | Scroll the preview down / up
# keybind: Tmux/PR popup | Ctrl+d / Ctrl+u | Scroll the preview half a page down / up
# keybind: Tmux/PR popup | Enter | Open the current view full screen (failed check logs in checks)
# keybind: Tmux/PR popup | / | Search PRs (Enter or Esc goes back to normal mode)
# keybind: Tmux/PR popup | f | Cycle the filter (open, review requested, mine, closed, merged, all)
# keybind: Tmux/PR popup | R | Reload PRs from GitHub
# keybind: Tmux/PR popup | m | Merge the PR (squash, merge commit, rebase or auto-merge)
# keybind: Tmux/PR popup | a | Approve the PR (optional message)
# keybind: Tmux/PR popup | r | Request changes on the PR (message in your editor)
# keybind: Tmux/PR popup | c | Add a comment to the PR (in your editor)
# keybind: Tmux/PR popup | x | Close the PR (reopens a closed one)
# keybind: Tmux/PR popup | o | Switch this repo to the PR's branch (gh pr checkout)
# keybind: Tmux/PR popup | d | Toggle the PR between draft and ready for review
# keybind: Tmux/PR popup | y | Copy the PR's link
# keybind: Tmux/PR popup | b | Open the PR in the browser
# keybind: Tmux/PR popup | q / Esc | Quit the PR popup
# keybind: Tmux/PR popup | Ctrl+a G | Quit the PR popup (prefix G toggles it)

self=$(readlink -f "$0")

rose=$'\e[38;2;208;149;164m' gold=$'\e[38;2;212;178;92m' dim=$'\e[38;2;108;112;134m'
fg=$'\e[38;2;215;221;230m' sub=$'\e[38;2;154;159;170m' green=$'\e[38;2;158;209;166m'
red=$'\e[38;2;232;125;125m' blue=$'\e[38;2;108;142;191m' purple=$'\e[38;2;194;130;206m'
b=$'\e[1m' r=$'\e[0m' key=$'\e[1;38;2;208;149;164m'

FILTERS=(open review mine closed merged all)
NORMAL_KEYS='j,k,g,G,J,K,1,2,3,4,f,R,m,a,r,c,x,o,d,y,b,q,/'

# ------------------------------------------------------------------ data
# List fields: cheap enough for one call (detail per PR is fetched apart).
LIST_FIELDS=number,title,author,headRefName,baseRefName,isDraft,additions,deletions,changedFiles,updatedAt,reviewDecision,state,url,isCrossRepository,labels,statusCheckRollup
VIEW_FIELDS=number,title,author,headRefName,baseRefName,isDraft,additions,deletions,changedFiles,createdAt,updatedAt,mergedAt,closedAt,reviewDecision,state,url,isCrossRepository,labels,statusCheckRollup,body,comments,files,latestReviews,reviews,reviewRequests,mergeable,mergeStateStatus,assignees

filter() { cat "$STATE/filter" 2>/dev/null || echo open; }
mode() { cat "$STATE/mode" 2>/dev/null || echo overview; }

fetch_list() {
  local f=${1:-$(filter)} args=()
  case $f in
    open) args=(--state open) ;;
    review) args=(--state open --search 'review-requested:@me') ;;
    mine) args=(--state open --author @me) ;;
    closed) args=(--state closed) ;;
    merged) args=(--state merged) ;;
    all) args=(--state all) ;;
  esac
  # Closed/merged PRs don't need CI status, the heaviest field.
  local fields=$LIST_FIELDS
  case $f in closed | merged) fields=${fields%,statusCheckRollup} ;; esac
  gh pr list -R "$REPO" -L 50 "${args[@]}" --json "$fields" >"$CACHE/list-$f.tmp" 2>"$STATE/err" &&
    mv "$CACHE/list-$f.tmp" "$CACHE/list-$f.json"
}

fetch_pr() {
  local n=$1
  gh pr view "$n" -R "$REPO" --json "$VIEW_FIELDS" >"$CACHE/$n.tmp" 2>/dev/null && mv "$CACHE/$n.tmp" "$CACHE/$n.json"
  [ "$2" = --quick ] && return
  gh pr diff "$n" -R "$REPO" --color=never >"$CACHE/$n.diff.tmp" 2>/dev/null && mv "$CACHE/$n.diff.tmp" "$CACHE/$n.diff"
  gh api "repos/$REPO/pulls/$n/comments" --paginate >"$CACHE/$n.rc.tmp" 2>/dev/null && mv "$CACHE/$n.rc.tmp" "$CACHE/$n.rc.json"
}

# Details for the first PRs of the list, a few at a time, in the background.
prefetch() {
  local done=$STATE/prefetched-$(filter)
  [ -e "$done" ] && return
  touch "$done"
  jq -r '.[:15][].number' "$CACHE/list-$(filter).json" 2>/dev/null |
    xargs -r -P 4 -I{} "$self" --fetch-pr {} >/dev/null 2>&1
}

# ------------------------------------------------------------------ list
JQ_DEFS='
def ci: (.statusCheckRollup // []) as $c
  | if ($c | length) == 0 then "none"
    elif any($c[]; ((.conclusion // .state // "") | test("FAILURE|ERROR|TIMED_OUT|CANCELLED|ACTION_REQUIRED|STARTUP_FAILURE"))) then "fail"
    elif any($c[]; ((.status // "COMPLETED") != "COMPLETED") or ((.state // "") | test("PENDING|EXPECTED"))) then "pending"
    else "pass" end;
def ago(t): (now - (t | fromdateiso8601)) as $s
  | if $s < 3600 then "\($s / 60 | floor)m" elif $s < 86400 then "\($s / 3600 | floor)h"
    elif $s < 604800 then "\($s / 86400 | floor)d" elif $s < 2592000 then "\($s / 604800 | floor)w"
    else "\($s / 2592000 | floor)mo" end;
'

ci_icon() { case $1 in pass) echo "${green}✓" ;; fail) echo "${red}✗" ;; pending) echo "${gold}●" ;; *) echo "${dim}·" ;; esac; }
rev_icon() { case $1 in APPROVED) echo "${green}✔" ;; CHANGES_REQUESTED) echo "${red}✎" ;; REVIEW_REQUIRED) echo "${dim}○" ;; *) echo " " ;; esac; }

# One NUL-separated, two-line entry per PR: number <TAB> line 1 <TAB> line 2.
list() {
  local file=$CACHE/list-$(filter).json
  [ -s "$file" ] || { [ "$1" = --cached ] && return; fetch_list || return; }
  jq -r "$JQ_DEFS"'.[] | [.number, .title, .author.login, .headRefName, .baseRefName, .additions, .deletions,
      .changedFiles, ci, (.reviewDecision // ""), .isDraft, ago(.updatedAt), .state,
      ([.labels[].name] | join(", "))] | map(tostring) | join("\u001f")' "$file" |
  while IFS=$'\x1f' read -r n title author head base add del files ci rev draft age state labels; do
    local tag=""
    [ "$draft" = true ] && tag="${dim}draft "
    [ "$state" = MERGED ] && tag="${purple}merged "
    [ "$state" = CLOSED ] && tag="${red}closed "
    [ -n "$labels" ] && labels="  ${dim}[$labels]"
    printf '%s\t %s %s %s%4s %s#%-5s %s%s%s%s%s\t\n               %s%s %s· %s%s %s→ %s  %s+%s %s−%s %s· %s file%s%s%s\0' \
      "$n" "$(ci_icon "$ci")" "$(rev_icon "$rev")" "$dim" "$age" "$gold$b" "$n" "$r" "$tag" "$fg$b" "$title" "$r" \
      "$sub" "$author" "$dim" "$blue" "$head" "$dim" "$base" "$green" "$add" "$red" "$del" "$dim" "$files" \
      "$([ "$files" = 1 ] || echo s)" "$labels" "$r"
  done
}

# ------------------------------------------------------------------ views
cols() { echo "${FZF_PREVIEW_COLUMNS:-$(tput cols 2>/dev/null || echo 100)}"; }
rule() { local w; w=$(( $(cols) - 2 )); printf '%s── %s %s%s\n' "$dim" "$1" "$(printf '─%.0s' $(seq 1 $(( w > ${#1} + 4 ? w - ${#1} - 4 : 1 ))))" "$r"; }
# Capsule like the tmux status bar: badge <hex bg> <text>
badge() {
  local h=${1#\#} bg; bg="$((16#${h:0:2}));$((16#${h:2:2}));$((16#${h:4:2}))"
  printf '\e[38;2;%sm\e[0m\e[48;2;%sm\e[38;2;11;14;20m\e[1m %s \e[0m\e[38;2;%sm\e[0m' "$bg" "$bg" "$2" "$bg"
}
# GitHub-style change bar: <added> <deleted> <width>: green/red share, gray rest
bar() {
  local a=$1 d=$2 w=${3:-5} t ga gd i out=""
  t=$((a + d)); [ "$t" -gt 0 ] || { printf '%s%s%s' "$dim" "$(printf '▪%.0s' $(seq 1 "$w"))" "$r"; return; }
  ga=$(( (a * w + t / 2) / t )); gd=$(( w - ga ))
  [ "$a" -gt 0 ] && [ "$ga" -eq 0 ] && { ga=1; gd=$((w - 1)); }
  [ "$d" -gt 0 ] && [ "$gd" -eq 0 ] && { gd=1; ga=$((w - 1)); }
  for ((i = 0; i < ga; i++)); do out+="${green}▪"; done
  for ((i = 0; i < gd; i++)); do out+="${red}▪"; done
  printf '%s%s' "$out" "$r"
}
md() { bat -l md --color=always --style=plain --paging=never --terminal-width "$(cols)" 2>/dev/null || cat; }

need_pr() {
  [ -s "$CACHE/$1.json" ] || fetch_pr "$1"
  [ -s "$CACHE/$1.json" ] || { echo "${red}Couldn't load #$1 from GitHub.$r"; return 1; }
}

view_overview() {
  local n=$1 j=$CACHE/$1.json
  need_pr "$n" || return
  local st title who upd opened head base fork
  IFS=$'\x1f' read -r st title who upd opened head base fork < <(jq -r "$JQ_DEFS"'
    [(if .state == "OPEN" and .isDraft then "DRAFT" else .state end), .title, .author.login,
     ago(.updatedAt), ago(.createdAt), .headRefName, .baseRefName, .isCrossRepository] | map(tostring) | join("\u001f")' "$j")
  echo
  printf ' %s#%s%s  %s%s%s\n\n' "$gold$b" "$n" "$r" "$fg$b" "$title" "$r"
  case $st in OPEN) bc=#9ED1A6 ;; DRAFT) bc=#9A9FAA ;; MERGED) bc=#C282CE ;; *) bc=#E87D7D ;; esac
  printf ' %s  %s %s%s · updated %s ago · opened %s ago%s\n' "$(badge "$bc" "$st")" "$gold$who$r" "$sub" "" "$upd" "$opened" "$r"
  printf '  %s %s%s %s→%s %s%s%s\n\n' "$dim" "$blue" "$head" "$dim" "$r" "$blue" "$base" "$([ "$fork" = true ] && echo "$dim  (from a fork)")$r"
  local ms mg rd
  IFS=$'\x1f' read -r ms mg rd < <(jq -r '[.mergeStateStatus, .mergeable, (.reviewDecision // "")] | map(tostring) | join("\u001f")' "$j")
  local state; state=$(jq -r .state "$j")
  if [ "$state" = OPEN ]; then
    case $ms in
      CLEAN) m="${green}✓ ready to merge" ;;
      UNSTABLE) m="${gold}● mergeable, but some checks fail" ;;
      BLOCKED) m="${gold}● blocked$([ "$rd" = REVIEW_REQUIRED ] && echo ": needs an approving review")$([ "$rd" = CHANGES_REQUESTED ] && echo ": changes requested")" ;;
      BEHIND) m="${gold}● behind ${b}base${r}${gold}: update the branch first" ;;
      DIRTY) m="${red}✗ merge conflicts" ;;
      DRAFT) m="${dim}draft: mark it ready (d) before merging" ;;
      HAS_HOOKS) m="${green}✓ mergeable (with hooks)" ;;
      *) m="${dim}… GitHub is still computing mergeability" ;;
    esac
    printf '  %s󰘬  merge%s     %s%s\n' "$dim" "$r" "$m" "$r"
  fi
  # Checks summary
  read -r pass fail pend < <(jq -r '(.statusCheckRollup // []) | map(.conclusion // .state // .status // "") |
      [(map(select(test("SUCCESS|NEUTRAL|SKIPPED"))) | length),
       (map(select(test("FAILURE|ERROR|TIMED_OUT|CANCELLED|ACTION_REQUIRED|STARTUP_FAILURE"))) | length),
       (map(select(test("SUCCESS|NEUTRAL|SKIPPED|FAILURE|ERROR|TIMED_OUT|CANCELLED|ACTION_REQUIRED|STARTUP_FAILURE") | not)) | length)] | @tsv' "$j")
  if [ $((pass + fail + pend)) -eq 0 ]; then c="${dim}none"
  else c="${green}✓ $pass passed$r"; [ "$fail" -gt 0 ] && c+="  ${red}✗ $fail failed$r"; [ "$pend" -gt 0 ] && c+="  ${gold}● $pend running$r"; fi
  printf '  %s  checks%s    %s%s\n' "$dim" "$r" "$c" "$r"
  # Reviews: latest per reviewer, plus who's still asked
  local rv
  rv=$(jq -r '[(.latestReviews // [])[] | select(.state != "COMMENTED" and .state != "PENDING") |
        (if .state == "APPROVED" then "\u001b[38;2;158;209;166m✔ \(.author.login) approved"
         elif .state == "CHANGES_REQUESTED" then "\u001b[38;2;232;125;125m✎ \(.author.login) requested changes"
         else "\(.author.login) \(.state | ascii_downcase)" end)]
       + [(.reviewRequests // [])[] | "\u001b[38;2;108;112;134m○ waiting on \(.login // .name // .slug)"] | join("\u001b[0m  ")' "$j")
  printf '  %s  reviews%s   %s%s\n' "$dim" "$r" "${rv:-${dim}none yet}" "$r"
  jq -r 'if (.labels | length) > 0 then "  \u001b[38;2;108;112;134m  labels\u001b[0m    \([.labels[].name] | join(", "))" else empty end' "$j"
  jq -r 'if (.assignees | length) > 0 then "  \u001b[38;2;108;112;134m  assigned\u001b[0m  \([.assignees[].login] | join(", "))" else empty end' "$j"
  local ad dl cf; read -r ad dl cf < <(jq -r '"\(.additions) \(.deletions) \(.changedFiles)"' "$j")
  printf '  %s  changes%s   %s+%s%s %s−%s%s in %s file%s  %s\n' "$dim" "$r" "$green" "$ad" "$r" "$red" "$dl" "$r" "$cf" "$([ "$cf" = 1 ] || echo s)" "$(bar "$ad" "$dl" 10)"
  echo
  rule "files ($cf)"
  jq -r '.files[] | "\(.additions)\t\(.deletions)\t\(.path)"' "$j" | head -40 |
    while IFS=$'\t' read -r a d p; do
      local dir=${p%/*}/; [ "$dir" = "$p/" ] && dir=""
      printf '  %s %s%5s%s %s%5s%s  %s%s%s%s%s\n' "$(bar "$a" "$d" 5)" "$green" "+$a" "$r" "$red" "−$d" "$r" "$dim" "$dir" "$fg" "${p##*/}" "$r"
    done
  [ "$(jq '.files | length' "$j")" -gt 40 ] && echo "  ${dim}… and more (2 shows the full diff)$r"
  echo
  rule description
  local body; body=$(jq -r '.body // ""' "$j")
  if [ -n "${body//[[:space:]]/}" ]; then printf '%s\n' "$body" | tr -d '\r' | md; else echo "  ${dim}no description$r"; fi
  local nc; nc=$(jq '(.comments | length) + ([.reviews[] | select(.body != "")] | length)' "$j")
  local ni; ni=$(jq 'length' "$CACHE/$n.rc.json" 2>/dev/null || echo 0)
  echo
  [ $((nc + ni)) -gt 0 ] && echo "  ${dim}$nc comment(s), $ni on the code: press 4 to read them$r"
}

view_diff() {
  [ -s "$CACHE/$1.diff" ] || fetch_pr "$1"
  [ -s "$CACHE/$1.diff" ] || { echo "${dim}No diff (or couldn't load it).$r"; return; }
  bat -l diff --color=always --style=plain --paging=never --terminal-width "$(cols)" "$CACHE/$1.diff" 2>/dev/null || cat "$CACHE/$1.diff"
}

view_checks() {
  need_pr "$1" || return
  local rows
  rows=$(jq -r '(.statusCheckRollup // [])[] |
      (.conclusion // .state // .status // "") as $s |
      [(if ($s | test("FAILURE|ERROR|TIMED_OUT|CANCELLED|ACTION_REQUIRED|STARTUP_FAILURE")) then 0
        elif ($s | test("SUCCESS|NEUTRAL|SKIPPED")) then 2 else 1 end),
       $s, (.workflowName // ""),
       (if (.name // "") != "" then .name else (.context // .workflowName // "check") end),
       (if .startedAt and .completedAt and (.completedAt | startswith("0001") | not) and (.startedAt | startswith("0001") | not)
        then (((.completedAt | fromdateiso8601) - (.startedAt | fromdateiso8601)) |
              if . < 0 then "" elif . < 60 then "\(.)s" else "\(. / 60 | floor)m \(. % 60)s" end) else "" end)] | map(tostring) | join("\u001f")' "$CACHE/$1.json" | sort -t$'\x1f' -k1,1n -k3)
  [ -n "$rows" ] || { echo "  ${dim}No checks on this PR.$r"; return; }
  while IFS=$'\x1f' read -r _ s wf name dur; do
    case $s in
      SUCCESS) i="${green}✓" ;; NEUTRAL|SKIPPED) i="${dim}–" ;;
      FAILURE|ERROR|TIMED_OUT|CANCELLED|ACTION_REQUIRED|STARTUP_FAILURE) i="${red}✗" ;;
      *) i="${gold}●" ;;
    esac
    printf '  %s%s  %s%s%s  %s%s%s%s\n' "$i" "$r" "$fg" "$name" "$r" "$dim" "$wf" "${dur:+${wf:+ · }$dur}" "$r"
  done <<<"$rows"
  grep -q '^0' <<<"$rows" && printf '\n  %sEnter shows the failed jobs'"'"' logs.%s\n' "$dim" "$r"
}

view_comments() {
  need_pr "$1" || return
  local j=$CACHE/$1.json
  # Conversation: comments and reviews with a body, oldest first
  local conv
  conv=$(jq -r '[(.comments[] | {t: .createdAt, who: .author.login, what: "commented", body}),
                 (.reviews[] | select(.body != "") | {t: .submittedAt, who: .author.login,
                   what: (.state | ascii_downcase | gsub("_"; " ")), body})] | sort_by(.t)[] |
                "\u0001\(.who)\t\(.what)\t\(.t)\n\(.body)"' "$j")
  rule conversation
  if [ -z "$conv" ]; then echo "  ${dim}No comments.$r"; else
    printf '%s\n' "$conv" | tr -d '\r' | while IFS= read -r line; do
      if [[ $line == $'\001'* ]]; then
        IFS=$'\t' read -r who what t <<<"${line#$'\001'}"
        printf '\n%s%s%s %s%s · %s%s\n' "$gold$b" "$who" "$r" "$dim" "$what" "${t%T*}" "$r"
      else printf '  %s\n' "$line"; fi
    done
  fi
  echo
  rule "on the code"
  local rc=$CACHE/$1.rc.json
  if [ ! -s "$rc" ] || [ "$(jq length "$rc")" = 0 ]; then echo "  ${dim}No review comments on the code.$r"; return; fi
  jq -r 'sort_by(.path, (.original_line // .line // 0), .created_at)[] |
      "\u0001\(.path)\t\(.line // .original_line // "?")\t\(.user.login)\t\(if .in_reply_to_id then "reply" else "" end)\n\(.body)"' "$rc" |
    tr -d '\r' | while IFS= read -r line; do
      if [[ $line == $'\001'* ]]; then
        IFS=$'\t' read -r path ln who reply <<<"${line#$'\001'}"
        printf '\n%s%s:%s%s  %s%s%s%s\n' "$blue" "$path" "$ln" "$r" "$gold" "$who" "$r" "${reply:+ $dim(reply)$r}"
      else printf '  %s\n' "$line"; fi
    done
}

preview() {
  [ -n "$1" ] || { echo; echo "  ${dim}No pull requests for this filter. f changes it, R reloads.$r"; return; }
  "view_$(mode)" "$1"
}

preview_label() {
  local m out="" i=1; m=$(mode)
  for v in overview diff checks comments; do
    if [ "$v" = "$m" ]; then out+=" ${key}$i $v$r "; else out+=" ${dim}$i $v$r "; fi
    i=$((i + 1))
  done
  printf '%s' "${1:+$gold#$1$r $dim·$r}$out"
}

list_label() {
  local who=${GH_USER:-$(gh config get -h github.com user 2>/dev/null)}
  local count="${FZF_TOTAL_COUNT:-0} PRs"; [ -n "$1" ] && count=$1
  printf ' 󰊤 %s · %s%s%s · %s%s as %s%s ' "$REPO" "$gold" "$(filter)" "$r" "$dim" "$count" "$who" "$r"
}

# Full-screen version of the current view; in checks, the failed jobs' logs.
open_full() {
  local n=$1; [ -n "$n" ] || return
  export FZF_PREVIEW_COLUMNS=$(tput cols)
  # Nerd Font icons are private-use code points; tell less they print.
  export LESSUTFCHARDEF=e000-f8ff:p,f0000-ffffd:p
  if [ "$(mode)" = checks ]; then
    local jobs
    jobs=$(jq -r '(.statusCheckRollup // [])[] | select((.conclusion // "") | test("FAILURE|TIMED_OUT|CANCELLED|STARTUP_FAILURE")) | .detailsUrl // empty' "$CACHE/$n.json" |
      sed -n 's#.*/actions/runs/[0-9]*/job/\([0-9]*\).*#\1#p')
    if [ -n "$jobs" ]; then
      for id in $jobs; do gh run view -R "$REPO" --job "$id" --log-failed 2>&1 | fmt_log; done | less -R
      return
    fi
  fi
  preview "$n" | less -R
}

# gh's "job <TAB> step <TAB> timestamp text" lines: one header per job/step,
# no timestamps or leftover color codes, errors in red.
fmt_log() {
  awk -F'\t' -v red="$red" -v gold="$gold$b" -v dim="$dim" -v r="$r" '
    NF < 3 { print; next }
    $1 != job { job = $1; print "\n" gold "✗ " job r }
    $2 != step { step = $2; print dim "  ── " step " ──" r }
    { line = $3; for (i = 4; i <= NF; i++) line = line "\t" $i
      sub(/^\xef\xbb\xbf/, "", line); sub(/^[0-9-]+T[0-9:.]+Z ?/, "", line)
      gsub(/(\^\[|\033)\[[0-9;]*m/, "", line)
      if (line ~ /^##\[endgroup\]/) next
      sub(/^##\[group\]/, "▸ ", line)
      if (line ~ /##\[error\]|FAIL|[Ee]rror:/) { sub(/##\[error\]/, "", line); line = red line r }
      print "    " line }'
}

# ------------------------------------------------------------------ actions
pause() { printf '\n%spress any key%s' "$dim" "$r"; read -rsn1; }
ask() { local k; printf '%s' "$1" >&2; read -rsn1 k; echo >&2; printf '%s' "$k"; }
notify() { notify-send -a tmux -i utilities-terminal "PR #$1" "$2"; }

header() {
  clear
  jq -r '"\u001b[1;38;2;212;178;92m#\(.number)\u001b[0m  \u001b[1m\(.title)\u001b[0m\n\u001b[38;2;108;112;134m\(.author.login) · \(.headRefName) → \(.baseRefName) · \(.state | ascii_downcase)\u001b[0m\n"' "$CACHE/$1.json"
}

# Message in $EDITOR. Prints the file's text above the marker; empty = cancel.
compose() {
  local f; f=$(mktemp --suffix=.md)
  printf '\n\n──── write above this line; leave it empty to cancel ────\n%s on #%s: %s\n' "$1" "$2" "$(jq -r .title "$CACHE/$2.json")" >"$f"
  "${VISUAL:-${EDITOR:-nvim}}" "$f" </dev/tty >/dev/tty
  sed '/^──── write above this line/,$d' "$f"
  rm -f "$f"
}

action() {
  local a=$1 n=$2
  [ -n "$n" ] || return
  need_pr "$n" >/dev/null || { pause; return; }
  local title state; title=$(jq -r .title "$CACHE/$n.json"); state=$(jq -r .state "$CACHE/$n.json")
  case $a in
    merge)
      [ "$state" = OPEN ] || { header "$n"; echo "This PR is ${state,,}; nothing to merge."; pause; return; }
      header "$n"; view_overview "$n" | sed -n '/merge/,/changes/p'; echo
      local k how auto=""
      k=$(ask "  ${key}s${r} squash   ${key}m${r} merge commit   ${key}r${r} rebase   ${key}a${r} auto-merge (squash) when checks pass   ${dim}any other key cancels$r  ")
      case $k in s) how=--squash ;; m) how=--merge ;; r) how=--rebase ;; a) how=--squash auto=--auto ;; *) return ;; esac
      local del=n head cross; head=$(jq -r .headRefName "$CACHE/$n.json"); cross=$(jq -r .isCrossRepository "$CACHE/$n.json")
      if [ "$cross" = false ] && [ -z "$auto" ]; then
        k=$(ask "  Delete the branch ${blue}$head${r} on GitHub afterwards? ${key}Y${r}/n ")
        [ "$k" = n ] || [ "$k" = N ] || del=y
      fi
      echo
      # -R and no --delete-branch: gh then leaves the local checkout alone.
      if out=$(gh pr merge "$n" -R "$REPO" $how $auto 2>&1); then
        [ "$del" = y ] && gh api -X DELETE "repos/$REPO/git/refs/heads/$head" >/dev/null 2>&1 && out+=$'\n'"Deleted branch $head."
        echo "${green}$out${r}"; notify "$n" "$([ -n "$auto" ] && echo "Auto-merge enabled" || echo Merged): $title"
        sleep 0.8
      else
        echo "${red}$out${r}"; pause
      fi ;;
    approve)
      header "$n"
      printf '  Approve with an optional message (Enter approves, Ctrl+c cancels):\n  %s❯%s ' "$rose" "$r"
      local msg; read -re msg || return
      if out=$(gh pr review "$n" -R "$REPO" --approve ${msg:+--body "$msg"} 2>&1); then
        notify "$n" "Approved: $title"
      else echo "${red}$out${r}"; pause; fi ;;
    request)
      local body; body=$(compose "Requesting changes" "$n")
      [ -n "${body//[[:space:]]/}" ] || return
      header "$n"
      if out=$(gh pr review "$n" -R "$REPO" --request-changes --body "$body" 2>&1); then
        notify "$n" "Requested changes: $title"
      else echo "${red}$out${r}"; pause; fi ;;
    comment)
      local body; body=$(compose "Comment" "$n")
      [ -n "${body//[[:space:]]/}" ] || return
      header "$n"
      if out=$(gh pr comment "$n" -R "$REPO" --body "$body" 2>&1); then
        notify "$n" "Commented: $title"
      else echo "${red}$out${r}"; pause; fi ;;
    close)
      header "$n"
      case $state in
        OPEN)
          [ "$(ask "  Close this PR without merging? y/${key}N${r} ")" = y ] || return
          printf '  Optional closing comment (Enter to skip):\n  %s❯%s ' "$rose" "$r"
          local msg; read -re msg || return
          if out=$(gh pr close "$n" -R "$REPO" ${msg:+--comment "$msg"} 2>&1); then notify "$n" "Closed: $title"
          else echo "${red}$out${r}"; pause; fi ;;
        CLOSED)
          [ "$(ask "  Reopen this PR? y/${key}N${r} ")" = y ] || return
          if out=$(gh pr reopen "$n" -R "$REPO" 2>&1); then notify "$n" "Reopened: $title"
          else echo "${red}$out${r}"; pause; fi ;;
        *) echo "  Merged PRs can't be closed or reopened."; pause ;;
      esac ;;
    checkout)
      header "$n"
      [ "$(ask "  Switch $(basename "$PWD") to this PR's branch? y/${key}N${r} ")" = y ] || return
      if out=$(gh pr checkout "$n" -R "$REPO" 2>&1); then echo "${green}$out${r}"; notify "$n" "Checked out: $title"; sleep 0.8
      else echo "${red}$out${r}"; pause; fi ;;
    draft)
      if [ "$(jq -r .isDraft "$CACHE/$n.json")" = true ]; then out=$(gh pr ready "$n" -R "$REPO" 2>&1) && notify "$n" "Ready for review: $title"
      else out=$(gh pr ready "$n" -R "$REPO" --undo 2>&1) && notify "$n" "Back to draft: $title"; fi ||
        { header "$n"; echo "${red}$out${r}"; pause; } ;;
  esac
  fetch_pr "$n" --quick
}

# ------------------------------------------------------------------ main
case $1 in
  --list) list "$2"; exit ;;
  --reload) fetch_list; list; exit ;;
  --preview) preview "$2"; exit ;;
  --plabel) preview_label "$2"; exit ;;
  --llabel) list_label; exit ;;
  --mode) echo "$2" >"$STATE/mode"; exit ;;
  --next-mode)
    case $(mode) in overview) m=diff ;; diff) m=checks ;; checks) m=comments ;; *) m=overview ;; esac
    echo "$m" >"$STATE/mode"; exit ;;
  --next-filter)
    cur=$(filter) nxt=${FILTERS[0]}
    for i in "${!FILTERS[@]}"; do [ "${FILTERS[$i]}" = "$cur" ] && nxt=${FILTERS[$(( (i + 1) % ${#FILTERS[@]} ))]}; done
    echo "$nxt" >"$STATE/filter"; rm -f "$STATE/fresh"; exit ;;
  --fetch-pr) fetch_pr "$2"; exit ;;
  # tmux doesn't see keys while a popup is open, so prefix G (Ctrl+a, G)
  # is caught here: Ctrl+a marks the time, a G within 2 s closes the popup.
  --prefix) touch "$STATE/prefix"; exit ;;
  --G)
    if [ -n "$(find "$STATE/prefix" -newermt '-2 seconds' 2>/dev/null)" ]; then echo abort; else echo last; fi
    exit ;;
  # First load shows the cached list; it then asks for the fresh one once.
  # Every load updates the label and prefetches details in the background.
  --on-load)
    if [ ! -e "$STATE/fresh" ]; then
      touch "$STATE/fresh"; echo "change-list-label($(list_label refreshing…))+reload-sync($self --reload)"; exit
    fi
    setsid -f "$self" --prefetch >/dev/null 2>&1
    echo "change-list-label($(list_label))"; exit ;;
  --copy)
    jq -r .url "$CACHE/$2.json" 2>/dev/null | wl-copy && notify-send -a tmux -i utilities-terminal "PR #$2" "Link copied"
    exit ;;
  --prefetch) prefetch; exit ;;
  --action) action "$2" "$3"; exit ;;
  --full) open_full "$2"; exit ;;
esac

# Repo from the origin remote (no network); gh as a fallback.
url=$(git remote get-url origin 2>/dev/null)
url=${url%.git}
case $url in *github*) REPO=$(sed -E 's#.*[:/]([^/:]+/[^/]+)$#\1#' <<<"$url") ;; esac
[ -n "$REPO" ] || REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)
if [ -z "$REPO" ]; then
  notify-send -a tmux -i utilities-terminal "Pull requests" "$(basename "$PWD") isn't a GitHub repository"
  exit 0
fi

# Account for this folder (git config github.user), else gh's active one.
GH_USER=$(git config --get github.user 2>/dev/null)
if [ -n "$GH_USER" ] && tok=$(gh auth token --user "$GH_USER" 2>/dev/null); then export GH_TOKEN=$tok; else GH_USER=""; fi

CACHE=${XDG_CACHE_HOME:-$HOME/.cache}/gh-pr/${REPO//\//_}
STATE=$(mktemp -d "${XDG_RUNTIME_DIR:-/tmp}/gh-pr.XXXXXX")
mkdir -p "$CACHE"
trap 'rm -rf "$STATE"' EXIT
export REPO GH_USER CACHE STATE

# Short lines: the legend sits under the list, which gets 40% of the width.
footer="${key}j/k${r} move  ${key}g/G${r} top/end  ${key}/${r} search  ${key}f${r} filter  ${key}R${r} reload
${key}1${r} overview ${key}2${r} diff ${key}3${r} checks ${key}4${r} comments ${key}tab${r} next
${key}J/K${r} scroll  ${key}enter${r} full screen  ${key}b${r} browser  ${key}y${r} copy link
${key}m${r} merge  ${key}a${r} approve  ${key}r${r} request changes  ${key}c${r} comment
${key}x${r} close/reopen  ${key}o${r} checkout  ${key}d${r} draft/ready  ${key}q${r} quit"

normal="hide-input+rebind($NORMAL_KEYS)"
# esc/enter use transform:CMD (to the end of the binding), not transform(CMD):
# fzf ends the latter at the first ")", which is inside rebind(...).
act() { echo "execute($self --action $1 {1})+reload-sync($self --reload)+refresh-preview"; }

# Cached list first (instant), the fresh one replaces it once fetched.
"$self" --list --cached | SHELL=bash fzf --ansi --read0 --gap --delimiter '\t' --with-nth 2.. --nth 1 \
  --no-input --no-hscroll --layout reverse --info hidden --no-separator --no-scrollbar --highlight-line \
  --prompt '  ' --pointer '▌' --marker ' ' --gutter ' ' \
  --input-border rounded --input-label ' search (Enter or Esc: back to normal mode) ' --input-label-pos 3 \
  --list-border rounded --list-label-pos 3 \
  --footer "$footer" --footer-border rounded --footer-label ' keys ' --footer-label-pos 3 \
  --preview "$self --preview {1}" --preview-window 'right,60%,border-rounded,wrap' --preview-label-pos 3 \
  --bind "load:transform($self --on-load)" \
  --bind "focus:transform-preview-label($self --plabel {1})" \
  --bind "ctrl-a:execute-silent($self --prefix),G:transform($self --G)" \
  --bind "j:down,k:up,g:first,J:preview-down,K:preview-up,ctrl-d:preview-half-page-down,ctrl-u:preview-half-page-up" \
  --bind "1:execute-silent($self --mode overview)+refresh-preview+transform-preview-label($self --plabel {1})" \
  --bind "2:execute-silent($self --mode diff)+refresh-preview+transform-preview-label($self --plabel {1})" \
  --bind "3:execute-silent($self --mode checks)+refresh-preview+transform-preview-label($self --plabel {1})" \
  --bind "4:execute-silent($self --mode comments)+refresh-preview+transform-preview-label($self --plabel {1})" \
  --bind "tab:execute-silent($self --next-mode)+refresh-preview+transform-preview-label($self --plabel {1})" \
  --bind "f:execute-silent($self --next-filter)+reload-sync($self --list --cached)" \
  --bind "R:execute-silent(rm -f \"\$STATE\"/prefetched-*)+reload-sync($self --reload)+refresh-preview" \
  --bind "m:$(act merge),a:$(act approve),r:$(act request),c:$(act comment),x:$(act close),o:$(act checkout),d:$(act draft)" \
  --bind "y:execute-silent($self --copy {1})" \
  --bind "b:execute-silent(gh pr view {1} -R \"\$REPO\" --web >/dev/null 2>&1 &)" \
  --bind "q:abort" \
  --bind "/:show-input+unbind($NORMAL_KEYS)" \
  --bind "esc:transform:[ \"\$FZF_INPUT_STATE\" = enabled ] && echo '$normal' || echo abort" \
  --bind "enter:transform:[ \"\$FZF_INPUT_STATE\" = enabled ] && echo '$normal' || echo \"execute($self --full {1})\"" \
  --color "bg:-1,bg+:#2A2D35,fg:#D7DDE6,fg+:#FFFFFF,hl:#D095A4,hl+:#D095A4" \
  --color "border:#D095A4,label:#D095A4,prompt:#D095A4,pointer:#D095A4,info:#6C7086,query:#D7DDE6" \
  --color "input-border:#D095A4,list-border:#3B4048,list-label:#D095A4,footer-border:#3B4048,footer-label:#6C7086" \
  --color "preview-border:#3B4048,preview-label:#6C7086" >/dev/null
exit 0
