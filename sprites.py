"""sprites.py — টেক্সট-গ্রিড স্প্রাইট ও তাদের কালার ম্যাপ (design.md §7)।"""

import config

# ক্যারেক্টার স্প্রাইটের সাধারণ legend: '#' = OUTLINE, 'W' = SKIN, 'S' = SKIN_S, '.' = transparent
CHAR_COLORS = {
    "#": config.OUTLINE,   # আউটলাইন
    "W": config.SKIN,      # শরীরের সাদা
    "S": config.SKIN_S,    # লাভেন্ডার ছায়া
}

# HEAD_SLEEP (9×7) — ঘুমন্ত মাথা; ৪ নম্বর সারিতে বন্ধ চোখ, উপরে গোল মাথা
HEAD_SLEEP = [
    "..#####..",
    ".#WWWWW#.",
    "#WWWWWWS#",
    "#W##W##S#",   # বন্ধ চোখ
    "#WWWWWWS#",
    ".#WWWWS#.",
    "..#####..",
]
HEAD_SLEEP_COLORS = CHAR_COLORS

# HEAD_BACK (9×7) — পেছন থেকে মাথা (বসে কাজ করার সময়); চোখ নেই
HEAD_BACK = [
    "..#####..",
    ".#WWWWW#.",
    "#WWWWWWS#",
    "#WWWWWWS#",
    "#WWWWWSS#",
    ".#WSSSS#.",
    "..#####..",
]
HEAD_BACK_COLORS = CHAR_COLORS

# BODY_BACK (10×5) — পেছন থেকে কাঁধ/পিঠ
BODY_BACK = [
    "#WWWWWWWS#",
    "#WWWWWWWS#",
    "#WWWWWWSS#",
    ".#WWWSSS#.",
    ".########.",
]
BODY_BACK_COLORS = CHAR_COLORS

# STAND (9×13) — দাঁড়ানো পূর্ণ শরীর
STAND = [
    "..#####..",
    ".#WWWWW#.",
    "#WWWWWWS#",
    "#W#WW#WS#",
    "#WWWWWWS#",
    ".#WWWWS#.",
    "..#####..",
    ".#WWWWS#.",
    ".#WWWWS#.",
    ".#WWWSS#.",
    ".#WW#SS#.",
    ".#W#.#S#.",
    ".##..##..",
]

# WALK_A / WALK_B — STAND-এর সাথে শুধু শেষ ২ সারি (পা) বদলায়; হাঁটার সময় ০.১৫s অন্তর অদলবদল
# নোট: design §7-এ WALK_A-এর পা সারি ভুলে ১০ চওড়া (STAND ৯ চওড়া); trailing '.' বাদ দিয়ে ৯-এ মিলিয়েছি।
_WALK_A_LEGS = [
    ".#W#..#S#",
    ".##...##.",
]
_WALK_B_LEGS = [
    ".##..#S#.",
    ".....##..",
]
WALK_A = STAND[:11] + _WALK_A_LEGS
WALK_B = STAND[:11] + _WALK_B_LEGS

STAND_COLORS = CHAR_COLORS
WALK_A_COLORS = CHAR_COLORS
WALK_B_COLORS = CHAR_COLORS

# পিছন-দিক (back view) স্প্রাইট — একই শরীর/পা, কিন্তু মাথায় HEAD_BACK (মুখ নেই)।
# design fix: উপরে (dy < 0) হাঁটলে পিঠ দেখা যায়, তাই এই ভার্সন ব্যবহার হয়।
# STAND-এর প্রথম ৭ সারি = মাথা; সেগুলো HEAD_BACK দিয়ে বদলে বাকি (পা) অংশ রেখে দিই।
STAND_BACK = HEAD_BACK + STAND[7:]
WALK_A_BACK = HEAD_BACK + WALK_A[7:]
WALK_B_BACK = HEAD_BACK + WALK_B[7:]
STAND_BACK_COLORS = CHAR_COLORS
WALK_A_BACK_COLORS = CHAR_COLORS
WALK_B_BACK_COLORS = CHAR_COLORS

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
