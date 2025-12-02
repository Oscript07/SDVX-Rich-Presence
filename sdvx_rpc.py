import sys
import os
import subprocess
import re
import time
from pypresence import Presence

# --- CONFIGURATION ---
CLIENT_ID = '1444878192463839412' 
GAME_EXECUTABLE = "spice64.exe" 

# --- IMAGE ASSETS ---
# Keys must match assets uploaded to Discord Developer Portal
IMG_DEFAULT = "sdvx_logo"
IMG_MENU    = "sdvx_logo"
IMG_PLAYING = "sdvx_logo"

def print_logo():
    # Clear console
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # ANSI Colors
    C = "\033[96m" # Cyan
    M = "\033[95m" # Magenta
    P = "\033[38;2;88;101;242m" # Discord Blurple/Purple
    R = "\033[0m"  # Reset

    # ASCII Art construction
    l1 = f"   {C}____                  {M}__                      {R}"
    l2 = f"  {C}/ __/__  __ _____  {M}___/ /                      {R}"
    l3 = f" {C}_\ \/ _ \/ // / _ \{M}/ _  /                        {R}"
    l4 = f"{C}/___/\___/\_,_/_//_/{M}\_,_/                        {R}"
    
    l5 = f"           {C}_    __{M}      ____                     {R}"
    l6 = f"          {C}| | / /__{M}  / / /______ __              {R}"
    l7 = f"          {C}| |/ / _ \{M}/ / __/ -_) \ /              {R}"
    l8 = f"          {C}|___/\___/{M}_/\__/\__/_\_\              {R}"
    
    l9  = f"{P}   ___  _                          __  ___  _____ {R}"
    l10 = f"{P}  / _ \(_)__ _______  _______/ / / _ \/ _ \/ ___/ {R}"
    l11 = f"{P} / // / (_-</ __/ _ \/ __/ _  / / , _/ ___/ /__   {R}"
    l12 = f"{P}/____/_/___/\__/\___/_/  \_,_/ /_/|_/_/   \___/   {R}"

    print(l1); print(l2); print(l3); print(l4)
    print(l5); print(l6); print(l7); print(l8)
    print(l9); print(l10); print(l11); print(l12)
    print(f"\n              {P}[ Active ]{R}")

def find_music_db():
    """ Locates the music database file. """
    possible_paths = [
        "data/others/music_db.xml", 
        "../data/others/music_db.xml", 
        "others/music_db.xml", 
        "music_db.xml"
    ]
    for path in possible_paths:
        if os.path.exists(path): return path
    return None

def load_song_map():
    """ Parses XML to map Song IDs to Titles. """
    xml_path = find_music_db()
    if not xml_path: return {}
    
    song_map = {}
    try:
        content = ""
        # Try different encodings
        for enc in ['cp932', 'shift_jis', 'utf-8']:
            try:
                with open(xml_path, 'r', encoding=enc, errors='ignore') as f:
                    content = f.read()
                if "<music" in content: break
            except: continue
            
        # Regex parsing
        blocks = re.findall(r'<music id="(\d+)">.*?<title_name>(.*?)</title_name>', content, re.DOTALL)
        for mid, name in blocks:
            try: 
                song_map[int(mid)] = name.strip()
            except: 
                pass
    except: 
        pass
    return song_map

def connect_discord():
    try:
        rpc = Presence(CLIENT_ID)
        rpc.connect()
        return rpc
    except:
        return None

def get_image_key(state):
    """ Returns the image key based on game state. """
    if state == "Menu" or state == "Selecting":
        return IMG_MENU
    elif state == "Playing":
        return IMG_PLAYING
    return IMG_DEFAULT

def main():
    print_logo()

    if not os.path.exists(GAME_EXECUTABLE):
        print(f"\n[ERROR] Could not find {GAME_EXECUTABLE}")
        print(f"Please place this file in the game folder.")
        input("Press Enter to exit...")
        return

    song_map = load_song_map()
    rpc = connect_discord()
    
    try:
        # Launch game
        process = subprocess.Popen(
            [GAME_EXECUTABLE],
            stdout=subprocess.PIPE,      
            stderr=subprocess.STDOUT,    
            stdin=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True,
            encoding='cp932',            
            errors='replace'
        )
    except Exception as e:
        print(f"\n[ERROR] Failed to launch game: {e}")
        input()
        return

    # State Variables
    current_song = "..."
    current_state = "Menu"
    play_mode = "" 
    active_event = ""
    start_time = time.time()

    if rpc: 
        rpc.update(state="In Menu", details="Sound Voltex", large_image=IMG_MENU, start=start_time)

    while True:
        if process.poll() is not None:
            break

        try:
            line = process.stdout.readline()
            if not line: continue
            line = line.strip()

            # --- 1. DETECT PLAY MODE ---
            if "ea3_report_posev" in line and "/coin/kfc_game_s_" in line:
                new_mode = ""
                if "light" in line:           new_mode = "Light Start"
                elif "standard" in line:      new_mode = "Normal Start"
                elif "standard_plus" in line: new_mode = "Normal Start"
                elif "premium" in line:       new_mode = "Premium Time"
                elif "blaster" in line:       new_mode = "Blaster Start"
                elif "paradise" in line:      new_mode = "Paradise Start"
                elif "arena" in line:         new_mode = "Arena Battle"
                elif "megamix" in line:       new_mode = "MegaMix Battle"
                
                if new_mode:
                    play_mode = new_mode

            # --- 2. DETECT HEXA DIVER ---
            # Enter
            if "LoadingIFS" in line and "hexa_diver" in line and "blue" in line:
                if active_event != "Hexa Diver":
                    active_event = "Hexa Diver"
                    current_song = "Browsing..." 
                    current_state = "Selecting"
                    
                    if rpc:
                        details_txt = f"{active_event}"
                        if play_mode: details_txt += f" ({play_mode})"
                        rpc.update(state="Choosing Song...", details=details_txt, large_image=IMG_MENU, large_text="Exceed Gear")

            # Exit
            if "LoadingIFS" in line and "ver06/ms_sel" in line:
                if active_event == "Hexa Diver":
                    active_event = ""

            # --- 3. DETECT SONG ---
            is_bg_load = "Loading /data/music/" in line and "_b.png" in line
            is_game_load = "Loading /data/music/" in line and ".png" in line and (current_state == "Playing" or active_event == "Hexa Diver")

            if is_bg_load or is_game_load:
                match = re.search(r'music/(\d+)_', line)
                if match:
                    try:
                        sid = int(match.group(1))
                        song_name = song_map.get(sid, str(sid))
                        
                        if song_name != current_song:
                            current_song = song_name
                            
                            if rpc:
                                img_key = get_image_key(current_state)
                                
                                if current_state == "Playing":
                                    details_txt = "Playing Sound Voltex"
                                    if active_event: details_txt = f"Playing {active_event}"
                                    if play_mode: details_txt += f" ({play_mode})"
                                    
                                    rpc.update(
                                        state=f"Playing: {current_song}",
                                        details=details_txt,
                                        large_image=img_key,
                                        large_text=current_song,
                                        start=start_time
                                    )
                                elif current_state == "Selecting":
                                    details_txt = "Selecting Song"
                                    if active_event: details_txt = f"Selecting {active_event}"
                                    if play_mode: details_txt += f" ({play_mode})"

                                    rpc.update(
                                        state=f"Selecting: {current_song}",
                                        details=details_txt,
                                        large_image=img_key,
                                        large_text=current_song
                                    )
                    except: pass

            # --- 4. DETECT STATES ---
            
            # Selecting
            if "in MUSICSELECT" in line:
                if active_event == "Hexa Diver" and "ms_sel" in line: 
                     active_event = ""

                if current_state != "Selecting":
                    current_state = "Selecting"
                    
                    details_txt = "Selecting Song"
                    if active_event: details_txt = f"Selecting {active_event}"
                    if play_mode: details_txt += f" ({play_mode})"
                    
                    state_txt = f"Selecting: {current_song}"
                    if current_song == "Browsing..." or current_song == "...": 
                        state_txt = "Choosing Song..."

                    img_key = get_image_key("Selecting")

                    if rpc:
                        rpc.update(state=state_txt, details=details_txt, large_image=img_key, large_text="Exceed Gear")

            # Playing
            if "in ALTERNATIVE_GAME_SCENE" in line:
                if current_state != "Playing":
                    current_state = "Playing"
                    start_time = time.time()
                    
                    details_txt = "Playing Sound Voltex"
                    if active_event: details_txt = f"Playing {active_event}"
                    if play_mode: details_txt += f" ({play_mode})"
                    
                    txt = f"Playing: {current_song}"
                    if current_song == "Browsing..." or current_song == "...": 
                        txt = "Loading..."

                    img_key = get_image_key("Playing")

                    if rpc:
                        rpc.update(state=txt, details=details_txt, large_image=img_key, large_text=current_song, start=start_time)

            # Results
            if "in RESULT_SCENE" in line:
                if current_state != "Results":
                    current_state = "Results"
                    
                    details_txt = "Sound Voltex"
                    if active_event: details_txt = f"{active_event}"
                    if play_mode: details_txt += f" ({play_mode})"
                    
                    img_key = get_image_key("Playing")

                    if rpc:
                        rpc.update(state=f"Result: {current_song}", details=details_txt, large_image=img_key, large_text=current_song, start=start_time)

            # Session End / Menu
            if "in T_RESULT_SCENE" in line:
                 if current_state != "TotalResults":
                    current_state = "TotalResults"
                    if rpc: 
                        rpc.update(state="Session Results", details="Sound Voltex", large_image=IMG_MENU)

            if "in GAMEOVER" in line or "in CARD_OUT_SCENE" in line or "in TITLEDEMO" in line:
                if current_state != "Menu":
                    current_state = "Menu"
                    play_mode = "" 
                    active_event = ""
                    if rpc:
                        rpc.update(state="In Menu", details="Sound Voltex", large_image=IMG_MENU, start=time.time())

        except Exception:
            pass

if __name__ == "__main__":
    main()