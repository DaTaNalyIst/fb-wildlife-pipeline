"""
Pipeline 1: Prompt Factory
==========================
Uses Gemini 2.5 Pro to generate a full day's batch of animal POV
video prompts + captions, saved as JSON for the video pipeline.

Cost: FREE — uses Gemini text generation (free tier: 250 req/day)
Runs: 8am EAT daily via GitHub Actions cron
"""
import os
import json
import google.generativeai as genai
from datetime import date
from pathlib import Path

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-pro-preview-06-05")

# 10 animal/setting combinations — rotate daily if needed
NICHES = [
    ("rabbit", "dense moss-covered forest", "golden hour"),
    ("bald eagle", "snow-capped mountain ridge", "sunrise alpenglow"),
    ("bottlenose dolphin", "clear tropical ocean", "midday light"),
    ("cheetah", "open African savanna", "orange sunset"),
    ("monarch butterfly", "wildflower meadow", "soft morning light"),
    ("anglerfish", "deep sea midnight zone", "bioluminescent darkness"),
    ("great horned owl", "old-growth forest", "full moon night"),
    ("hummingbird", "tropical garden", "bright noon"),
    ("arctic wolf", "snowy tundra", "blue dawn"),
    ("green sea turtle", "vibrant coral reef", "dappled afternoon"),
]

MASTER_PROMPT = """
You are a professional AI video prompt engineer creating viral wildlife POV content
for Facebook monetization. Target audience: US adults aged 25-55.

Generate a JSON array of exactly 10 animal POV video packages.

Each package must have these exact keys:
- "animal": the animal (e.g. "rabbit")
- "setting": the environment
- "lighting": time of day and light quality
- "veo3_prompt": a Veo3 video generation prompt. Must:
    * Start with: "POV shot from a tiny GoPro camera mounted on the back of a [animal],"
    * Describe exactly 8 seconds of continuous forward motion
    * Include specific visual detail (terrain, plants, light quality, textures)
    * Include audio cues (specific nature sounds, NO music)
    * Use words: photorealistic, 4K, cinematic, GoPro HERO aesthetic
    * Be under 120 words total
- "caption": Facebook post caption. Must:
    * Be under 80 characters
    * No hashtags
    * Use curiosity or wonder (NOT hype)
    * Feel like a nature documentary, posted casually
- "caption_alt": Alternative caption ending with a question to drive comments
- "hook_seconds": First 3 seconds description — what makes the viewer keep watching

Generate for these 10 animals/settings/lighting conditions:
{pairs}

CRITICAL: Return ONLY a valid JSON array. No markdown fences. No preamble. No explanation.
Just the raw JSON array starting with [ and ending with ].
""".strip()

pairs_text = "\n".join(
    f"{i+1}. {a} | {s} | {l}" for i, (a, s, l) in enumerate(NICHES)
)

print(f"Calling Gemini 2.5 Pro for {date.today().isoformat()} prompt batch...")

try:
    response = model.generate_content(
        MASTER_PROMPT.format(pairs=pairs_text),
        generation_config={
            "temperature": 0.85,
            "max_output_tokens": 8000,
            "response_mime_type": "application/json",
        },
    )
    raw = response.text.strip()
except Exception as e:
    print(f"Gemini API error: {e}")
    raise

# Clean up any accidental markdown fences
if raw.startswith("```"):
    raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw[:-3].strip()
    elif "```" in raw:
        raw = raw.split("```")[0].strip()

# Parse and validate
try:
    batch = json.loads(raw)
    if not isinstance(batch, list):
        raise ValueError("Expected JSON array, got something else")
    print(f"Parsed {len(batch)} prompt packages")
except json.JSONDecodeError as e:
    print(f"JSON parse error: {e}")
    print(f"Raw response (first 500 chars):\n{raw[:500]}")
    raise

# Save to data/prompts/YYYY-MM-DD.json
output_dir = Path("data/prompts")
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / f"{date.today().isoformat()}.json"

payload = {
    "date": date.today().isoformat(),
    "model": "gemini-2.5-pro",
    "count": len(batch),
    "prompts": batch,
}

with open(output_file, "w") as f:
    json.dump(payload, f, indent=2)

print(f"\nSaved to {output_file}")
print("Sample prompt:")
if batch:
    print(f"  Animal: {batch[0].get('animal')}")
    print(f"  Caption: {batch[0].get('caption')}")
    print(f"  Veo3 prompt: {batch[0].get('veo3_prompt', '')[:100]}...")
