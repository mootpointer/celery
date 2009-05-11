set workers to {"h8.opera.com", "h9.opera.com", "h10.opera.com"}
tell application "iTerm"
    activate
    set myterm to (make new terminal)
    tell myterm
        set number of columns to 80
        set number of rows to 50
        repeat with workerhost in workers
            set worker to (make new session at the end of sessions)
            tell worker
                set name to workerhost
                set foreground color to "white"
                set background color to "black"
                set transparency to 0.1
                exec command "/bin/sh -i"
                write text "ssh root@" & workerhost & " 'tail -f /var/log/celeryd.log'"
            end tell
        end repeat
        tell the first session
            activate
        end tell
    end tell
end tell
