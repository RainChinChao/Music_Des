on run
    set rootFile to POSIX path of (path to resource "project_root.txt")
    set rootPath to do shell script "/bin/cat " & quoted form of rootFile
    try
        do shell script "/bin/bash " & quoted form of (rootPath & "/run_gui_background.sh")
    on error errorMessage
        display dialog "GenAI MIDI Studio could not start." & return & return & errorMessage buttons {"OK"} default button "OK" with icon stop
    end try
end run
