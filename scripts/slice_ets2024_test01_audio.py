#!/usr/bin/env python3
"""
Slice authentic ETS 2024 Test 01 master audio into individual question MP3 clips.
Saves to apps/web/public/audio/ets2024_01/
Part 1: part1_q01.mp3 to part1_q06.mp3
Part 2: part2_q07.mp3 to part2_q31.mp3
"""

import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MASTER_AUDIO = BASE_DIR / "server" / "data" / "audio" / "ets2024_01_full.mp3"
OUTPUT_DIR = BASE_DIR / "apps" / "web" / "public" / "audio" / "ets2024_01"

CLIPS = [
    # Part 1 (Photographs)
    ("part1_q01.mp3", 96.0, 23.2),    # Q1: She's eating in a picnic area...
    ("part1_q02.mp3", 124.0, 21.5),   # Q2: The man is standing in the snow...
    ("part1_q03.mp3", 156.5, 23.3),   # Q3: Two of the people are having a conversation...
    ("part1_q04.mp3", 184.0, 24.2),   # Q4: Clothing is being displayed under a tent...
    ("part1_q05.mp3", 212.5, 23.5),   # Q5: A computer station has been set up...
    ("part1_q06.mp3", 240.0, 23.0),   # Q6: A door has been taken off its frame...

    # Part 2 (Question - Response)
    ("part2_q07.mp3", 300.5, 17.0),   # Q7: How old is this building?
    ("part2_q08.mp3", 321.5, 16.3),   # Q8: Can you come to my jazz performance tonight?
    ("part2_q09.mp3", 342.0, 17.0),   # Q9: Which apartment submitted a work order?
    ("part2_q10.mp3", 363.5, 15.7),   # Q10: Will you contact the vendor about changing our delivery date?
    ("part2_q11.mp3", 383.8, 15.7),   # Q11: Why was the maintenance worker here?
    ("part2_q12.mp3", 404.0, 16.3),   # Q12: Did management make a hiring decision yet?
    ("part2_q13.mp3", 425.0, 15.6),   # Q13: Do you want to eat here in our cafeteria or go out?
    ("part2_q14.mp3", 445.0, 17.4),   # Q14: Didn't you email the employment contract to Mr Patel yesterday?
    ("part2_q15.mp3", 466.8, 16.6),   # Q15: Our division's picnic is this Saturday, right?
    ("part2_q16.mp3", 488.0, 14.5),   # Q16: Would you like coffee or tea?
    ("part2_q17.mp3", 507.0, 14.8),   # Q17: We achieved our sales targets this month.
    ("part2_q18.mp3", 526.2, 15.2),   # Q18: How often do you travel for your job?
    ("part2_q19.mp3", 546.0, 14.9),   # Q19: We should hike the Wildflower Trail today.
    ("part2_q20.mp3", 565.5, 16.5),   # Q20: You have booked a hotel in London, haven't you?
    ("part2_q21.mp3", 586.5, 15.5),   # Q21: Are there any tickets left for tonight's concert?
    ("part2_q22.mp3", 606.5, 14.6),   # Q22: Haven't you used this software before?
    ("part2_q23.mp3", 625.5, 16.5),   # Q23: When is the new blender going to be released?
    ("part2_q24.mp3", 646.5, 15.7),   # Q24: Who's picking up our clients at the airport?
    ("part2_q25.mp3", 666.5, 17.3),   # Q25: Where are the red roses that came in this morning?
    ("part2_q26.mp3", 688.2, 16.6),   # Q26: This film has been nominated for several awards.
    ("part2_q27.mp3", 709.2, 17.1),   # Q27: Who's interested in starting a carpool program?
    ("part2_q28.mp3", 730.8, 16.4),   # Q28: Where will I teach my workshop this month?
    ("part2_q29.mp3", 751.8, 17.6),   # Q29: Why are we moving these sweaters to the back of the store?
    ("part2_q30.mp3", 773.8, 16.4),   # Q30: Would you be interested in working on some of these contracts?
    ("part2_q31.mp3", 794.8, 16.7),   # Q31: What type of job are you looking for?
]


def slice_all():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not MASTER_AUDIO.exists():
        raise FileNotFoundError(f"Master audio not found: {MASTER_AUDIO}")

    ffmpeg_bin = "/opt/homebrew/bin/ffmpeg"
    print(f"Slicing {len(CLIPS)} authentic audio clips from {MASTER_AUDIO.name}...")

    for filename, start, dur in CLIPS:
        out_path = OUTPUT_DIR / filename
        cmd = [
            ffmpeg_bin, "-y",
            "-ss", str(start),
            "-t", str(dur),
            "-i", str(MASTER_AUDIO),
            "-acodec", "libmp3lame",
            "-b:a", "128k",
            str(out_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error slicing {filename}: {res.stderr}")
        else:
            size_kb = out_path.stat().st_size / 1024
            print(f"✓ {filename} ({dur:.1f}s, {size_kb:.1f} KB)")

    print(f"\nAll {len(CLIPS)} clips successfully sliced into {OUTPUT_DIR}")


if __name__ == "__main__":
    slice_all()
