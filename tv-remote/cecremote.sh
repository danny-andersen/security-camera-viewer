#!/bin/bash
function keychar {
    parin1=$1 #first param; abc1
    parin2=$2 #second param; 0=a, 1=b, 2=c, 3=1, 4=a, ...
    parin2=$((parin2)) #convert to numeric
    parin1len=${#parin1} #length of parin1
    parin2pos=$((parin2 % parin1len)) #position mod
    char=${parin1:parin2pos:1} #char key to simulate
    if [ "$parin2" -gt 0 ]; then #if same key pressed multiple times, delete previous char; write a, delete a write b, delete b write c, ...
        xdotool key "BackSpace"
    fi
    #special cases for xdotool ( X Keysyms )
    if [ "$char" = " " ]; then char="space"; fi
    if [ "$char" = "." ]; then char="period"; fi
    if [ "$char" = "-" ]; then char="minus"; fi
    xdotool key $char
}
datlastkey=$(date +%s%N)
strlastkey=""
intkeychar=0
intmsbetweenkeys=2000 #two presses of a key sooner that this makes it delete previous key and write the next one (a->b->c->1->a->...)
intmousestartspeed=10 #mouse starts moving at this speed (pixels per key press)
intmouseacc=10 #added to the mouse speed for each key press (while holding down key, more key presses are sent from the remote)
intmousespeed=10

while read oneline
do
    keyline=$(echo $oneline | grep " key ")
    #echo $keyline --- debugAllLines
    if [ -n "$keyline" ]; then
        datnow=$(date +%s%N)
        datdiff=$((($datnow - $datlastkey) / 1000000)) #bla bla key pressed: previous channel (123)
        strkey=$(grep -oP '(?<=sed: ).*?(?= \()' <<< "$keyline") #bla bla key pres-->sed: >>previous channel<< (<--123)
        strstat=$(grep -oP '(?<=key ).*?(?=:)' <<< "$keyline") #bla bla -->key >>pressed<<:<-- previous channel (123)
        strpressed=$(echo $strstat | grep "pressed")
        strreleased=$(echo $strstat | grep "released")
        if [ -n "$strpressed" ]; then
            #echo $keyline --- debug
            if [ "$strkey" = "$strlastkey" ] && [ "$datdiff" -lt "$intmsbetweenkeys" ]; then
                intkeychar=$((intkeychar + 1)) #same key pressed for a different char
            else
                intkeychar=0 #different key / too far apart
            fi
            datlastkey=$datnow
            strlastkey=$strkey
            case "$strkey" in
                "channel up")
                    xdotool click 4 #mouse scroll up
                    ;;
                "channel down")
                    xdotool click 5 #mouse scroll down
                    ;;
                "channels list")
                    xdotool click 3 #right mouse button click"
                    ;;
                # "up")
                #     intpixels=$((-1 * intmousespeed))
                #     xdotool mousemove_relative -- 0 $intpixels #move mouse up
                #     intmousespeed=$((intmousespeed + intmouseacc)) #speed up
                #     ;;
                # "down")
                #     intpixels=$(( 1 * intmousespeed))
                #     xdotool mousemove_relative -- 0 $intpixels #move mouse down
                #     intmousespeed=$((intmousespeed + intmouseacc)) #speed up
                #     ;;
                # "left")
                #     intpixels=$((-1 * intmousespeed))
                #     xdotool mousemove_relative -- $intpixels 0 #move mouse left
                #     intmousespeed=$((intmousespeed + intmouseacc)) #speed up
                #     ;;
                # "right")
                #     intpixels=$(( 1 * intmousespeed))
                #     xdotool mousemove_relative -- $intpixels 0 #move mouse right
                #     intmousespeed=$((intmousespeed + intmouseacc)) #speed up
                #     ;;
                # "stop")
                #     ## with my remote I only got "STOP" as key released (auto-released), not as key pressed; see below
                #     echo Key Pressed: STOP
                #     ;;
                # *)
                #     echo Unrecognized Key Pressed: $strkey ; CEC Line: $keyline
                #     ;;
                    
            esac
        fi
        if [ -n "$strreleased" ]; then
            #echo $keyline --- debug
            if [ "$strkey" = "$strlastkey" ] && [ "$datdiff" -lt "$intmsbetweenkeys" ]; then
                intkeychar=$((intkeychar + 1)) #same key pressed for a different char
            else
                intkeychar=0 #different key / too far apart
            fi
            datlastkey=$datnow
            strlastkey=$strkey
            case "$strkey" in
                "1")
                    xdotool key "1"
                    ;;
                "2")
                    xdotool key "2"
                    ;;
                "3")
                    xdotool key "3"
                    ;;
                "4")
                    xdotool key "4"
                    ;;
                "5")
                    xdotool key "5"
                    ;;
                "6")
                    xdotool key "6"

                    ;;
                "7")
                    keychar "pqrs7" intkeychar
                    ;;
                "8")
                    keychar "tuv8" intkeychar
                    ;;
                "9")
                    keychar "wxyz9" intkeychar
                    ;;
                "0")
                    keychar " 0.-" intkeychar
                    ;;
                "F2") 
                    xdotool key "F2" # Red
                    ;;
                "F3") 
                    xdotool key "F3" # Green
                    ;;
                "F4") 
                    xdotool key "F4" # Yellow
                    ;;
                "F1")
                    xdotool key "F1" # Blue
                    ;;
                "previous channel")
                    xdotool key "Return" #Enter
                    ;;
                "select")
                    xdotool key "Return" #Enter
                    ;;
                "return")
                    xdotool key "BackSpace"
                    ;;
                "exit")
                    xdotool key "BackSpace"
                    ;;
                "stop")
                    xdotool key "Pause"
                    ;;
                "rewind")
                    echo Key Pressed: REWIND
                    ;;
                "pause")
                    xdotool key "Pause"
                    ;;
                "Fast forward")
                    echo Key Pressed: FAST FORWARD
                    ;;
                "play")
                    xdotool key "Pause"
                    ;;
                "down")
                    #Use vi like keys for up/down/left/right to avoid conflicts with other keybindings
                    xdotool key "j"
                    ;;
                "up")
                    xdotool key "k"
                    ;;
                "left")
                    xdotool key "h"
                    ;;
                "right")
                    xdotool key "l"
                    ;;
                *)
                    echo Unrecognized Key Released: $strkey ; CEC Line: $keyline
                    ;;
                    
            esac
        fi
    fi
done
