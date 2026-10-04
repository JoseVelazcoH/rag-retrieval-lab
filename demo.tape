# Vertical social format: 1080x1350 (4:5). Font size 30 gives ~55 columns.
Output demo.mp4
Output demo.gif

Set Shell "bash"
Set FontFamily "JetBrains Mono"
Set FontSize 30
Set Width 1080
Set Height 1350
Set Padding 18
Set WindowBar Colorful
Set TypingSpeed 45ms
Set Framerate 20
Set Theme { "name": "MacTerminalPro", "black": "#000000", "red": "#c23621", "green": "#25bc24", "yellow": "#adad27", "blue": "#492ee1", "magenta": "#d338d3", "cyan": "#33bbc8", "white": "#cbcccd", "brightBlack": "#818383", "brightRed": "#fc391f", "brightGreen": "#31e722", "brightYellow": "#eaec23", "brightBlue": "#5833ff", "brightMagenta": "#f935f8", "brightCyan": "#14f0f0", "brightWhite": "#e9ebeb", "background": "#141414", "foreground": "#f2f2f2", "selection": "#414141", "cursor": "#b4b4b4" }

# Hidden setup: macOS-like prompt, venv on PATH, warm the OS file cache.
Hide
Type "export PS1='jose@MacBook-Pro ~ % ' && source .venv/bin/activate && clear"
Enter
Type "search 'warm up' > /dev/null && clear"
Enter
Wait+Line@120s /%\s*$/
Sleep 1s
Show

Type 'search "timeout 504 nginx" --bm25'
Sleep 400ms
Enter
Wait+Screen@90s /\d+ ms/
Sleep 6s
Hide
Type "clear"
Enter
Wait+Line /%\s*$/
Show

Type 'search "the page takes forever and then crashes" --vector'
Sleep 400ms
Enter
Wait+Screen@90s /\d+ ms/
Sleep 6s
