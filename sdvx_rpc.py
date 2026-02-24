import sys
import os
import subprocess
import re
import time
import threading
from pypresence import Presence

# --- CONFIGURATION ---
CLIENT_ID = '1475931399554076875' 
GAME_EXECUTABLE = "spice64.exe" 

# --- IMAGE ASSETS ---
# Keys must match assets uploaded to Discord Developer Portal
IMG_DEFAULT = "nabla_logo"
IMG_MENU    = "nabla_logo"
IMG_PLAYING = "nabla_logo"

# --- THREAD VARIABLES ---
desired_rpc = {}
last_sent_rpc = {}

def print_logo():
    # Clear console
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # ANSI Colors for Nabla Theme
    L_GRN = "\033[92m" # Light Green
    D_GRN = "\033[32m" # Dark Green
    P = "\033[38;2;88;101;242m" # Discord Blurple
    R = "\033[0m"  # Reset

    # ASCII Art construction with new color scheme
    l1 = f"   {L_GRN}____                  {D_GRN}__                      {R}"
    l2 = f"  {L_GRN}/ __/__  __ _____  {D_GRN}___/ /                      {R}"
    l3 = f" {L_GRN}_\ \/ _ \/ // / _ \{D_GRN}/ _  /                        {R}"
    l4 = f"{L_GRN}/___/\___/\_,_/_//_/{D_GRN}\_,_/                        {R}"
    
    l5 = f"           {L_GRN}_   __{D_GRN}     ____                       {R}"
    l6 = f"          {L_GRN}| | / /__{D_GRN}  / / /______ __              {R}"
    l7 = f"          {L_GRN}| |/ / _ \{D_GRN}/ / __/ -_) \ /              {R}"
    l8 = f"          {L_GRN}|___/\___/{D_GRN}_/\__/\__/_\_\              {R}"
    
    l9  = f"{P}   ___  _                     __   __  ___  _____ {R}"
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

def get_safe_string(text):
    """ Prevents Discord RPC crash by ensuring text is at least 2 chars long """
    if not text: return "..."
    text = str(text).strip()
    if len(text) < 2:
        return text + " "
    return text

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
                song_name = name.strip()
                if len(song_name) == 1:
                    song_name = song_name + " "
                song_map[int(mid)] = song_name
            except: 
                pass
    except: 
        pass
    return song_map

def connect_discord():
    """ Establishes connection with Discord RPC. """
    for _ in range(3):
        try:
            rpc = Presence(CLIENT_ID)
            rpc.connect()
            return rpc
        except:
            time.sleep(1)
    return None

def get_image_key(state):
    """ Returns the image key based on game state. """
    if state in ["Menu", "Selecting", "MyRoom"]:
        return IMG_MENU
    elif state == "Playing":
        return IMG_PLAYING
    return IMG_DEFAULT

def rpc_updater_thread(rpc_conn):
    """ Background thread to handle Discord's rate limit smartly without lagging the UI """
    global last_sent_rpc, desired_rpc
    
    while True:
        if rpc_conn and desired_rpc != last_sent_rpc:
            target_rpc = desired_rpc.copy()
            
            # Extract base states to see if it's a major scene change
            old_state = last_sent_rpc.get("state", "")
            new_state = target_rpc.get("state", "")
            
            old_base = old_state.split(":")[0].split(",")[0]
            new_base = new_state.split(":")[0].split(",")[0]
            
            is_major_change = (old_base != new_base)
            
            # If it's just scrolling songs (same menu), wait 1.5s to avoid rate limit bans
            if not is_major_change:
                time.sleep(1.5)
            
            # Send update if state is still the same after waiting OR if it was a major change
            if is_major_change or (desired_rpc == target_rpc):
                try:
                    rpc_conn.update(**target_rpc)
                    last_sent_rpc = target_rpc.copy()
                except Exception:
                    # If Discord still hits rate limit, cool down silently
                    time.sleep(2)
        else:
            # Ultra-fast polling when idle
            time.sleep(0.1)

def main():
    global desired_rpc
    print_logo()

    if not os.path.exists(GAME_EXECUTABLE):
        print(f"\n[ERROR] Could not find {GAME_EXECUTABLE}")
        print(f"Please place this file in the game folder.")
        input("Press Enter to exit...")
        return

    song_map = load_song_map()
    rpc = connect_discord()
    
    try:
        # Launch game process
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
    start_time = int(time.time())

    # Set Initial RPC State
    desired_rpc = {
        "state": "In Menu",
        "details": "Sound Voltex",
        "large_image": IMG_MENU,
        "large_text": "Nabla \u2207",
        "start": start_time
    }

    # Start the async background updater
    if rpc:
        t = threading.Thread(target=rpc_updater_thread, args=(rpc,), daemon=True)
        t.start()

    # Log Monitoring Loop
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
                    if current_state == "Menu":
                        current_state = "MyRoom"
                        desired_rpc = {
                            "state": f"My Room, {play_mode}",
                            "details": "Sound Voltex",
                            "large_image": IMG_MENU,
                            "large_text": "Nabla \u2207"
                        }

            # --- 2. DETECT HEXA DIVER ---
            if "LoadingIFS" in line and "hexa_diver" in line and "blue" in line:
                if active_event != "Hexa Diver":
                    active_event = "Hexa Diver"
                    current_song = "Browsing..." 
                    current_state = "Selecting"
                    
                    details_txt = f"{active_event}"
                    if play_mode: details_txt += f" ({play_mode})"
                    desired_rpc = {
                        "state": "Choosing Song...", 
                        "details": details_txt, 
                        "large_image": IMG_MENU, 
                        "large_text": "Nabla \u2207"
                    }

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
                        
                        if song_name and song_name != current_song:
                            current_song = song_name
                            large_text_safe = get_safe_string(current_song)
                            
                            if current_state == "Playing":
                                details_txt = "Playing Sound Voltex"
                                if active_event: details_txt = f"Playing {active_event}"
                                if play_mode: details_txt += f" ({play_mode})"
                                
                                desired_rpc = {
                                    "state": f"Playing: {current_song}",
                                    "details": details_txt,
                                    "large_image": get_image_key("Playing"),
                                    "large_text": large_text_safe,
                                    "start": start_time
                                }
                            elif current_state == "Selecting":
                                details_txt = "Selecting Song"
                                if active_event: details_txt = f"Selecting {active_event}"
                                if play_mode: details_txt += f" ({play_mode})"

                                desired_rpc = {
                                    "state": f"Selecting: {current_song}",
                                    "details": details_txt,
                                    "large_image": get_image_key("Selecting"),
                                    "large_text": large_text_safe
                                }
                    except: pass

            # --- 4. DETECT STATES ---
            
            # My Room (Character/Valkyrie selection)
            if "in MYROOM_SCENE" in line:
                if current_state != "MyRoom":
                    current_state = "MyRoom"
                    state_txt = f"My Room, {play_mode}" if play_mode else "My Room"
                    
                    desired_rpc = {
                        "state": state_txt,
                        "details": "Sound Voltex",
                        "large_image": IMG_MENU,
                        "large_text": "Nabla \u2207"
                    }

            # Selecting
            elif "in MUSICSELECT" in line:
                if active_event == "Hexa Diver" and "ms_sel" in line: 
                     active_event = ""

                if current_state != "Selecting":
                    current_state = "Selecting"
                    
                    details_txt = "Selecting Song"
                    if active_event: details_txt = f"Selecting {active_event}"
                    if play_mode: details_txt += f" ({play_mode})"
                    
                    state_txt = f"Selecting: {current_song}"
                    if current_song in ["Browsing...", "..."]: 
                        state_txt = "Choosing Song..."

                    large_text_safe = get_safe_string(current_song) if current_song not in ["Browsing...", "..."] else "Nabla \u2207"

                    desired_rpc = {
                        "state": state_txt,
                        "details": details_txt,
                        "large_image": get_image_key("Selecting"),
                        "large_text": large_text_safe
                    }

            # Playing
            elif "Attach: in ALTERNATIVE_GAME_SCENE" in line or "Attach: in GAME_SCENE" in line:
                if current_state != "Playing":
                    current_state = "Playing"
                    start_time = int(time.time())
                    
                    details_txt = "Playing Sound Voltex"
                    if active_event: details_txt = f"Playing {active_event}"
                    if play_mode: details_txt += f" ({play_mode})"
                    
                    txt = f"Playing: {current_song}"
                    if current_song in ["Browsing...", "..."]: 
                        txt = "Loading..."

                    large_text_safe = get_safe_string(current_song) if current_song not in ["Browsing...", "..."] else "Nabla \u2207"

                    desired_rpc = {
                        "state": txt,
                        "details": details_txt,
                        "large_image": get_image_key("Playing"),
                        "large_text": large_text_safe,
                        "start": start_time
                    }

            # Results
            elif "in RESULT_SCENE" in line and "T_RESULT_SCENE" not in line:
                if current_state != "Results":
                    current_state = "Results"
                    
                    details_txt = "Sound Voltex"
                    if active_event: details_txt = f"{active_event}"
                    if play_mode: details_txt += f" ({play_mode})"
                    
                    large_text_safe = get_safe_string(current_song) if current_song not in ["Browsing...", "..."] else "Nabla \u2207"

                    desired_rpc = {
                        "state": f"Result: {current_song}",
                        "details": details_txt,
                        "large_image": get_image_key("Playing"),
                        "large_text": large_text_safe
                    }

            # Session End / Total Results
            elif "Attach: in T_RESULT_SCENE" in line:
                 if current_state != "TotalResults":
                    current_state = "TotalResults"
                    
                    desired_rpc = {
                        "state": "Session Results",
                        "details": "Sound Voltex",
                        "large_image": IMG_MENU,
                        "large_text": "Nabla \u2207"
                    }

            # Return to Main Menu
            elif "Attach: in GAMEOVER" in line or "Attach: in CARD_OUT_SCENE" in line or "Attach: in TITLEDEMO" in line:
                if current_state != "Menu":
                    current_state = "Menu"
                    play_mode = "" 
                    active_event = ""
                    
                    desired_rpc = {
                        "state": "In Menu",
                        "details": "Sound Voltex",
                        "large_image": IMG_MENU,
                        "large_text": "Nabla \u2207",
                        "start": int(time.time())
                    }

        except Exception:
            pass

if __name__ == "__main__":
    main()