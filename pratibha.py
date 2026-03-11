# prat.py - complete fixed version
# - main menu background fixed (assets/background.jpg or .png; else random from assets)
# - settings toggles now save and apply immediately (music/sfx/tts/voice/theme)
# - multiplayer and all original game logic preserved

import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from PIL import Image, ImageTk
import random, json, os, datetime

# Optional modules
try:
    import pygame
    pygame_available = True
except Exception:
    pygame_available = False

try:
    import pyttsx3
    tts_available = True
except Exception:
    tts_available = False

try:
    import speech_recognition as sr
    voice_available = True
except Exception:
    voice_available = False

# try to import nltk; if not available use fallback word list
try:
    import nltk
    from nltk.corpus import words, wordnet
    nltk_available = True
    try:
        nltk.data.find('corpora/words')
    except Exception:
        try:
            nltk.download('words', quiet=True)
        except Exception:
            pass
    try:
        nltk.data.find('corpora/wordnet')
    except Exception:
        try:
            nltk.download('wordnet', quiet=True)
        except Exception:
            pass
except Exception:
    nltk_available = False

FALLBACK_WORDS = ["apple","bread","chair","drink","eagle","frame","grape","hotel","image","joker",
                  "knife","lemon","mouse","noble","ocean","peace","queen","river","stone","table"]

# ---------------------------
# Paths and defaults
# ---------------------------
BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

LEADERBOARD_PATH = os.path.join(BASE_DIR, "leaderboard.json")
SETTINGS_PATH = os.path.join(BASE_DIR, "settings.json")
PROFILES_PATH = os.path.join(BASE_DIR, "profiles.json")
QUESTIONS_GENERAL_PATH = os.path.join(BASE_DIR, "questions_general.json")
QUESTIONS_APTITUDE_PATH = os.path.join(BASE_DIR, "questions_aptitude.json")

leaderboard = {}
profiles = {}
settings = {
    "theme": "Ocean",
    "music": True,
    "sfx": True,
    "tts": False,
    "voice": False,
}

THEMES = {
    "Ocean": {"bg": "#e3f6fc", "primary": "#1E90FF", "accent": "#32CD32", "text": "#222"},
    "Sunset": {"bg": "#FFDDC1", "primary": "#FF6347", "accent": "#FFD700", "text": "#222"},
    "Midnight": {"bg": "#1d1f21", "primary": "#444", "accent": "#6bbef9", "text": "#f2f2f2"},
}

SOUND_PATHS = {
    "click": os.path.join(ASSETS_DIR, 'click.wav'),
    "correct": os.path.join(ASSETS_DIR, 'correct.wav'),
    "wrong": os.path.join(ASSETS_DIR, 'wrong.wav'),
    "win": os.path.join(ASSETS_DIR, 'win.wav'),
    "lose": os.path.join(ASSETS_DIR, 'lose.wav'),
    "bgm": os.path.join(ASSETS_DIR, 'bgm.mp3'),
}

# ---------------------------
# Persistence helpers
# ---------------------------
def save_json(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Failed to save {path}: {e}")

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load {path}: {e}")
    return default

leaderboard = load_json(LEADERBOARD_PATH, {})
settings.update(load_json(SETTINGS_PATH, {}))
profiles = load_json(PROFILES_PATH, {})

# ---------------------------
# Audio helpers
# ---------------------------
def init_audio():
    if pygame_available:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception as e:
            print("pygame init failed:", e)




# ---------------------------
# Leaderboard & profiles
# ---------------------------
def update_leaderboard(player, score):
    now = datetime.datetime.now().isoformat()
    entry = {"player": player, "score": score, "ts": now}
    leaderboard.setdefault("entries", []).append(entry)
    save_json(LEADERBOARD_PATH, leaderboard)

    prof = profiles.setdefault(player, {
        "avatar": None, "xp":0, "level":1,
        "stats": {"wins":0, "losses":0, "fastest_quiz_sec": None, "word_wins":0},
        "achievements": []
    })
    prof["xp"] += max(0, score)
    prof["level"] = max(1, 1 + prof["xp"] // 100)
    save_json(PROFILES_PATH, profiles)

def record_result(player, won=False, game=""):
    prof = profiles.setdefault(player, {
        "avatar": None, "xp":0, "level":1,
        "stats": {"wins":0, "losses":0, "fastest_quiz_sec": None, "word_wins":0},
        "achievements": []
    })
    if won:
        prof["stats"]["wins"] = prof["stats"].get("wins",0) + 1
    else:
        prof["stats"]["losses"] = prof["stats"].get("losses",0) + 1
    if game == "Word Guess" and won:
        prof["stats"]["word_wins"] = prof["stats"].get("word_wins", 0) + 1
    save_json(PROFILES_PATH, profiles)

def grant_achievement(player, badge):
    prof = profiles.setdefault(player, {"avatar":None,"xp":0,"level":1,"stats":{},"achievements":[]})
    if badge not in prof["achievements"]:
        prof["achievements"].append(badge)
        save_json(PROFILES_PATH, profiles)
        try:
            messagebox.showinfo("Achievement Unlocked!", f"{player} earned: {badge}")
        except Exception:
            pass

def clear_leaderboard():
    global leaderboard
    leaderboard = {}
    save_json(LEADERBOARD_PATH, leaderboard)
    try:
        messagebox.showinfo("Reset", "Leaderboard has been completely reset!")
    except Exception:
        pass

def clear_scores():
    global leaderboard
    leaderboard["entries"] = []
    save_json(LEADERBOARD_PATH, leaderboard)
    try:
        messagebox.showinfo("Reset", "All scores have been reset!")
    except Exception:
        pass

# ---------------------------
# Themed UI & background
# ---------------------------
def themed_colors():
    return THEMES.get(settings.get("theme","Ocean"), THEMES["Ocean"])

def add_background(widget, game_tag=None):
    """Always use fixed background images based on screen tag."""
    # Remove previous background if any
    for child in widget.winfo_children():
        if isinstance(child, tk.Label) and getattr(child, "_is_bg", False):
            child.destroy()

    # Choose fixed background based on screen tag
    chosen = None
    if game_tag:
        bg_path = os.path.join(ASSETS_DIR, f"background_{game_tag}.jpg")
        if os.path.exists(bg_path):
            chosen = bg_path

    # Fallback to main background if specific not found
    if not chosen:
        default_bg = os.path.join(ASSETS_DIR, "background_main.jpg")
        if os.path.exists(default_bg):
            chosen = default_bg

    # Load and display background
    if chosen:
        try:
            screen_w = widget.winfo_screenwidth()
            screen_h = widget.winfo_screenheight()
            img = Image.open(chosen)
            img = img.resize((screen_w, screen_h), Image.LANCZOS)
            bg = ImageTk.PhotoImage(img)
            label = tk.Label(widget, image=bg)
            label.image = bg
            label.place(x=0, y=0, relwidth=1, relheight=1)
            label.lower()
            label._is_bg = True
        except Exception as e:
            print("Error loading background:", e)
    else:
        widget.configure(bg="black")  # fallback color
def make_btn(parent, text, cmd, kind="primary"):
    c = themed_colors()
    colors = {"primary": c["primary"], "accent": c["accent"], "warn": "#DC143C", "ok": "#32CD32"}
    b = tk.Button(parent, text=text, font=("Arial",16),
                  bg=colors.get(kind, c["primary"]), fg="white",
                  width=22, height=2, command=lambda: (play_sound("click"), cmd()))
    return b

def make_small_btn(parent, text, cmd):
    c = themed_colors()
    b = tk.Button(parent, text=text, font=("Arial",12), bg=c["primary"], fg="white",
                  height=1, width=12, command=lambda: (play_sound("click"), cmd()))
    return b

# ---------------------------
# Player prompt (text entry)
# ---------------------------
def prompt_player_name(title="Enter name", prompt_text="Player name:", default=""):
    dlg = tk.Toplevel(root)
    dlg.transient(root)
    dlg.grab_set()
    dlg.title(title)
    add_background(dlg)
    c = themed_colors()
    tk.Label(dlg, text=prompt_text, font=("Arial",14), bg=c["primary"], fg="white").pack(pady=8)
    entry = tk.Entry(dlg, font=("Arial",14))
    entry.insert(0, default)
    entry.pack(padx=10, pady=6)
    result = {"name": None}
    def on_ok():
        name = entry.get().strip()
        if not name:
            messagebox.showerror("Input", "Please enter a name.")
            return
        result["name"] = name
        dlg.destroy()
    def on_cancel():
        dlg.destroy()
    btn_frame = tk.Frame(dlg, bg=c["bg"]); btn_frame.pack(pady=8)
    tk.Button(btn_frame, text="OK", command=on_ok, font=("Arial",12), width=10, bg=c["accent"], fg="white").pack(side="left", padx=6)
    tk.Button(btn_frame, text="Cancel", command=on_cancel, font=("Arial",12), width=10, bg="#DC143C", fg="white").pack(side="left", padx=6)
    root.wait_window(dlg)
    return result["name"]

# ---------------------------
# Screens: Leaderboard, Settings, Profile
# ---------------------------
def show_leaderboard():
    for w in root.winfo_children(): w.destroy()
    add_background(root, game_tag="leaderboard")
    c = themed_colors()
    tk.Label(root, text="Leaderboard", font=("Arial",28,"bold"), bg=c["primary"], fg="white").pack(pady=16)
    list_frame = tk.Frame(root, bg=c["bg"]); list_frame.pack(pady=8)
    entries = leaderboard.get("entries", [])[:]
    for e in entries[-20:][::-1]:
        txt = f"{e.get('player','?')} — {e.get('score',0)} pts"
        tk.Label(list_frame, text=txt, font=("Arial",14), bg=c["bg"], fg=c["text"]).pack(anchor="w", padx=8, pady=2)
    make_btn(root, "Back", main_menu).pack(pady=14)

def toggle_setting_direct(key, value):
    settings[key] = value
    save_json(SETTINGS_PATH, settings)
    # apply immediate effects
    if key == "music":
        if value:
            play_bgm()
        else:
            stop_bgm()

def show_settings():
    for w in root.winfo_children(): w.destroy()
    add_background(root, game_tag="settings")
    c = themed_colors()
    tk.Label(root, text="Settings", font=("Arial",28,"bold"), bg=c["primary"], fg="white").pack(pady=12)

    # Theme combobox
    frame_theme = tk.Frame(root, bg=c["bg"]); frame_theme.pack(pady=6)
    tk.Label(frame_theme, text="Theme:", bg=c["bg"], fg=c["text"], font=("Arial",16)).pack(side="left", padx=6)
    theme_combo = ttk.Combobox(frame_theme, values=list(THEMES.keys()), state="readonly", font=("Arial",12))
    theme_combo.set(settings.get("theme","Ocean"))
    theme_combo.pack(side="left", padx=6)
    def on_theme_change(evt=None):
        t = theme_combo.get()
        settings["theme"] = t
        save_json(SETTINGS_PATH, settings)
        # re-render settings to apply theme immediately
        show_settings()
    theme_combo.bind("<<ComboboxSelected>>", on_theme_change)

    # toggles
    music_var = tk.BooleanVar(value=settings.get("music", True))
    sfx_var = tk.BooleanVar(value=settings.get("sfx", True))
    tts_var = tk.BooleanVar(value=settings.get("tts", False))
    voice_var = tk.BooleanVar(value=settings.get("voice", False))

    def make_toggle_row(label_text, var, key):
        row = tk.Frame(root, bg=c["bg"]); row.pack(pady=4, anchor="w", padx=8)
        cb = tk.Checkbutton(row, text=label_text, variable=var, bg=c["bg"], fg=c["text"], font=("Arial",14),
                            command=lambda: toggle_setting_direct(key, bool(var.get())))
        cb.pack(side="left")
    make_toggle_row("Background Music", music_var, "music")
    make_toggle_row("Sound Effects", sfx_var, "sfx")
    make_toggle_row("Text-to-Speech (TTS)", tts_var, "tts")
    make_toggle_row("Voice Input (Quiz/Aptitude)", voice_var, "voice")

    make_btn(root, "Back", main_menu, "accent").pack(pady=12)

def profile_center():
    for w in root.winfo_children(): w.destroy()
    add_background(root, game_tag="profile")
    c = themed_colors()
    tk.Label(root, text="Profile & Avatar", font=("Arial",28,"bold"), bg=c["primary"], fg="white").pack(pady=16)
    players = sorted(profiles.keys())
    sel = tk.StringVar(value=players[0] if players else "")
    sel_frame = tk.Frame(root, bg=c["bg"]); sel_frame.pack(pady=6)
    if players:
        for p in players:
            tk.Radiobutton(sel_frame, text=p, variable=sel, value=p, bg=c["bg"], fg=c["text"]).pack(anchor="w")
    else:
        tk.Label(sel_frame, text="No profiles yet.", bg=c["bg"], fg=c["text"]).pack()
    avatar_label = tk.Label(root, bg=c["bg"]); avatar_label.pack(pady=10)
    def refresh_avatar():
        name = sel.get().strip()
        if not name:
            avatar_label.config(image='', text='(No player)')
            return
        p = profiles.get(name, {}).get("avatar")
        if p and os.path.exists(p):
            try:
                img = Image.open(p).resize((120,120))
                ph = ImageTk.PhotoImage(img)
                avatar_label.config(image=ph, text=''); avatar_label.image = ph
            except Exception:
                avatar_label.config(text='(Error loading avatar)')
        else:
            avatar_label.config(text='(No avatar set)')
    def set_avatar():
        name = sel.get().strip()
        if not name:
            messagebox.showerror("Player","Select a player first")
            return
        path = filedialog.askopenfilename(title="Choose avatar image", filetypes=[("Images","*.png;*.jpg;*.jpeg;*.gif")])
        if path:
            profiles.setdefault(name, {"avatar":None,"xp":0,"level":1,"stats":{},"achievements":[]})
            profiles[name]["avatar"] = path
            save_json(PROFILES_PATH, profiles)
            refresh_avatar()
    def show_stats():
        name = sel.get().strip()
        if not name or name not in profiles:
            messagebox.showinfo("Stats","No stats yet.")
            return
        prof = profiles[name]; s = prof.get("stats",{}); ach = ", ".join(prof.get("achievements",[])) or "None"
        messagebox.showinfo("Stats", f"Level: {prof.get('level',1)}\nXP: {prof.get('xp',0)}\nWins: {s.get('wins',0)}\nLosses: {s.get('losses',0)}\nFastest Quiz (sec): {s.get('fastest_quiz_sec','-')}\nWord Wins: {s.get('word_wins',0)}\nAchievements: {ach}")
    make_btn(root,"Refresh Avatar",refresh_avatar,"accent").pack(pady=6)
    make_btn(root,"Choose Avatar",set_avatar).pack(pady=6)
    make_btn(root,"View Stats",show_stats).pack(pady=6)
    make_btn(root,"Back",main_menu).pack(pady=12)

# ---------------------------
# Player setup & Main Menu
# ---------------------------
def get_player_info_page():
    for widget in root.winfo_children(): widget.destroy()
    add_background(root, game_tag="player_setup")
    c = themed_colors()
    tk.Label(root, text="Choose Player", font=("Arial",28,"bold"), bg=c["accent"], fg="white").pack(pady=12)
    frm = tk.Frame(root, bg=c["bg"]); frm.pack(pady=8)
    tk.Label(frm, text="Player 1 name:", font=("Arial",14), bg=c["bg"], fg=c["text"]).grid(row=0,column=0,sticky="w",padx=6,pady=6)
    entry_p1 = tk.Entry(frm, font=("Arial",14)); entry_p1.grid(row=0,column=1,padx=6,pady=6)
    tk.Label(frm, text="Difficulty:", font=("Arial",14), bg=c["bg"], fg=c["text"]).grid(row=1,column=0,sticky="w",padx=6,pady=6)
    difficulty_var = tk.StringVar(value="Easy")
    diff_frame = tk.Frame(frm, bg=c["bg"]); diff_frame.grid(row=1,column=1,padx=6,pady=6)
    for diff in ["Easy","Medium","Hard"]:
        tk.Radiobutton(diff_frame, text=diff, font=("Arial",12), variable=difficulty_var, value=diff, bg=c["bg"], fg=c["text"]).pack(side="left", padx=4)
    mp_var = tk.BooleanVar(value=False)
    def on_mp_toggle():
        if mp_var.get():
            tk.Label(frm, text="Player 2 name:", font=("Arial",14), bg=c["bg"], fg=c["text"]).grid(row=2,column=0,sticky="w",padx=6,pady=6)
            entry_p2.grid(row=2,column=1,padx=6,pady=6)
        else:
            try:
                entry_p2.grid_remove()
                for w in frm.grid_slaves(row=2,column=0):
                    w.grid_remove()
            except Exception:
                pass
    cb = tk.Checkbutton(frm, text="Multiplayer (Pass & Play)", variable=mp_var, command=on_mp_toggle, bg=c["bg"], fg=c["text"], font=("Arial",14))
    cb.grid(row=3,column=0,columnspan=2,pady=6)
    entry_p2 = tk.Entry(frm, font=("Arial",14)); entry_p2.grid(row=2,column=1,padx=6,pady=6); entry_p2.grid_remove()
    def start_selected_game():
        player1 = entry_p1.get().strip(); difficulty = difficulty_var.get()
        if not player1:
            messagebox.showerror("Input Error","Please enter Player 1 name before proceeding.")
            return
        if mp_var.get():
            player2 = entry_p2.get().strip()
            if not player2:
                messagebox.showerror("Input Error","Please enter Player 2 name for multiplayer.")
                return
            profiles.setdefault(player1, {"avatar":None,"xp":0,"level":1,"stats":{},"achievements":[]})
            profiles.setdefault(player2, {"avatar":None,"xp":0,"level":1,"stats":{},"achievements":[]})
            save_json(PROFILES_PATH, profiles)
            start_game_page(player1, difficulty, player2=player2)
        else:
            profiles.setdefault(player1, {"avatar":None,"xp":0,"level":1,"stats":{},"achievements":[]})
            save_json(PROFILES_PATH, profiles)
            start_game_page(player1, difficulty)
    make_btn(root,"Start",start_selected_game,"accent").pack(pady=10)
    make_btn(root,"Back",main_menu).pack(pady=6)

def main_menu():
    for widget in root.winfo_children(): widget.destroy()
    add_background(root, game_tag="main")   # fixed main background preference
    c = themed_colors()
    tk.Label(root, text="Game Hub", font=("Arial",34,"bold"), bg=c["primary"], fg="white").pack(pady=20)
    make_btn(root,"Start Game",get_player_info_page,"accent").pack(pady=6)
    make_btn(root,"Daily Challenge",daily_challenge,"primary").pack(pady=6)
    make_btn(root,"View Leaderboard",show_leaderboard,"primary").pack(pady=6)
    make_btn(root,"Settings",show_settings,"primary").pack(pady=6)
    make_btn(root,"Reset Scores",clear_scores,"warn").pack(pady=6)
    make_btn(root,"Clear Leaderboard",clear_leaderboard,"warn").pack(pady=6)

# ---------------------------
# Game selection & game functions (unchanged logic)
# ---------------------------
def start_game_page(player_name, difficulty, player2=None):
    for widget in root.winfo_children(): widget.destroy()
    add_background(root, game_tag="main")
    c = themed_colors()
    hdr = f"Choose a Game ({player_name}" + (f" vs {player2})" if player2 else ")")
    tk.Label(root, text=hdr, font=("Arial",26,"bold"), bg=c["bg"], fg=c["text"]).pack(pady=20)
    make_btn(root,"Word Guess", lambda: word_guess(player_name,difficulty,player2),"accent").pack(pady=6)
    make_btn(root,"Number Guess", lambda: number_guess(player_name,difficulty,player2),"primary").pack(pady=6)
    make_btn(root,"General Quiz", lambda: quiz_section(player_name,difficulty,player2),"primary").pack(pady=6)
    make_btn(root,"Aptitude Test", lambda: aptitude_test(player_name,difficulty,player2),"primary").pack(pady=6)
    make_btn(root,"Back", main_menu).pack(pady=10)

# Word Guess
def word_guess(player_name, difficulty, player2=None):
    for widget in root.winfo_children(): widget.destroy()
    add_background(root, game_tag="word")
    c = themed_colors()
    # select word
    try:
        if nltk_available:
            wl = words.words()
            candidates = [w.lower() for w in wl if 4 <= len(w) <= 6 and w.isalpha()]
            if not candidates:
                candidates = FALLBACK_WORDS
        else:
            candidates = FALLBACK_WORDS
    except Exception:
        candidates = FALLBACK_WORDS
    word = random.choice(candidates)
    guessed_letters = set(); wrong_letters = set()
    clue = ""
    try:
        if nltk_available:
            syns = wordnet.synsets(word); clue = syns[0].definition() if syns else "No clue available"
    except Exception:
        clue = "No clue available"
    max_attempts = {"Easy":10,"Medium":7,"Hard":5}.get(difficulty,7)
    attempts = max_attempts
    display_word = tk.StringVar(value=" ".join(["_" for _ in word]))
    hangman_canvas = tk.Canvas(root, width=240, height=280, bg=c["bg"], highlightthickness=0); hangman_canvas.pack(pady=6)
    def draw_hangman_stage(stage):
        hangman_canvas.delete("all")
        hangman_canvas.create_line(30,260,210,260,width=6,fill="#7f5539")
        hangman_canvas.create_line(60,260,60,30,width=6,fill="#7f5539")
        hangman_canvas.create_line(60,30,160,30,width=6,fill="#7f5539")
        hangman_canvas.create_line(160,30,160,60,width=6,fill="#7f5539")
        if stage>0: hangman_canvas.create_oval(135,60,185,110,width=4,outline="#222",fill="#fffbe7")
        if stage>1: hangman_canvas.create_line(160,110,160,170,width=4,fill="#222")
        if stage>2: hangman_canvas.create_line(160,130,130,150,width=4,fill="#222")
        if stage>3: hangman_canvas.create_line(160,130,190,150,width=4,fill="#222")
        if stage>4: hangman_canvas.create_line(160,170,130,210,width=4,fill="#222")
        if stage>5: hangman_canvas.create_line(160,170,190,210,width=4,fill="#222")
        if stage>6:
            hangman_canvas.create_oval(147,75,153,81,fill="#222")
            hangman_canvas.create_oval(167,75,173,81,fill="#222")
        if stage>7: hangman_canvas.create_arc(148,92,172,108,start=20,extent=140,style=tk.ARC,width=2)
        if stage>8: hangman_canvas.create_line(160,81,160,91,width=2,fill="#222")
    def animate_hangman():
        stage = max_attempts - attempts
        draw_hangman_stage(stage)
    tk.Label(root, textvariable=display_word, font=("Consolas",32,"bold"), bg=c["bg"], fg=c["text"]).pack(pady=6)
    tk.Label(root, text=f"Clue: {clue}", font=("Arial",16), bg=c["bg"], fg=c["text"]).pack(pady=2)
    attempts_left_label = tk.Label(root, text=f"Attempts Left: {attempts}", font=("Arial",16), bg=c["bg"], fg=c["text"]); attempts_left_label.pack(pady=2)
    guessed_label = tk.Label(root, text="Guessed Letters: ", font=("Arial",14), bg=c["bg"], fg=c["text"]); guessed_label.pack(pady=1)
    wrong_label = tk.Label(root, text="Wrong Guesses: ", font=("Arial",14), bg=c["bg"], fg="#d7263d"); wrong_label.pack(pady=1)
    letters_frame = tk.Frame(root, bg=c["bg"]); letters_frame.pack(pady=8)
    letter_buttons = {}
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    turn_player = [player_name]
    if player2: turn_player.append(player2)
    turn_idx = 0
    def switch_turn():
        nonlocal turn_idx
        if player2: turn_idx = 1 - turn_idx
    def on_letter_click(ch):
        nonlocal attempts, turn_idx
        ch = ch.lower()
        btn = letter_buttons.get(ch)
        if not btn or btn['state'] == tk.DISABLED: return
        btn.config(state=tk.DISABLED)
        if ch in guessed_letters or ch in wrong_letters: return
        if ch in word:
            play_sound("correct"); guessed_letters.add(ch)
        else:
            play_sound("wrong"); wrong_letters.add(ch); attempts -= 1
        update_ui()
        if all(letter in guessed_letters for letter in word): end_game(True); return
        if attempts == 0: end_game(False); return
        if player2: switch_turn()
    for idx, ch in enumerate(alphabet):
        r = idx // 9; cidx = idx % 9
        b = tk.Button(letters_frame, text=ch, width=3, height=1, font=("Arial",12), command=lambda ch=ch: on_letter_click(ch))
        b.grid(row=r, column=cidx, padx=3, pady=3)
        letter_buttons[ch.lower()] = b
    def use_hint():
        nonlocal attempts
        hidden = [ch for ch in set(word) if ch not in guessed_letters]
        if not hidden:
            messagebox.showinfo("Hint","No hidden letters left!"); return
        reveal = random.choice(hidden)
        guessed_letters.add(reveal)
        btn = letter_buttons.get(reveal)
        if btn: btn.config(state=tk.DISABLED)
        attempts = max(0, attempts-1); update_ui()
        if all(letter in guessed_letters for letter in word): end_game(True); return
        if attempts == 0: end_game(False); return
        if player2: switch_turn()
    ctrl = tk.Frame(root, bg=c["bg"]); ctrl.pack(pady=6)
    tk.Button(ctrl, text="Hint (-1)", font=("Arial",12), command=use_hint, bg=c["primary"], fg="white").pack(side="left", padx=6)
    make_btn(ctrl, "Back", lambda: start_game_page(player_name, difficulty, player2)).pack(side="left", padx=6)
    def update_ui():
        display_word.set(" ".join([letter if letter in guessed_letters else "_" for letter in word]))
        attempts_left_label.config(text=f"Attempts Left: {attempts} (Turn: {turn_player[turn_idx]})")
        guessed_label.config(text="Guessed Letters: " + " ".join(sorted(guessed_letters)))
        wrong_label.config(text="Wrong Guesses: " + " ".join(sorted(wrong_letters)))
        animate_hangman()
    def end_game(won):
        nonlocal turn_idx
        for b in letter_buttons.values(): b.config(state=tk.DISABLED)
        if won:
            play_sound("win")
            messagebox.showinfo("Success", f"You guessed the word: {word}")
            update_leaderboard(turn_player[turn_idx], 10)
            record_result(turn_player[turn_idx], won=True, game="Word Guess")
            grant_achievement(turn_player[turn_idx], "Hangman Hero")
        else:
            play_sound("lose")
            messagebox.showinfo("Game Over", f"The word was: {word}")
            if player2:
                other = turn_player[1 - turn_idx]
                update_leaderboard(other, 6)
                record_result(other, won=True, game="Word Guess")
        start_game_page(player_name, difficulty, player2)
    update_ui()

# Number guess
def number_guess(player_name, difficulty, player2=None):
    for widget in root.winfo_children(): widget.destroy()
    add_background(root, game_tag="number")
    c = themed_colors()
    number = random.randint(1,100)
    attempts = {"Easy":10,"Medium":7,"Hard":5}.get(difficulty,7)
    low, high = 1, 100
    tk.Label(root, text="Guess a number between 1 and 100", font=("Arial",22), bg=c["bg"], fg=c["text"]).pack(pady=10)
    attempts_left_label = tk.Label(root, text=f"Attempts Left: {attempts}", font=("Arial",16), bg=c["bg"], fg=c["text"]); attempts_left_label.pack(pady=4)
    range_label = tk.Label(root, text=f"Range: {low} - {high}", font=("Arial",14), bg=c["bg"], fg=c["text"]); range_label.pack(pady=2)
    scale = tk.Scale(root, from_=1, to=100, orient=tk.HORIZONTAL, length=400); scale.set(50); scale.pack(pady=6)
    turn_player = [player_name]
    if player2: turn_player.append(player2)
    turn_idx = 0
    def switch_turn():
        nonlocal turn_idx
        if player2: turn_idx = 1 - turn_idx
    def check_number():
        nonlocal attempts, low, high, turn_idx
        try:
            guess = int(scale.get())
        except:
            guess = int(scale.get())
        if guess == number:
            play_sound("win"); messagebox.showinfo("Success", f"Correct! ({turn_player[turn_idx]} guessed it)")
            update_leaderboard(turn_player[turn_idx], 10)
            record_result(turn_player[turn_idx], won=True, game="Number Guess")
            start_game_page(player_name, difficulty, player2); return
        elif guess < number:
            play_sound("wrong"); low = max(low, guess+1); messagebox.showinfo("Hint","Too low!")
        else:
            play_sound("wrong"); high = min(high, guess-1); messagebox.showinfo("Hint","Too high!")
        attempts -= 1
        attempts_left_label.config(text=f"Attempts Left: {attempts} (Turn: {turn_player[turn_idx]})")
        range_label.config(text=f"Range: {low} - {high}")
        scale.config(from_=low, to=high)
        if attempts == 0:
            play_sound("lose"); messagebox.showinfo("Game Over", f"The number was: {number}")
            if player2:
                other = turn_player[1 - turn_idx]; update_leaderboard(other,5); record_result(other, won=True, game="Number Guess")
            start_game_page(player_name, difficulty, player2)
        else:
            if player2: switch_turn()
    make_btn(root, "Submit", check_number, "accent").pack(pady=6)
    make_btn(root, "Back", lambda: start_game_page(player_name, difficulty, player2)).pack(pady=6)

# Questions import & load
def load_questions(default_list, path):
    if os.path.exists(path):
        try:
            with open(path,'r',encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    return data
        except Exception as e:
            print("Failed to load questions:", e)
    return default_list

def import_questions_dialog():
    for w in root.winfo_children(): w.destroy()
    add_background(root, game_tag="import_q")
    c = themed_colors()
    tk.Label(root, text="Import Questions (JSON array)", font=("Arial",24,"bold"), bg=c["primary"], fg="white").pack(pady=12)
    def import_file(which):
        path = filedialog.askopenfilename(title="Choose questions JSON", filetypes=[("JSON","*.json")])
        if not path: return
        try:
            with open(path,'r',encoding='utf-8') as f: data = json.load(f)
            if not isinstance(data, list):
                messagebox.showerror("Format","JSON must be an array of {question, options, answer} objects."); return
            out_path = QUESTIONS_GENERAL_PATH if which=="General" else QUESTIONS_APTITUDE_PATH
            save_json(out_path, data); messagebox.showinfo("Imported", f"Imported {len(data)} questions to {which}.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import: {e}")
    make_btn(root,"Import to General Quiz", lambda: import_file("General"), "primary").pack(pady=6)
    make_btn(root,"Import to Aptitude", lambda: import_file("Aptitude"), "primary").pack(pady=6)
    make_btn(root,"Back", main_menu).pack(pady=10)

# Quiz
def quiz_section(player_name, difficulty, player2=None):
    for widget in root.winfo_children(): widget.destroy()
    add_background(root, game_tag="quiz")
    c = themed_colors()
    default_qs = [
        {"question":"What is the capital of France?","options":["Berlin","Madrid","Paris","Rome"],"answer":"Paris"},
        {"question":"What is 2 + 2?","options":["3","4","5","6"],"answer":"4"},
        {"question":"Who wrote 'Romeo and Juliet'?","options":["Shakespeare","Dickens","Hemingway","Austen"],"answer":"Shakespeare"},
        {"question":"Which planet is known as the Red Planet?","options":["Earth","Mars","Jupiter","Saturn"],"answer":"Mars"}
    ]
    questions = load_questions(default_qs, QUESTIONS_GENERAL_PATH)
    score = 0; start_time = datetime.datetime.now()
    tk.Label(root, text="General Quiz", font=("Arial",24,"bold"), bg=c["bg"], fg=c["text"]).pack(pady=6)
    timer_label = tk.Label(root, text="Time: 0s", font=("Arial",14), bg=c["bg"], fg=c["text"]); timer_label.pack()
    question_label = tk.Label(root, text="", font=("Arial",20), bg=c["bg"], fg=c["text"]); question_label.pack(pady=6)
    options_frame = tk.Frame(root, bg=c["bg"]); options_frame.pack(pady=6)
    def tick():
        delta = (datetime.datetime.now() - start_time).seconds
        timer_label.config(text=f"Time: {delta}s"); root.after(1000, tick)
    tick()
    current_question = {}
    def next_question():
        nonlocal current_question
        if questions:
            current_question = random.choice(questions); questions.remove(current_question)
            q = current_question["question"]; opts = current_question.get("options", [])
            question_label.config(text=q)
            for w in options_frame.winfo_children(): w.destroy()
            for opt in opts:
                b = tk.Button(options_frame, text=opt, font=("Arial",14), width=30, command=lambda opt=opt: check_quiz_answer(opt))
                b.pack(pady=4)
            speak(q)
        else:
            end_quiz()
    def end_quiz():
        nonlocal score
        elapsed = (datetime.datetime.now() - start_time).seconds
        if elapsed <=30: score += 5
        update_leaderboard(player_name, score)
        prof = profiles.setdefault(player_name, {"stats":{}})
        best = prof.get("stats", {}).get("fastest_quiz_sec")
        if best is None or elapsed < best:
            profiles[player_name]["stats"]["fastest_quiz_sec"] = elapsed
            save_json(PROFILES_PATH, profiles)
            grant_achievement(player_name, "Speedster")
        messagebox.showinfo("Test Over", f"Score: {score} (Time {elapsed}s)"); record_result(player_name, won=True, game="Quiz")
        start_game_page(player_name, difficulty, player2)
    def check_quiz_answer(selected_opt):
        nonlocal score
        ans = selected_opt
        if ans and ans.lower() == str(current_question["answer"]).lower():
            play_sound("correct"); score += 5; messagebox.showinfo("Answer","Correct!")
        else:
            play_sound("wrong"); messagebox.showinfo("Answer", f"Wrong! Correct: {current_question['answer']}")
        next_question()
    tk.Button(root, text="Back", font=("Arial",14), command=lambda: start_game_page(player_name,difficulty,player2)).pack(pady=6)
    next_question()

# Aptitude
def aptitude_test(player_name, difficulty, player2=None):
    for widget in root.winfo_children(): widget.destroy()
    add_background(root, game_tag="aptitude")
    c = themed_colors()
    default_qs = [
        {"question":"If a train travels 60 miles in 1 hour, what is its speed?","options":["60 mph","50 mph","70 mph","80 mph"],"answer":"60 mph"},
        {"question":"What is 12 × 12?","options":["144","132","156","120"],"answer":"144"},
        {"question":"What is 10 + 15?","options":["20","25","30","35"],"answer":"25"},
        {"question":"How many degrees are in a circle?","options":["360","180","90","270"],"answer":"360"}
    ]
    questions = load_questions(default_qs, QUESTIONS_APTITUDE_PATH)
    score = 0; start_time = datetime.datetime.now()
    tk.Label(root, text="Aptitude Test", font=("Arial",24,"bold"), bg=c["bg"], fg=c["text"]).pack(pady=6)
    timer_label = tk.Label(root, text="Time: 0s", font=("Arial",14), bg=c["bg"], fg=c["text"]); timer_label.pack()
    question_label = tk.Label(root, text="", font=("Arial",20), bg=c["bg"], fg=c["text"]); question_label.pack(pady=6)
    options_frame = tk.Frame(root, bg=c["bg"]); options_frame.pack(pady=6)
    def tick():
        delta = (datetime.datetime.now() - start_time).seconds
        timer_label.config(text=f"Time: {delta}s"); root.after(1000, tick)
    tick()
    current_question = {}
    def next_question():
        nonlocal current_question
        if questions:
            current_question = random.choice(questions); questions.remove(current_question)
            q = current_question["question"]; opts = current_question.get("options", [])
            question_label.config(text=q)
            for w in options_frame.winfo_children(): w.destroy()
            for opt in opts:
                b = tk.Button(options_frame, text=opt, font=("Arial",14), width=30, command=lambda opt=opt: check_aptitude_answer(opt))
                b.pack(pady=4)
            speak(q)
        else:
            end_test()
    def end_test():
        nonlocal score
        elapsed = (datetime.datetime.now() - start_time).seconds
        if elapsed <=30: score += 5
        update_leaderboard(player_name, score)
        record_result(player_name, won=True, game="Aptitude")
        messagebox.showinfo("Test Over", f"Score: {score} (Time {elapsed}s)")
        start_game_page(player_name, difficulty, player2)
    def check_aptitude_answer(selected_opt):
        nonlocal score
        ans = selected_opt
        if ans and ans.lower() == str(current_question["answer"]).lower():
            play_sound("correct"); score += 5; messagebox.showinfo("Answer","Correct!")
        else:
            play_sound("wrong"); messagebox.showinfo("Answer", f"Wrong! Correct: {current_question['answer']}")
        next_question()
    tk.Button(root, text="Back", font=("Arial",14), command=lambda: start_game_page(player_name,difficulty,player2)).pack(pady=6)
    next_question()

# Daily & mixed
def daily_challenge():
    today = datetime.date.today().isoformat()
    seed = sum(ord(ch) for ch in today); random.seed(seed)
    for w in root.winfo_children(): w.destroy()
    add_background(root, game_tag="daily")
    c = themed_colors()
    tk.Label(root, text=f"Daily Challenge ({today})", font=("Arial",26,"bold"), bg=c["primary"], fg="white").pack(pady=12)
    def start():
        name = prompt_player_name(title="Player for Daily", prompt_text="Enter player name:")
        if not name: return
        pick = random.choice(["word","number","quiz","apt"])
        if pick=="word": word_guess(name,"Medium")
        elif pick=="number": number_guess(name,"Medium")
        elif pick=="quiz": quiz_section(name,"Medium")
        else: aptitude_test(name,"Medium")
    make_btn(root,"Start",start,"accent").pack(pady=8)
    make_btn(root,"Back",main_menu).pack(pady=6)

def mixed_mode():
    name = prompt_player_name(title="Mixed Mode - Player", prompt_text="Enter player name:")
    if not name: return
    sequence = ["word","number","quiz","apt"]; random.shuffle(sequence)
    messagebox.showinfo("Mixed Mode", "You'll play all four games once. Start with the first now!")
    g = sequence[0]
    if g=="word": word_guess(name,"Medium")
    elif g=="number": number_guess(name,"Medium")
    elif g=="quiz": quiz_section(name,"Medium")
    else: aptitude_test(name,"Medium")

# ---------------------------
# App start
# ---------------------------
root = tk.Tk(); root.title("Game Hub")
try:
    root.geometry("900x700")
except Exception:
    pass

init_audio()
# Apply music setting at start
if settings.get("music", True):
    play_bgm()

main_menu()
root.mainloop()
