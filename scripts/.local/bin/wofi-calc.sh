#!/bin/bash
# A simple calculator/converter wrapper for wofi

INPUT=$(wofi --show dmenu --prompt "Math / Currency (e.g. 100 USD to EUR)..." --height 100)

if [ -n "$INPUT" ]; then
    # Calculate the result
    RESULT=$(qalc -t "$INPUT")
    
    # Show the result in Wofi, and if selected, copy to Wayland clipboard
    echo "$RESULT" | wofi --show dmenu --prompt "Result (Enter to copy):" --height 150 | wl-copy
fi
