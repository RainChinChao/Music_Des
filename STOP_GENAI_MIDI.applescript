on run
    set rootFile to POSIX path of (path to resource "project_root.txt")
    set rootPath to do shell script "/bin/cat " & quoted form of rootFile
    try
        do shell script "/bin/bash " & quoted form of (rootPath & "/STOP_GENAI_MIDI.command")
        display notification "Background web server stopped." with title "GenAI MIDI Studio"
    on error errorMessage
        display dialog "GenAI MIDI Studio could not be stopped." & return & return & errorMessage buttons {"OK"} default button "OK" with icon stop
    end try
end run
