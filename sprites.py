"""sprites.py — টেক্সট-গ্রিড স্প্রাইট ও তাদের কালার ম্যাপ (design.md §7)।"""

import config

# design.md §7 legend: '#' = OUTLINE, 'W' = SKIN, 'S' = SKIN_S, '.' = transparent

# HEAD_SLEEP (9×7) — ঘুমন্ত মাথা; ৪ নম্বর সারিতে বন্ধ চোখ, উপরে গোল মাথা (design.md §7)
HEAD_SLEEP = [
    "..#####..",
    ".#WWWWW#.",
    "#WWWWWWS#",
    "#W##W##S#",   # বন্ধ চোখ (## ## দুই চোখ)
    "#WWWWWWS#",
    ".#WWWWS#.",
    "..#####..",
]

# HEAD_SLEEP-এর অক্ষর → রঙ ম্যাপ (মান config থেকে, কোনো হেক্স হার্ডকোড নেই)
HEAD_SLEEP_COLORS = {
    "#": config.OUTLINE,   # আউটলাইন
    "W": config.SKIN,      # শরীরের সাদা
    "S": config.SKIN_S,    # লাভেন্ডার ছায়া
}
