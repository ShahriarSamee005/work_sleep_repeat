import config

# ---- Per-character sprite grids (Phase 18) ----
# Legend: '#'=OUTLINE 'W'=SKIN 'S'=SKIN_S 'H'=hair 'C'=clothes 'c'=clothes shadow '.'=transparent
# Zoro extras: 'G'=haramaki 'r'=red eye   Sanji extras: 'b'=blue collar 'y'=yellow buttons

# ---------- SAMEE = ZORO ----------

ZORO_STAND = [
    "..#####..",
    ".#HHHHH#.",
    "#HHHHHHH#",
    "#HW#WrWH#",
    "#WWWWWWW#",
    ".#WWWWW#.",
    "..#WWW#..",
    "#WWWWWWW#",
    "#WWWWWWW#",
    "#GGGGGGG#",
    "#CCCCCCC#",
    "#CC#.#CC#",
    "#CC#.#CC#",
]
ZORO_HEAD_SLEEP = [
    "..#####..",
    ".#HHHHH#.",
    "#HHHHHHH#",
    "#W##W##S#",
    "#WWWWWWS#",
    ".#WWWWS#.",
    "..#####..",
]
ZORO_HEAD_BACK = [
    "..#####..",
    ".#HHHHH#.",
    "#HHHHHHH#",
    "#HHHHHHH#",
    "#HHHHHHH#",
    ".#HHHHH#.",
    "..#####..",
]
ZORO_BODY_BACK = [
    "#WWWWWWWW#",
    "#WWWWWWWW#",
    "#GGGGGGGG#",
    "#CCCCCCCC#",
    "#CCCCCCCC#",
]
_ZORO_WALK_A_LEGS = ["#CCC.#CC#", "#CC#.#CC#"]
_ZORO_WALK_B_LEGS = ["#CC#.CCC#", "#CC#.#CC#"]

ZORO_WALK_A = ZORO_STAND[:11] + _ZORO_WALK_A_LEGS
ZORO_WALK_B = ZORO_STAND[:11] + _ZORO_WALK_B_LEGS
ZORO_STAND_BACK = ZORO_HEAD_BACK + ZORO_STAND[7:]
ZORO_WALK_A_BACK = ZORO_HEAD_BACK + ZORO_WALK_A[7:]
ZORO_WALK_B_BACK = ZORO_HEAD_BACK + ZORO_WALK_B[7:]

CHAR_COLORS_SAMEE = {
    "#": "#231c2b", "W": "#f4f2ee", "S": "#cdbfa0",
    "H": "#4a7a5a",
    "G": "#2e7d52",
    "C": "#20202a", "c": "#15151c",
    "r": "#c0392b",
}

CHAR_SPRITES_SAMEE = {
    "STAND": ZORO_STAND,
    "STAND_BACK": ZORO_STAND_BACK,
    "WALK_A": ZORO_WALK_A,
    "WALK_B": ZORO_WALK_B,
    "WALK_A_BACK": ZORO_WALK_A_BACK,
    "WALK_B_BACK": ZORO_WALK_B_BACK,
    "HEAD_SLEEP": ZORO_HEAD_SLEEP,
    "HEAD_BACK": ZORO_HEAD_BACK,
    "BODY_BACK": ZORO_BODY_BACK,
}

# ---------- RIFAT = SANJI ----------

SANJI_STAND = [
    "..#####..",
    ".#HHHHH#.",
    "#HHHHHHH#",
    "#HHHHW#W#",
    "#HWWWWWW#",
    ".#WWWWW#.",
    "..#WWW#..",
    "#CCbCbCC#",
    "#CCyCyCC#",
    "#CCCCCCC#",
    "#CCCCCCC#",
    "#CC#.#CC#",
    "#CC#.#CC#",
]
SANJI_HEAD_SLEEP = [
    "..#####..",
    ".#HHHHH#.",
    "#HHHHHHH#",
    "#W##W##S#",
    "#WWWWWWS#",
    ".#WWWWS#.",
    "..#####..",
]
SANJI_HEAD_BACK = [
    "..#####..",
    ".#HHHHH#.",
    "#HHHHHHH#",
    "#HHHHHHH#",
    "#HHHHHHH#",
    ".#HHHHH#.",
    "..#####..",
]
SANJI_BODY_BACK = [
    "#CCCCCCCC#",
    "#CCCCCCCC#",
    "#CCCCCCCC#",
    "#CCCCCCCC#",
    "#CCCCCCCC#",
]
_SANJI_WALK_A_LEGS = ["#CCC.#CC#", "#CC#.#CC#"]
_SANJI_WALK_B_LEGS = ["#CC#.CCC#", "#CC#.#CC#"]

SANJI_WALK_A = SANJI_STAND[:11] + _SANJI_WALK_A_LEGS
SANJI_WALK_B = SANJI_STAND[:11] + _SANJI_WALK_B_LEGS
SANJI_STAND_BACK = SANJI_HEAD_BACK + SANJI_STAND[7:]
SANJI_WALK_A_BACK = SANJI_HEAD_BACK + SANJI_WALK_A[7:]
SANJI_WALK_B_BACK = SANJI_HEAD_BACK + SANJI_WALK_B[7:]

CHAR_COLORS_RIFAT = {
    "#": "#231c2b", "W": "#f4f2ee", "S": "#cdbfa0",
    "H": "#ffcf33",
    "C": "#1a1a22", "c": "#101016",
    "b": "#3f82c8",
    "y": "#ffcf33",
}

CHAR_SPRITES_RIFAT = {
    "STAND": SANJI_STAND,
    "STAND_BACK": SANJI_STAND_BACK,
    "WALK_A": SANJI_WALK_A,
    "WALK_B": SANJI_WALK_B,
    "WALK_A_BACK": SANJI_WALK_A_BACK,
    "WALK_B_BACK": SANJI_WALK_B_BACK,
    "HEAD_SLEEP": SANJI_HEAD_SLEEP,
    "HEAD_BACK": SANJI_HEAD_BACK,
    "BODY_BACK": SANJI_BODY_BACK,
}

# PLANT (9×6) — গাছের পাতা; 'G' = PLANT, 'g' = PLANT_D
PLANT = [
    "..G.G....",
    ".GGgGG...",
    "GGgGGgG..",
    "gGGgGGG..",
    ".GgGGg...",
    "..GGG....",
]
PLANT_COLORS = {
    "G": config.PLANT,
    "g": config.PLANT_D,
}

# MOON (12×12) — প্যানেল আইকন; 'Y' = MOON_LIGHT, '#' = MOON_EDGE
MOON = [
    "....####....",
    "..##YYY#....",
    ".#YYYY#.....",
    ".#YYY#......",
    "#YYYY#......",
    "#YYYY#......",
    "#YYYYY#.....",
    "#YYYYYY#..##",
    ".#YYYYYY##Y#",
    ".#YYYYYYYYY#",
    "..##YYYYY##.",
    "....#####...",
]
MOON_COLORS = {
    "Y": config.MOON_LIGHT,
    "#": config.MOON_EDGE,
}

# SUN (12×12) — প্যানেল আইকন; 'Y' = GOLD, 'O' = SUN_CORE, '#' = SUN_EDGE
SUN = [
    ".....YY.....",
    ".Y...YY...Y.",
    "..Y......Y..",
    "....####....",
    "...#OOOO#...",
    "YY.#OOOO#.YY",
    "YY.#OOOO#.YY",
    "...#OOOO#...",
    "....####....",
    "..Y......Y..",
    ".Y...YY...Y.",
    ".....YY.....",
]
SUN_COLORS = {
    "Y": config.GOLD,
    "O": config.SUN_CORE,
    "#": config.SUN_EDGE,
}

# BUBBLE_DIBS (11×9) — যে dibs ডেকেছে তার মাথার উপরে ছোট speech bubble + তোলা হাত (design §3)
# 'B' = বাবলের ভেতর, '#' = OUTLINE, 'H' = হাতের রঙ
BUBBLE_DIBS = [
    ".#########.",
    "#BBBBBBBBB#",
    "#BHBHBHBBB#",    # তিনটি আঙুল
    "#BHHHHHHBB#",
    "#HHHHHHHHB#",    # বাঁয়ে বুড়ো আঙুল
    "#HHHHHHHBB#",
    "#BHHHHHBBB#",
    "#BBBBBBBB#.",
    ".##.##.....",    # বাবলের লেজ (চরিত্রের দিকে)
]
BUBBLE_DIBS_COLORS = {
    "B": config.BUBBLE_BG,
    "H": config.OUTLINE,   # হাত গাঢ় silhouette — এই মাপে সেটিই সবচেয়ে স্পষ্ট পড়া যায়
    "#": config.OUTLINE,
}

# ---- ট্রে আইকন (design §4) — ১৬×১৬ গ্রিড; tray.py রান-টাইমে ছবি বানায় (কোনো ফাইল শিপ করি না) ----

# TRAY_MOON (16×16) — কেউ কাজ করছে না; 'Y' = MOON_LIGHT, '#' = MOON_EDGE
TRAY_MOON = [
    "................",
    "....######......",
    "..##YYYYY##.....",
    ".#YYYYYYYY##....",
    ".#YYYYY#####....",
    "#YYYYY#.........",
    "#YYYY#..........",
    "#YYYY#..........",
    "#YYYY#..........",
    "#YYYY#..........",
    "#YYYYY#.........",
    ".#YYYYY#####....",
    ".#YYYYYYYY##....",
    "..##YYYYY##.....",
    "....######......",
    "................",
]
TRAY_MOON_COLORS = {
    "Y": config.MOON_LIGHT,
    "#": config.MOON_EDGE,
}

# TRAY_MOON_OFF — একই চাঁদ, ধূসর (সার্ভারে পৌঁছানো যাচ্ছে না)
TRAY_MOON_OFF_COLORS = {
    "Y": config.OFFLINE_GREY,
    "#": config.PANEL_BORDER,
}

# TRAY_LAMP (16×16) — কেউ কাজ করছে; 'L' = LAMP_ON শেড, 'B' = বাল্বের রেখা,
# 'G' = নিচে ছড়ানো আলো, '#' = OUTLINE
TRAY_LAMP = [
    "................",
    "......####......",
    ".....#LLLL#.....",
    "....#LLLLLL#....",
    "...#LLLLLLLL#...",
    "...#BBBBBBBB#...",
    "....GG#..#GG....",
    "...GG..#..GG....",
    "......#.........",
    "......#.........",
    "......#.........",
    "......#.........",
    "....####........",
    "...#....#.......",
    "...######.......",
    "................",
]
TRAY_LAMP_COLORS = {
    "L": config.LAMP_ON,
    "B": config.LAMP_BULB,
    "G": config.GLOW_WARM,
    "#": config.OUTLINE,
}

# TRAY_HEAD (16×16) — ক্যারেক্টারের মাথা, অ্যাপ আইকন হিসেবে ব্যবহৃত
TRAY_HEAD = [
    "................",
    ".....######.....",
    "....#WWWWWW#....",
    "...#WWWWWWWW#...",
    "..#WWWWWWWWWS#..",
    "..#WWWWWWWWWS#..",
    ".#WW##WWWW##WS#.",
    ".#WWWWWWWWWWWS#.",
    "..#WWWWWWWWWSS#.",
    "...#WWWWWWSS#...",
    "....#WSSSS#.....",
    ".....######.....",
    "................",
    "................",
    "................",
    "................",
]
TRAY_HEAD_COLORS = {
    "#": config.OUTLINE,
    "W": config.SKIN,
    "S": config.SKIN_S,
}
TRAY_HEAD_OFF_COLORS = {
    "#": config.PANEL_BORDER,
    "W": config.OFFLINE_GREY,
    "S": config.PANEL_BORDER,
}
