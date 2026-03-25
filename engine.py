"""
═══════════════════════════════════════════════════════════════════
  STORYBOARD VISUAL ENGINE v7
  Purpose-built for storyboard → cinematic image pipeline
═══════════════════════════════════════════════════════════════════
  Consistency Layers:
    L1: Multi-angle character refs (front / 3/4 / action)
    L2: Environment refs (key locations)
    L3: World anchor (persistent rules in every prompt)
    L4: Multi-turn chat (grouped by section)
    L5: Post-processing (teal-orange grade + vignette + grain)
    L6: Master Shots (hero render per location, shared globally)
    L7: Visual Memory Bank (latest successful render per char/env,
        carried across sections so ABC stays ABC forever)

  Rules:
    • 1 character per panel (warn if 2+ detected)
    • Max 60 words per prompt (warn if exceeded)
    • Style prefix injected by tool, not in prompt
    • Media Video REMOVED — fully AI-generated pipeline
    • GFX removed in v3 — fully 3D pipeline (Noir + Fern only)
    • Cold Open: Noir only

  Setup:
    Double-click this file to run
"""

import os, re, json, time, sys, base64, threading, shutil
from pathlib import Path
from datetime import datetime
import numpy as np

from google import genai
from google.genai import types
from PIL import Image, ImageDraw


# ═══════════════════════════════════════════════════════════
# STYLE PRESETS — Select in UI dropdown or paste custom
# ═══════════════════════════════════════════════════════════
STYLE_PRESETS = {
    "Noir Documentary (Faceless 3D)": {
        "world_anchor": (
            "PERSISTENT WORLD RULES: "
            "All human characters are faceless mannequins with completely smooth heads — "
            "NO eyes, NO nose, NO mouth, NO facial features. "
            "Skin is smooth matte mannequin plastic. "
            "Color palette: desaturated teal and warm orange tones. "
            "Lighting: dramatic single-source with volumetric god rays, deep shadows. "
            "Film grain and vignette on every image. "
            "16:9 widescreen. Unreal Engine 5 photorealistic PBR. "
            "NEVER: cartoon, anime, 2D, text overlays, facial features. "
        ),
        "primary": (
            "3D-rendered cinematic documentary scene. "
            "Faceless mannequin figures with smooth featureless heads. "
            "Realistic body proportions, era-appropriate clothing with fabric detail. "
            "Photorealistic PBR environment. "
            "Characters in dynamic mid-action poses, never idle. "
            "Cinematic 35-85mm lens, shallow depth of field, anamorphic bokeh. "
            "Dramatic single-source lighting with volumetric god rays, deep shadows. "
            "Desaturated teal-and-orange color grade, film grain, vignette. "
            "Mood: noir-documentary, investigative, atmospheric. "
        ),
        "secondary": (
            "3D tech documentary style, premium YouTube video essay aesthetic. "
            "Isometric or orthographic camera angle. "
            "Smooth matte clay-like materials and soft plastics. "
            "Glowing neon accents and LED lights on dark moody background. "
            "Global illumination, soft shadows, ambient occlusion. "
            "Abstract representation of technology, data, or infrastructure. "
            "Sleek, polished, professional. Blender Cycles quality. "
            "No clutter, no grime, no cartoon, no 2D. "
        ),
        "char_base": (
            "3D-rendered cinematic documentary scene. "
            "Faceless mannequin figure with completely smooth head — no eyes, nose, mouth. "
            "Realistic body proportions, era-appropriate clothing with fabric detail. "
            "Photorealistic PBR environment. "
            "Cinematic 85mm lens, shallow depth of field, anamorphic bokeh. "
            "Dramatic single-source lighting with volumetric god rays, deep shadows. "
            "Desaturated teal-and-orange color grade, film grain, vignette. "
            "Unreal Engine 5 quality. No cartoon, no anime, no text, no facial features. "
        ),
        "grade": {"desat": 0.15, "teal_r": -12, "teal_g": 6, "teal_b": 15, "warm_r": 12, "warm_g": 4, "warm_b": -8, "contrast": 1.08, "vignette": 0.25, "grain": 6},
    },
    "Photorealistic Documentary": {
        "world_anchor": (
            "PERSISTENT WORLD RULES: "
            "Photorealistic photography style. Real human faces with natural expressions. "
            "Shot on ARRI Alexa Mini, Zeiss Master Prime lenses. "
            "Natural color grade, slight desaturation. "
            "Documentary cinematography — observational, intimate, authentic. "
            "16:9 widescreen. High dynamic range. "
            "NEVER: cartoon, anime, 3D render look, plastic skin, mannequin. "
        ),
        "primary": (
            "Photorealistic documentary photograph. Real human with natural skin texture and features. "
            "ARRI Alexa Mini, 35-85mm Zeiss Master Prime, shallow depth of field. "
            "Natural single-source lighting — practical lights, window light, overhead fluorescent. "
            "Muted color palette, slight blue shadows, warm highlights. "
            "Mood: intimate, observational, journalistic. "
        ),
        "secondary": (
            "Clean photographic infographic style. "
            "Shot from above on dark surface — objects arranged for explanation. "
            "Soft even lighting, minimal shadows. "
            "Educational, clear, premium documentary B-roll aesthetic. "
        ),
        "char_base": (
            "Photorealistic portrait photograph. Real human with natural skin, hair, and facial features. "
            "ARRI Alexa Mini, 85mm lens, f/2.0, shallow depth of field. "
            "Natural studio lighting — soft key light, subtle fill, dark background. "
            "Muted documentary color grade. No cartoon, no 3D render look. "
        ),
        "grade": {"desat": 0.08, "teal_r": -5, "teal_g": 3, "teal_b": 8, "warm_r": 6, "warm_g": 2, "warm_b": -4, "contrast": 1.05, "vignette": 0.20, "grain": 4},
    },
    "Anime Documentary": {
        "world_anchor": (
            "PERSISTENT WORLD RULES: "
            "Japanese anime art style. 2D hand-drawn aesthetic with cel shading. "
            "Characters have expressive anime faces — large eyes, detailed hair, emotional expressions. "
            "Backgrounds are detailed painted environments. "
            "16:9 widescreen. Studio Bones / MAPPA quality animation frames. "
            "NEVER: 3D render, photorealistic, clay, pixel art, western cartoon. "
        ),
        "primary": (
            "Anime key frame illustration. Japanese animation studio quality. "
            "Dramatic anime cinematography — dynamic angles, speed lines where appropriate. "
            "Rich painted backgrounds with atmospheric depth. "
            "Cel-shaded characters with detailed clothing and expressive body language. "
            "Dramatic anime lighting — rim lights, color-coded shadows, lens flares. "
            "Mood: intense, cinematic, emotionally charged. "
        ),
        "secondary": (
            "Anime explainer style. Clean chibi or simplified character proportions. "
            "Whiteboard or chalkboard aesthetic with hand-drawn diagrams. "
            "Soft pastel colors, clear visual hierarchy. "
            "Educational anime aesthetic — think Cells at Work or Dr. Stone explanation scenes. "
        ),
        "char_base": (
            "Anime character design sheet. Japanese animation studio quality. "
            "Full body front view and 3/4 view side by side. "
            "Detailed anime face — distinctive eye color and shape, unique hairstyle. "
            "Era-appropriate costume with fabric detail and accessories. "
            "Clean lines, cel shading, neutral background. "
        ),
        "grade": {"desat": 0.0, "teal_r": 0, "teal_g": 0, "teal_b": 0, "warm_r": 0, "warm_g": 0, "warm_b": 0, "contrast": 1.10, "vignette": 0.10, "grain": 0},
    },
    "Comic Book / Graphic Novel": {
        "world_anchor": (
            "PERSISTENT WORLD RULES: "
            "Western comic book art style. Bold ink lines, halftone dot shading. "
            "Characters have stylized but realistic proportions — not chibi, not hyper-real. "
            "Strong blacks, limited color palette with flat colors and dramatic shadows. "
            "16:9 widescreen panel composition. DC/Marvel graphic novel quality. "
            "NEVER: anime, photorealistic, 3D render, watercolor, pixel art. "
        ),
        "primary": (
            "Comic book panel illustration. Bold ink outlines, halftone dot shading. "
            "Dramatic noir-influenced composition — deep shadows, stark contrasts. "
            "Limited color palette — 4-5 colors per scene maximum. "
            "Dynamic poses and dramatic camera angles. "
            "Style reference: Sean Phillips, Alex Maleev, David Mazzucchelli. "
            "Mood: gritty, noir, graphic. "
        ),
        "secondary": (
            "Comic book infographic panel. Blueprint aesthetic with technical cross-section views. "
            "White lines on dark blue background. Callout labels and arrows. "
            "Clean technical illustration meets comic book aesthetic. "
        ),
        "char_base": (
            "Comic book character design. Bold ink outlines, flat color fills. "
            "Front view and 3/4 view side by side. "
            "Stylized but anatomically correct proportions. "
            "Distinctive silhouette and costume design. Strong shadow shapes. "
            "Halftone shading. Neutral background. Graphic novel quality. "
        ),
        "grade": {"desat": 0.05, "teal_r": -8, "teal_g": 0, "teal_b": 10, "warm_r": 8, "warm_g": 2, "warm_b": -6, "contrast": 1.15, "vignette": 0.15, "grain": 3},
    },
    "Cyberpunk Neon Noir": {
        "world_anchor": (
            "PERSISTENT WORLD RULES: "
            "Cyberpunk neon noir aesthetic. Rain-soaked futuristic city. "
            "Characters have augmented cybernetic features mixed with streetwear. "
            "Dominant colors: electric blue, hot pink, toxic green neon against dark backgrounds. "
            "Holographic UI elements floating in environment. "
            "16:9 widescreen. Unreal Engine 5 quality. "
            "NEVER: daylight, cartoon, clean/sterile, natural environments. "
        ),
        "primary": (
            "Cyberpunk cinematic scene. Rain-soaked streets, neon reflections on wet asphalt. "
            "Volumetric fog and atmospheric haze. Holographic advertisements in background. "
            "Cinematic 35mm anamorphic lens, extreme depth. "
            "Dominant neon blue and pink lighting with deep shadows. "
            "Blade Runner meets Ghost in the Shell meets Akira aesthetic. "
            "Mood: dystopian, noir, electric. "
        ),
        "secondary": (
            "Cyberpunk holographic UI explainer. Floating translucent data visualizations. "
            "Wireframe 3D models with neon edge lighting on dark void background. "
            "Sci-fi tech aesthetic — think Minority Report UI or Iron Man HUD. "
        ),
        "char_base": (
            "Cyberpunk character design. Neon-lit portrait against dark rain-soaked backdrop. "
            "Front view and 3/4 view side by side. "
            "Streetwear mixed with cybernetic augmentations. "
            "Neon rim lighting, wet surface reflections. "
            "Detailed face with cyber-enhancements. Blade Runner 2049 aesthetic. "
        ),
        "grade": {"desat": 0.0, "teal_r": -15, "teal_g": 5, "teal_b": 20, "warm_r": 15, "warm_g": -5, "warm_b": 10, "contrast": 1.12, "vignette": 0.30, "grain": 5},
    },
    "Vintage Film (70s Grain)": {
        "world_anchor": (
            "PERSISTENT WORLD RULES: "
            "1970s film photography aesthetic. Shot on Kodak Ektachrome 64T film stock. "
            "Warm amber color cast, heavy film grain, slight lens softness. "
            "Natural available light — practicals, tungsten, daylight through windows. "
            "Vintage clothing and environments accurate to the 1970s. "
            "16:9 widescreen. Real photography, not illustration. "
            "NEVER: digital look, sharp/clinical, modern objects, neon, anime. "
        ),
        "primary": (
            "1970s documentary photograph on Kodak film stock. Heavy visible film grain. "
            "Warm amber and brown tones with faded blacks. Slight lens softness at edges. "
            "Available light only — practical lamps, sunlight, overhead fluorescent. "
            "Period-accurate environments and wardrobe. "
            "Style reference: Alan Pakula, Sidney Lumet cinematography. "
            "Mood: paranoid, gritty, authentic. "
        ),
        "secondary": (
            "1970s educational filmstrip aesthetic. Vintage overhead projector look. "
            "Faded colors, rounded corners, light leak effects. "
            "Simple diagrams with hand-drawn labels on yellowed paper. "
        ),
        "char_base": (
            "1970s portrait photograph on Kodak film stock. Heavy grain, warm amber tones. "
            "Front view and 3/4 view side by side. "
            "Natural available light, shallow depth of field. "
            "Period-accurate clothing and hairstyle. "
            "Slight lens softness. Documentary portrait style. "
        ),
        "grade": {"desat": 0.10, "teal_r": 5, "teal_g": -3, "teal_b": -10, "warm_r": 18, "warm_g": 8, "warm_b": -5, "contrast": 1.03, "vignette": 0.35, "grain": 12},
    },
    "Oil Painting / Classical": {
        "world_anchor": (
            "PERSISTENT WORLD RULES: "
            "Classical oil painting on canvas. Visible brushstrokes, rich impasto texture. "
            "Rembrandt and Caravaggio chiaroscuro lighting — dramatic single source. "
            "Deep rich colors — burnt sienna, raw umber, cadmium yellow, ultramarine blue. "
            "Gallery-quality fine art, museum-worthy composition. "
            "16:9 widescreen. Traditional oil painting medium. "
            "NEVER: digital art, photorealistic, cartoon, anime, flat colors. "
        ),
        "primary": (
            "Classical oil painting on canvas. Rich impasto brushstrokes visible in texture. "
            "Chiaroscuro lighting — single dramatic light source, deep shadow. "
            "Old master composition and color palette — warm earth tones, deep blues. "
            "Figures have weight and presence, draped in rich fabrics. "
            "Style reference: Rembrandt, Caravaggio, Vermeer. "
            "Mood: dramatic, timeless, gravitas. "
        ),
        "secondary": (
            "Technical illustration in old master drawing style. "
            "Sepia ink on parchment paper. Leonardo da Vinci notebook aesthetic. "
            "Cross-section diagrams with handwritten labels. Aged paper texture. "
        ),
        "char_base": (
            "Classical oil portrait painting. Rich brushwork, canvas texture visible. "
            "Front view and 3/4 view side by side. "
            "Chiaroscuro lighting — dramatic single source. "
            "Deep rich earth tone palette. Gallery-worthy composition. "
            "Old master portrait style — Rembrandt, Caravaggio influence. "
        ),
        "grade": {"desat": 0.05, "teal_r": 0, "teal_g": -5, "teal_b": -8, "warm_r": 15, "warm_g": 8, "warm_b": -3, "contrast": 1.06, "vignette": 0.30, "grain": 2},
    },
    "Watercolor / Storybook": {
        "world_anchor": (
            "PERSISTENT WORLD RULES: "
            "Delicate watercolor painting on textured paper. Visible paper grain and water blooms. "
            "Soft diffused edges, subtle color bleeding between shapes. "
            "Pastel and muted color palette — soft blues, warm pinks, sage greens, cream. "
            "Gentle and contemplative mood. Children's book illustration quality. "
            "16:9 widescreen. Traditional watercolor medium. "
            "NEVER: photorealistic, harsh shadows, neon colors, anime, digital look. "
        ),
        "primary": (
            "Watercolor illustration on textured cold-pressed paper. "
            "Visible paper grain, soft wet-on-wet color bleeds, delicate dry brush details. "
            "Soft diffused natural lighting — no harsh shadows. "
            "Muted pastel palette with occasional deeper accent colors. "
            "Style reference: Shaun Tan, Jon Klassen, Beatrix Potter. "
            "Mood: gentle, contemplative, melancholic beauty. "
        ),
        "secondary": (
            "Watercolor diagram on cream paper. Soft hand-painted labels and arrows. "
            "Botanical illustration precision meets watercolor softness. "
            "Educational diagram with artistic beauty. Aged paper texture. "
        ),
        "char_base": (
            "Watercolor character illustration on textured paper. "
            "Front view and 3/4 view side by side. "
            "Soft edges, visible paper grain, subtle color bleeding. "
            "Gentle muted palette. Delicate brushwork. "
            "Children's book illustration quality. Cream paper background. "
        ),
        "grade": {"desat": 0.0, "teal_r": 0, "teal_g": 2, "teal_b": 5, "warm_r": 5, "warm_g": 3, "warm_b": 0, "contrast": 1.02, "vignette": 0.10, "grain": 0},
    },
    "Clay / Stop Motion": {
        "world_anchor": (
            "PERSISTENT WORLD RULES: "
            "Claymation stop-motion animation style. Characters and environments made of clay and plasticine. "
            "Visible fingerprints and tool marks on surfaces. Miniature practical sets. "
            "Warm studio lighting with soft shadows. Slightly textured, handmade quality. "
            "16:9 widescreen. Laika Studios / Aardman quality. "
            "NEVER: photorealistic, anime, flat 2D, digital smooth surfaces. "
        ),
        "primary": (
            "Claymation stop-motion scene. Characters sculpted from plasticine clay. "
            "Miniature practical set with handcrafted props and environments. "
            "Visible fingerprints and sculpting tool marks on all surfaces. "
            "Warm studio lighting, soft shadows, shallow depth of field from macro lens. "
            "Tilt-shift miniature effect. Coraline / Kubo quality. "
            "Mood: tactile, handcrafted, charming but slightly eerie. "
        ),
        "secondary": (
            "Claymation diorama cutaway. Miniature cross-section model on turntable. "
            "Clay and wire armature visible in educational explainer style. "
            "Warm studio lighting, clean presentation. "
        ),
        "char_base": (
            "Claymation character design. Sculpted plasticine clay figure. "
            "Front view and 3/4 view side by side on miniature turntable. "
            "Visible fingerprints, handmade texture. Wire armature poseable joints. "
            "Warm studio lighting. Macro lens shallow depth of field. "
            "Laika Studios quality — Coraline, Kubo aesthetic. "
        ),
        "grade": {"desat": 0.0, "teal_r": 0, "teal_g": 2, "teal_b": 0, "warm_r": 10, "warm_g": 6, "warm_b": 0, "contrast": 1.04, "vignette": 0.15, "grain": 2},
    },
}

# Active preset — changed by UI dropdown
active_preset = STYLE_PRESETS["Noir Documentary (Faceless 3D)"]

def get_world_anchor():
    return active_preset["world_anchor"]

def get_primary_style():
    return active_preset["primary"]

def get_secondary_style():
    return active_preset["secondary"]

def get_char_base():
    return active_preset["char_base"]

def get_grade_params():
    return active_preset["grade"]



# ═══════════════════════════════════════════════════════════
# CHARACTER + ENVIRONMENT DEFINITIONS
# ═══════════════════════════════════════════════════════════
CHARACTERS = {
    "leo": {
        "name": "Leonardo Notarbartolo",
        "alias": [
            "Notarbartolo", "Leonardo", "Italian man",
            "charcoal suit", "tailored charcoal suit", "charcoal tailored suit",
            "slicked-back hair", "dark slicked-back hair",
            "gold watch", "thin gold watch",
            "white dress shirt", "open-collar white",
            "navy three-piece", "tailored dark navy",
        ],
        "desc": "Mid-50s, medium build, dark slicked-back hair, tailored charcoal suit, open-collar white dress shirt, thin gold watch on left wrist, polished black shoes",
        "views": {
            "front": "CHARACTER REFERENCE — FRONT VIEW. Mid-50s man, medium build, dark slicked-back hair, tailored charcoal suit, open-collar white dress shirt, thin gold watch on left wrist, polished black shoes. Light-toned smooth mannequin skin. Confident, one hand in pocket.",
            "three_quarter": "CHARACTER REFERENCE — 3/4 VIEW. Mid-50s man, dark slicked-back hair, charcoal suit, open-collar white shirt, gold watch. Light-toned smooth mannequin skin. Looking to the side.",
            "action": "CHARACTER REFERENCE — ACTION POSE. Man in charcoal suit and white dress shirt, slicked-back hair. Leaning over desk examining documents, gold watch visible. Light-toned smooth mannequin skin.",
        },
    },
    "monster": {
        "name": "The Monster",
        "alias": [
            "Monster", "Finotto", "Ferdinando",
            "massive barrel-chested", "barrel-chested",
            "black leather jacket", "dark henley",
            "enormous hands", "heavy work boots",
            "thick silver ring",
            # backward compat
            "tall muscular", "dark work coveralls", "heavy boots", "dark coveralls",
        ],
        "desc": "Late 40s, massive barrel-chested build, broad shoulders, black leather jacket over dark henley shirt, heavy work boots, thick silver ring on right hand",
        "views": {
            "front": "CHARACTER REFERENCE — FRONT VIEW. Late 40s massive barrel-chested man, broad shoulders, black leather jacket over dark henley shirt, heavy work boots, thick silver ring on right hand. Light-toned smooth mannequin skin. Arms crossed, imposing stance.",
            "three_quarter": "CHARACTER REFERENCE — 3/4 VIEW. Massive barrel-chested man in black leather jacket, dark henley, heavy boots. Light-toned smooth mannequin skin. Powerful build visible.",
            "action": "CHARACTER REFERENCE — ACTION POSE. Massive man in black leather jacket, enormous hands working on a lock mechanism with tools. Heavy work boots. Light-toned smooth mannequin skin.",
        },
    },
    "genius": {
        "name": "The Genius",
        "alias": [
            "Genius", "D'Onorio", "Elio",
            "dark navy technical jacket", "technical jacket",
            "thin-framed glasses", "thin precise hands",
            "rubber-soled shoes", "circuit board",
            # backward compat
            "wire-rimmed glasses", "wire-frame glasses",
            "olive utility vest", "olive vest", "tactical vest",
        ],
        "desc": "Early 50s, lean and wiry, precise movements, dark navy technical jacket, thin-framed glasses, black rubber-soled shoes, digital watch",
        "views": {
            "front": "CHARACTER REFERENCE — FRONT VIEW. Early 50s lean wiry man, dark navy technical jacket, thin-framed glasses, black rubber-soled shoes, digital watch. Light-toned smooth mannequin skin. Precise technical posture.",
            "three_quarter": "CHARACTER REFERENCE — 3/4 VIEW. Lean wiry man with thin-framed glasses, dark navy technical jacket, digital watch. Light-toned smooth mannequin skin. Examining something with precision.",
            "action": "CHARACTER REFERENCE — ACTION POSE. Lean man in dark navy technical jacket, thin-framed glasses, working on electronic circuit board. Digital watch visible. Light-toned smooth mannequin skin.",
        },
    },
    "speedy": {
        "name": "Speedy",
        "alias": [
            "Speedy", "Tavano", "Pietro",
            "wrinkled olive field jacket", "olive field jacket", "olive jacket",
            "thin nervous man", "nervous hands", "thin and fidgety",
            "cheap digital watch", "scuffed brown boots",
            # backward compat
            "lookout", "thin wiry man", "dark canvas jacket", "black wool beanie",
        ],
        "desc": "Late 40s, thin and fidgety, nervous energy, wrinkled olive field jacket, dark jeans, scuffed brown boots, cheap digital watch",
        "views": {
            "front": "CHARACTER REFERENCE — FRONT VIEW. Late 40s thin fidgety man in wrinkled olive field jacket, dark jeans, scuffed brown boots, cheap digital watch. Light-toned smooth mannequin skin. Nervous posture, shoulders hunched.",
            "three_quarter": "CHARACTER REFERENCE — 3/4 VIEW. Thin man in olive field jacket, dark jeans, brown boots. Light-toned smooth mannequin skin. Looking over shoulder nervously.",
            "action": "CHARACTER REFERENCE — ACTION POSE. Thin nervous man in olive field jacket sitting in car, hands gripping steering wheel tensely. Cheap digital watch. Light-toned smooth mannequin skin.",
        },
    },
    "king": {
        "name": "The King of Keys",
        "alias": [
            "King of Keys",
            "plain black coat", "leather gloves", "leather-gloved hands",
            "dark trousers", "nondescript",
            "key blank", "brass key",
            # backward compat
            "older man", "white hair", "wool sweater", "wool coat",
        ],
        "desc": "Age unknown, medium build, completely nondescript, plain black coat, dark trousers, leather gloves, no distinguishing accessories, face always in shadow",
        "views": {
            "front": "CHARACTER REFERENCE — FRONT VIEW. Nondescript medium-build man in plain black coat, dark trousers, leather gloves. Light-toned smooth mannequin skin. Face partly in shadow. No distinguishing features.",
            "three_quarter": "CHARACTER REFERENCE — 3/4 VIEW. Medium-build man in plain black coat, leather gloves. Light-toned smooth mannequin skin. Turned away, face in shadow. Examining key.",
            "action": "CHARACTER REFERENCE — ACTION POSE. Man in plain black coat, leather gloves filing a brass key blank on a vise. Face entirely in shadow. Light-toned smooth mannequin skin.",
        },
    },
    "guard": {
        "name": "Security Guard",
        "alias": [
            "security guard", "guard",
            "security uniform", "navy security uniform", "navy blue security",
            "shoulder patches", "clip-on ID badge", "utility belt",
        ],
        "desc": "Middle-aged, average build, navy blue security uniform with shoulder patches, black utility belt, clip-on ID badge, rubber-soled boots",
        "views": {
            "front": "CHARACTER REFERENCE — FRONT VIEW. Middle-aged average-build man in navy blue security uniform with shoulder patches, black utility belt, clip-on ID badge, rubber-soled boots. Light-toned smooth mannequin skin. Routine posture.",
            "three_quarter": "CHARACTER REFERENCE — 3/4 VIEW. Man in navy security uniform, utility belt, ID badge. Light-toned smooth mannequin skin. Walking posture.",
            "action": "CHARACTER REFERENCE — ACTION POSE. Man in navy security uniform walking down corridor, keys on belt. Routine movement. Light-toned smooth mannequin skin.",
        },
    },
    "vancamp": {
        "name": "August Van Camp",
        "alias": [
            "Van Camp", "August",
            "brown corduroy jacket", "faded brown corduroy", "corduroy jacket",
            "flat cap", "wellington boots", "muddy wellington",
            "slight build", "weathered",
            # backward compat
            "retired grocer", "red plaid flannel", "plaid flannel", "stocky",
        ],
        "desc": "59 years old, slight build, weathered features, faded brown corduroy jacket, flat cap, dark wool trousers, muddy wellington boots",
        "views": {
            "front": "CHARACTER REFERENCE — FRONT VIEW. 59-year-old man, slight build, faded brown corduroy jacket, flat cap, dark wool trousers, muddy wellington boots. Light-toned smooth mannequin skin. Hunched slightly, observant.",
            "three_quarter": "CHARACTER REFERENCE — 3/4 VIEW. Slight man in brown corduroy jacket, flat cap, wellington boots. Light-toned smooth mannequin skin. Walking slowly, looking at ground.",
            "action": "CHARACTER REFERENCE — ACTION POSE. Slight man in brown corduroy jacket and flat cap crouching on muddy path examining debris. Wellington boots. Light-toned smooth mannequin skin.",
        },
    },
    "peys": {
        "name": "Detective Peys",
        "alias": ["Peys", "detective", "Detective Peys", "Patrick Peys", "dark wool overcoat", "gray scarf"],
        "desc": "Middle-aged man, sturdy build, dark gray wool overcoat, gray scarf, short-cropped gray hair, detective badge on belt",
        "views": {
            "front": "CHARACTER REFERENCE — FRONT VIEW. Middle-aged man in dark wool overcoat and gray scarf, short-cropped gray hair, sturdy build. Light-toned smooth mannequin skin. Standing straight, hands at sides.",
            "three_quarter": "CHARACTER REFERENCE — 3/4 VIEW. Middle-aged man in dark wool overcoat and gray scarf, short-cropped gray hair. Light-toned smooth mannequin skin. Slight turn to left.",
            "action": "CHARACTER REFERENCE — ACTION POSE. Middle-aged man in dark wool overcoat and gray scarf. Walking through dark corridor, hand reaching for door. Light-toned smooth mannequin skin.",
        },
    },
}

def get_char_view_prompt(cid, view):
    """Build full character ref prompt: active preset char_base + character-specific detail."""
    chars = get_active_characters()
    if cid in chars and view in chars[cid].get("views", {}):
        return get_char_base() + chars[cid]["views"][view]
    return get_char_base()

ENVIRONMENTS = {
    "vault_interior": {"name": "Vault Interior", "keywords": ["vault interior", "vault floor", "safe deposit box", "boxes", "vault room", "inside vault", "vault wall"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Interior of massive underground bank vault. Rows of metal safe deposit boxes. Single dramatic overhead spotlight. Polished concrete floor. Industrial. Wide 16:9. No people."},
    "vault_door": {"name": "Vault Door", "keywords": ["vault door", "massive circular", "heavy metal door", "combination lock", "combination dial", "steel vault door", "colossal steel"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Massive circular steel vault door in concrete wall. Heavy metal frame. Combination dial. Single overhead light. Underground. Wide 16:9. No people."},
    "corridor": {"name": "Corridor", "keywords": ["corridor", "hallway", "stairwell", "stairs", "concrete corridor", "vault level"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Dimly lit concrete corridor. Fluorescent lights, harsh shadows. Metal railing. Industrial pipes. Emergency exit signs. Wide 16:9. No people."},
    "office": {"name": "Office", "keywords": ["office", "office desk", "conference", "meeting", "leather briefcase", "gem loupe"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Small rented office in old European building. Desk, chair, window with overcast daylight. Warm desk lamp. Wide 16:9. No people."},
    "exterior": {"name": "Building Exterior", "keywords": ["building exterior", "diamond centre", "facade", "diamond center", "commercial building", "stone and glass building", "bollards"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Imposing stone European building exterior. Grand old architecture. Security bollards. Overcast sky. Dramatic low angle. Wide 16:9. No people."},
    "diamond_district": {"name": "Diamond District", "keywords": ["diamond district", "cobblestone", "jewelry shops", "diamond capital", "three-block", "deserted", "shuttered storefronts"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Narrow European diamond district street at night. Cobblestone road, jewelry shops with golden window displays, wet pavement. Security cameras. Deserted. Wide 16:9. No people."},
    "garage": {"name": "Garage", "keywords": ["garage", "parking", "underground garage", "garage door", "garage exit"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Underground parking garage. Concrete ramp into darkness. Yellow sodium lights. Metal garage door. Nighttime. Wide 16:9. No people."},
    "apartment": {"name": "Apartment", "keywords": ["apartment", "divide", "split the take"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Dark European apartment. Wooden table under warm desk lamp. Sparse, functional. Curtains drawn. Wide 16:9. No people."},
    "warehouse": {"name": "Warehouse", "keywords": ["warehouse", "replica vault", "practice", "construction lights"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Large abandoned warehouse interior. Crude replica vault constructed from steel plates and concrete blocks. Construction lights on stands. Dark cavernous space. Industrial. Wide 16:9. No people."},
    "workshop": {"name": "Workshop", "keywords": ["workshop", "workbench", "sparks", "grinding", "tools", "precision tools", "filing"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Dimly lit mechanic's workshop. Heavy workbench with scattered tools. Single overhead bulb. Metalworking vise. Industrial grit. Wide 16:9. No people."},
    "vancamp_property": {"name": "Van Camp's Property", "keywords": ["van camp", "countryside", "property", "garden", "rural", "porch", "forest", "dirt road", "dirt path", "wooded", "muddy path", "bare trees", "bare winter trees"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Modest Belgian countryside near E19 motorway at dawn. Bare winter trees, muddy path, dead leaves. Wooded area adjacent to highway. Quiet rural morning. Wide 16:9. No people."},
    "highway": {"name": "Highway", "keywords": ["highway", "motorway", "E19", "empty highway", "open road"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. European highway at night. Empty road into darkness. Forest both sides. Wet asphalt. Tail lights in distance. Wide 16:9. No people."},
    "crime_scene": {"name": "Crime Scene", "keywords": ["police tape", "evidence markers", "forensic", "cordoned", "woodland clearing"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Muddy woodland clearing cordoned with police tape. Evidence markers on ground. Overcast sky. Forensic atmosphere. Wide 16:9. No people."},
    "prison": {"name": "Prison / Interview Room", "keywords": ["prison", "prison clothing", "interview room", "metal table", "stark", "barred window"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Stark prison interview room. Metal table and chairs. Single overhead light. Concrete walls. Small barred window. Institutional. Wide 16:9. No people."},
    "factory_district": {"name": "Factory District", "keywords": ["factory", "industrial cityscape", "smokestacks", "fiat", "car factories", "chain-link"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Industrial cityscape at dusk. Massive factory buildings with smokestacks. Chain-link fencing. Puddles reflecting factory lights. Gritty. Wide 16:9. No people."},
    "italian_rural": {"name": "Italian Rural", "keywords": ["rural Italian", "Italian property", "wood pellet", "rolling hills", "modest rural"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Modest rural Italian property at dusk. Small warehouse building. Rolling hills background. Warm amber light from single window. Peaceful but melancholy. Wide 16:9. No people."},
    "courtroom": {"name": "Courtroom", "keywords": ["courtroom", "court", "trial", "judge", "verdict", "sentencing", "testimony"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Belgian courtroom interior. Wooden judge bench elevated, witness stand, gallery seating. Institutional lighting, wood paneling. Formal, austere. Wide 16:9. No people."},
    "police_station": {"name": "Police Station", "keywords": ["police station", "interrogation", "detective office", "diamond detective"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Belgian police station interior. Interrogation room with metal table and chairs. One-way mirror. Harsh fluorescent lighting. Institutional, cold. Wide 16:9. No people."},
    "aerial_city": {"name": "Antwerp Aerial", "keywords": ["aerial", "skyline", "overview", "bird", "Gothic architecture", "rooftops"],
        "prompt_detail": "ENVIRONMENT REFERENCE — EMPTY. Dramatic aerial view of Antwerp city at dusk. Diamond district visible. Gothic architecture. Overcast sky, golden hour light breaking through clouds. Cinematic establishing shot. Wide 16:9. No people."},
}

def get_env_prompt(eid):
    """Build environment prompt using active preset."""
    return get_world_anchor() + get_primary_style() + ENVIRONMENTS[eid]["prompt_detail"]


# ═══════════════════════════════════════════════════════════
# PARSER
# ═══════════════════════════════════════════════════════════
def parse_storyboard(text):
    """Parse JSX storyboard → list of panel dicts.
    Supports:
      - v1 flat: const P = [{ id, t, g, f, s, vo, ... }]
      - v2 nested: const SECTIONS = [{ id, name, panels: [{ id, type, gemini:{}, kling:{}, ... }] }]
    Returns normalized flat list with consistent field names.
    """

    # ── TRY v2 NESTED FORMAT FIRST ──
    sec_match = re.search(r'const\s+SECTIONS\s*=\s*\[', text)
    if sec_match:
        return _parse_v2(text)

    # ── FALLBACK: v1 FLAT FORMAT ──
    match = re.search(r'const\s+(?:P|panels)\s*=\s*\[(.*?)\];', text, re.DOTALL)
    if not match:
        return []
    panels = []
    for m in re.finditer(r'\{([^{}]+)\}', match.group(1), re.DOTALL):
        p = {}
        for sf in re.findall(r'(\w+)\s*:\s*"((?:[^"\\]|\\.)*)"', m.group(1)):
            p[sf[0]] = sf[1]
        for nf in re.findall(r'(\w+)\s*:\s*(\d+)(?!\w)', m.group(1)):
            if nf[0] not in p:
                p[nf[0]] = int(nf[1])
        if 'id' in p:
            panels.append(p)
    return panels


def _parse_v2(text):
    """Parse v2 nested SECTIONS format. Handles both id/name and title formats."""
    panels = []
    
    # Find the SECTIONS array start
    sec_start = re.search(r'const\s+SECTIONS\s*=\s*\[', text)
    if not sec_start:
        return panels
    
    sections_text = text[sec_start.end():]
    
    # Find end of SECTIONS array
    depth = 1
    pos = 0
    while pos < len(sections_text) and depth > 0:
        if sections_text[pos] == '[': depth += 1
        elif sections_text[pos] == ']': depth -= 1
        pos += 1
    sections_text = sections_text[:pos-1]
    
    section_num = 0
    
    # Find each "panels: [" — only real sections have this
    for pm in re.finditer(r'panels:\s*\[', sections_text):
        # Walk backwards to find opening { of this section object
        obj_start = pm.start()
        brace_depth = 0
        for i in range(obj_start, -1, -1):
            if sections_text[i] == '{':
                if brace_depth == 0:
                    obj_start = i
                    break
                brace_depth -= 1
            elif sections_text[i] == '}':
                brace_depth += 1
        
        header_text = sections_text[obj_start:pm.start()]
        
        section_num += 1
        sec_name = f"Section {section_num}"
        sec_id = f"S{section_num}"
        
        # Try id: "S..." + name: "..." (old format)
        id_m = re.search(r'id:\s*"(S\d+)"', header_text)
        name_m = re.search(r'name:\s*"([^"]+)"', header_text)
        
        if id_m and name_m:
            sec_id = id_m.group(1)
            sec_name = name_m.group(1)
        else:
            # Try title: "..." (new format)
            title_m = re.search(r'title:\s*"([^"]+)"', header_text)
            if title_m:
                sec_name = title_m.group(1)
        
        # Extract panels array by bracket matching
        panels_start = pm.end()
        depth = 1
        pos = panels_start
        while pos < len(sections_text) and depth > 0:
            if sections_text[pos] == '[': depth += 1
            elif sections_text[pos] == ']': depth -= 1
            pos += 1
        panels_text_inner = sections_text[panels_start:pos-1]
        
        # Parse individual panel objects
        panel_objects = _extract_objects(panels_text_inner)
        for ptext in panel_objects:
            p = _parse_panel_object(ptext, sec_id, sec_name)
            if p and p.get('id'):
                panels.append(p)
    
    return panels



def _extract_objects(text):
    """Extract top-level { } objects from a comma-separated list, handling nesting."""
    objects = []
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                objects.append(text[start:i+1])
                start = None
    return objects


def _parse_panel_object(ptext, sec_id, sec_name):
    """Parse a single panel object string into a normalized dict."""
    p = {'section': sec_name, 'section_id': sec_id}

    # ID
    m = re.search(r'id:\s*"([^"]+)"', ptext)
    if m: p['id'] = m.group(1)

    # Type (noir/fern/gfx)
    m = re.search(r'type:\s*"([^"]+)"', ptext)
    if m: p['type'] = m.group(1)

    # Transition
    m = re.search(r'transition:\s*"([^"]+)"', ptext)
    if m: p['tr'] = m.group(1)

    # Music
    m = re.search(r'music:\s*"([^"]+)"', ptext)
    if m: p['m'] = m.group(1)

    # Voiceover
    m = re.search(r'vo:\s*"((?:[^"\\]|\\.)*)"', ptext)
    if m: p['vo'] = m.group(1)

    # Gemini block: { file: "...", prompt: "..." }
    gm = re.search(r'gemini:\s*\{([^}]+)\}', ptext)
    if gm:
        gtext = gm.group(1)
        fm = re.search(r'file:\s*"([^"]+)"', gtext)
        pm = re.search(r'prompt:\s*"((?:[^"\\]|\\.)*)"', gtext)
        if fm: p['f'] = fm.group(1).replace('.png', '')  # strip extension for consistency
        if pm: p['g'] = pm.group(1)

    # Kling block: { file: "...", note: "..." }
    km = re.search(r'kling:\s*\{([^}]+)\}', ptext)
    if km:
        ktext = km.group(1)
        fm = re.search(r'file:\s*"([^"]+)"', ktext)
        nm = re.search(r'note:\s*"((?:[^"\\]|\\.)*)"', ktext)
        if fm: p['kling_file'] = fm.group(1)
        if nm: p['k'] = nm.group(1)

    # Overlay block: { main: "...", style: "..." }
    om = re.search(r'overlay:\s*\{([^}]+)\}', ptext)
    if om:
        otext = om.group(1)
        mm = re.search(r'main:\s*"((?:[^"\\]|\\.)*)"', otext)
        sm = re.search(r'style:\s*"((?:[^"\\]|\\.)*)"', otext)
        if mm: p['overlay_main'] = mm.group(1)
        if sm: p['overlay_style'] = sm.group(1)

    # Hera prompts (GFX): array of strings
    hm = re.search(r'hera:\s*\[(.*?)\]', ptext, re.DOTALL)
    if hm:
        hera_text = hm.group(1)
        p['hera'] = re.findall(r'"((?:[^"\\]|\\.)*)"', hera_text)

    # Style context (GFX)
    # Must match style: "..." but NOT overlay.style
    # Find style at panel level (not inside overlay block)
    sm = re.search(r'(?<!\w)style:\s*"((?:[^"\\]|\\.)*)"', ptext)
    if sm and 'hera' in p:  # only for GFX panels
        p['hera_style'] = sm.group(1)

    # Cold open detection (S1 = cold open)
    if sec_id == 'S1':
        p['co'] = 1


    return p


def get_asset_type(panel):
    """Normalize asset type for STYLE selection (noir styling or fern styling)."""
    t = panel.get('type', panel.get('t', panel.get('assetType', ''))).lower()
    if t in ('i2v', 'parallax', 'noir') or 'noir' in t:
        return 'noir'
    elif t in ('explain', 'fern') or 'fern' in t:
        return 'fern'
    elif 'media' in t or t == 'media':
        return 'media'
    elif 'gfx' in t:
        return 'fern'
    return 'unknown'






def get_image_prompt(panel):
    """Extract the image generation prompt from panel."""
    return panel.get('g', panel.get('geminiPrompt', panel.get('prompt', '')))


def get_section(panel):
    """Extract section name."""
    return panel.get('section', panel.get('s', panel.get('scene', 'Unknown')))


# ═══════════════════════════════════════════════════════════
# AUTO-EXTRACT CHARACTERS FROM STORYBOARD
# ═══════════════════════════════════════════════════════════
# Runtime store for storyboard-extracted characters
_dynamic_characters = {}

# Clothing/appearance keywords that make good aliases
_CLOTHING_WORDS = {
    "suit", "jacket", "coat", "shirt", "vest", "hoodie", "coveralls", "uniform",
    "boots", "shoes", "gloves", "hat", "cap", "glasses", "watch", "ring", "tie",
    "turtleneck", "henley", "flannel", "corduroy", "trousers", "jeans", "pants",
    "leather", "wool", "silk", "denim",
}

def auto_extract_characters(text):
    """Parse CHARACTERS array from storyboard JSX, generate aliases from descriptions.
    Returns dict compatible with engine CHARACTERS format."""
    match = re.search(r'const\s+CHARACTERS\s*=\s*\[', text)
    if not match:
        return {}

    start = match.end()
    depth = 1
    pos = start
    while pos < len(text) and depth > 0:
        if text[pos] == '[': depth += 1
        elif text[pos] == ']': depth -= 1
        pos += 1
    chars_text = text[start:pos-1]

    extracted = {}
    for obj in _extract_objects(chars_text):
        name_m = re.search(r'name:\s*"([^"]+)"', obj)
        desc_m = re.search(r'desc:\s*"([^"]+)"', obj)
        if not name_m or not desc_m:
            continue

        name = name_m.group(1)
        desc = desc_m.group(1)
        cid = _make_char_id(name)

        aliases = _extract_aliases(name, desc)

        # Build simple views from desc
        base_desc = desc.split(". Mannequin: ")[-1] if ". Mannequin: " in desc else desc
        views = {
            "front": f"CHARACTER REFERENCE — FRONT VIEW. {base_desc} Light-toned smooth mannequin skin. Standing straight.",
            "three_quarter": f"CHARACTER REFERENCE — 3/4 VIEW. {base_desc} Light-toned smooth mannequin skin. Slight turn.",
            "action": f"CHARACTER REFERENCE — ACTION POSE. {base_desc} Light-toned smooth mannequin skin. In action.",
        }

        extracted[cid] = {
            "name": name,
            "alias": aliases,
            "desc": desc,
            "views": views,
        }

    return extracted


def _make_char_id(name):
    """Generate a short character ID from name."""
    name_lower = name.lower()
    # Known mappings
    if "notarbartolo" in name_lower or "leonardo" in name_lower: return "leo"
    if "monster" in name_lower: return "monster"
    if "genius" in name_lower: return "genius"
    if "speedy" in name_lower: return "speedy"
    if "king of keys" in name_lower: return "king"
    if "van camp" in name_lower: return "vancamp"
    if "peys" in name_lower: return "peys"
    if "guard" in name_lower or "security" in name_lower: return "guard"
    # Fallback: first word
    return re.sub(r'[^a-z0-9]', '', name_lower.split()[0])[:8]


def _extract_aliases(name, desc):
    """Generate detection aliases from character name and description."""
    aliases = []

    # Name parts
    parts = re.split(r'[\s\(\)]+', name)
    for p in parts:
        p = p.strip()
        if len(p) > 2 and p.lower() not in {"the", "and"}:
            aliases.append(p)

    # Multi-word name aliases
    if "(" in name:
        # "The Monster (Ferdinando Finotto)" → "The Monster", "Finotto"
        before = name.split("(")[0].strip()
        inside = name.split("(")[1].rstrip(")")
        if before: aliases.append(before)
        for w in inside.split():
            if len(w) > 3: aliases.append(w)

    # Clothing phrases from desc
    # Split by commas and periods
    phrases = re.split(r'[,\.]+', desc)
    for phrase in phrases:
        phrase = phrase.strip().lower()
        # Check if phrase contains a clothing keyword
        words = phrase.split()
        if any(w in _CLOTHING_WORDS for w in words) and 2 <= len(words) <= 5:
            aliases.append(phrase)

    # Deduplicate preserving order
    seen = set()
    unique = []
    for a in aliases:
        key = a.lower().strip()
        if key not in seen and len(key) > 2:
            seen.add(key)
            unique.append(a.strip())
    return unique


def load_dynamic_characters(storyboard_text):
    """Extract characters from storyboard and merge with hardcoded defaults.
    Call this at upload time."""
    global _dynamic_characters
    extracted = auto_extract_characters(storyboard_text)
    if extracted:
        # Start with hardcoded, overlay with extracted
        merged = dict(CHARACTERS)
        for cid, char in extracted.items():
            if cid in merged:
                # Merge aliases: keep hardcoded + add extracted
                existing_aliases = set(a.lower() for a in merged[cid]["alias"])
                new_aliases = list(merged[cid]["alias"])
                for a in char["alias"]:
                    if a.lower() not in existing_aliases:
                        new_aliases.append(a)
                        existing_aliases.add(a.lower())
                merged[cid]["alias"] = new_aliases
                # Update desc and views from storyboard (more specific)
                merged[cid]["desc"] = char["desc"]
                merged[cid]["views"] = char["views"]
                merged[cid]["name"] = char["name"]
            else:
                # New character not in hardcoded
                merged[cid] = char
        _dynamic_characters = merged
    else:
        _dynamic_characters = dict(CHARACTERS)
    return _dynamic_characters


def get_active_characters():
    """Return dynamic characters if loaded, else hardcoded."""
    return _dynamic_characters if _dynamic_characters else CHARACTERS


# ═══════════════════════════════════════════════════════════
# CHARACTER + ENV DETECTION
# ═══════════════════════════════════════════════════════════
def detect_characters(prompt, vo=""):
    """Detect characters in prompt. Returns list of char IDs."""
    text = ((prompt or "") + " " + (vo or "")).lower()
    chars = get_active_characters()
    found = []
    for cid, c in chars.items():
        for alias in c["alias"]:
            if alias.lower() in text:
                if cid not in found:
                    found.append(cid)
                break
    return found


def detect_environment(prompt, vo=""):
    """Detect environment/location."""
    text = ((prompt or "") + " " + (vo or "")).lower()
    for eid, env in ENVIRONMENTS.items():
        for kw in env["keywords"]:
            if kw.lower() in text:
                return eid
    return None


def count_words(text):
    return len(text.split()) if text else 0


# ═══════════════════════════════════════════════════════════
# PROMPT BUILDER
# ═══════════════════════════════════════════════════════════
def build_prompt(panel, char_id=None, env_id=None):
    """Build generation prompt: ANCHOR + CHAR_REF + ENV_REF + STYLE + SCENE."""
    scene_prompt = get_image_prompt(panel)
    asset = get_asset_type(panel)

    style = get_primary_style() if asset == 'noir' else get_secondary_style()

    # Character ref instruction (1 character only)
    char_str = ""
    chars = get_active_characters()
    if char_id and char_id in chars:
        char_str = (
            f"SUBJECT CONSISTENCY: The character in this scene is {chars[char_id]['name']}. "
            f"Maintain strict visual consistency with the provided character reference image. "
            f"Match clothing, build, and appearance exactly. "
        )

    # Environment ref instruction
    env_str = ""
    if env_id and env_id in ENVIRONMENTS:
        env_str = (
            f"ENVIRONMENT CONSISTENCY: This scene takes place in {ENVIRONMENTS[env_id]['name']}. "
            f"Maintain visual consistency with the environment reference image. "
        )

    return get_world_anchor() + char_str + env_str + style + scene_prompt


# ═══════════════════════════════════════════════════════════
# CONFIG FILE — saves API key + settings
# ═══════════════════════════════════════════════════════════
CONFIG_FILE = Path("storyboard_config.json")

def load_config():
    if CONFIG_FILE.exists():
        try: return json.loads(CONFIG_FILE.read_text())
        except: pass
    return {}

def save_config(data):
    existing = load_config()
    existing.update(data)
    CONFIG_FILE.write_text(json.dumps(existing, indent=2))

# Image output settings — updated by UI dropdowns
image_settings = {
    "resolution": "2K (recommended)",
    "aspect_ratio": "16:9",
    "model": "gemini-3-pro-image-preview",
}

MODEL_OPTIONS = {
    "Nano Banana Pro (Best)": "gemini-3-pro-image-preview",
    "Nano Banana 2 (Fast)": "gemini-3.1-flash-image-preview",
}

RESOLUTION_MAP = {
    "1K (fast, draft)": "1K",
    "2K (recommended)": "2K",
    "4K (production)": "4K",
}

AR_OPTIONS = ["16:9", "9:16", "4:3", "3:4", "1:1", "21:9"]

# ═══════════════════════════════════════════════════════════
# API GENERATION
# ═══════════════════════════════════════════════════════════
def get_config():
    ar = image_settings.get("aspect_ratio", "16:9")
    res_label = image_settings.get("resolution", "2K (recommended)")
    res_val = RESOLUTION_MAP.get(res_label, "2K")
    try:
        return types.GenerateContentConfig(
            response_modalities=['IMAGE', 'TEXT'],
            image_config=types.ImageConfig(
                aspect_ratio=ar,
                image_size=res_val,
                output_compression_quality=100,
            )
        )
    except:
        # Fallback without image_size for older SDK versions
        return types.GenerateContentConfig(
            response_modalities=['IMAGE', 'TEXT'],
            image_config=types.ImageConfig(aspect_ratio=ar)
        )


def extract_image(response):
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            d = part.inline_data.data
            return base64.b64decode(d) if isinstance(d, str) else d
    return None


def get_active_model():
    return image_settings.get("model", "gemini-3.1-flash-image-preview")


def gen_single(client, prompt, ref_paths=None, max_retries=3):
    contents = []
    if ref_paths:
        for rp in ref_paths:
            if Path(rp).exists():
                contents.append(Image.open(rp))
    contents.append(prompt)
    for attempt in range(max_retries):
        try:
            resp = client.models.generate_content(
                model=get_active_model(), contents=contents, config=get_config()
            )
            return extract_image(resp)
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                wait = 30 * (attempt + 1)  # 30s, 60s, 90s
                time.sleep(wait)
                continue
            raise


def gen_chat_section(client, section_name, panels_data, callback=None):
    """Generate panels in a section using chat for visual memory."""
    results = {}
    try:
        chat = client.chats.create(model=get_active_model())
        # Prime with world rules
        try:
            chat.send_message(
                f"You are generating a cinematic documentary storyboard. "
                f"Section: {section_name}. {get_world_anchor()} "
                f"Maintain absolute visual consistency across all images."
            )
        except:
            pass

        for pd in panels_data:
            if pd.get("stop"):
                break
            pid = pd["id"]
            out = Path(pd["output"])

            if out.exists():
                results[pid] = "skip"
                if callback: callback("skip", pid)
                continue

            if callback: callback("generating", pid, pd.get("info", ""))

            contents = []
            for rp in pd.get("refs", []):
                if Path(rp).exists():
                    contents.append(Image.open(rp))
            contents.append(pd["prompt"])

            try:
                resp = chat.send_message(contents)
                img = extract_image(resp)
                if img:
                    out.write_bytes(img)
                    results[pid] = "ok"
                    if callback: callback("ok", pid)
                else:
                    results[pid] = "warn"
                    if callback: callback("warn", pid, "No image returned")
            except Exception as e:
                # Auto-retry on 429 before fallback
                if "429" in str(e):
                    if callback: callback("log", f"Rate limited on {pid}, waiting 45s...", "warn")
                    time.sleep(45)
                    try:
                        resp = chat.send_message(contents)
                        img = extract_image(resp)
                        if img:
                            out.write_bytes(img)
                            results[pid] = "ok"
                            if callback: callback("ok", pid)
                            time.sleep(4)
                            continue
                    except:
                        pass
                # Fallback to single shot (has its own retry)
                try:
                    img = gen_single(client, pd["prompt"], pd.get("refs"))
                    if img:
                        out.write_bytes(img)
                        results[pid] = "ok"
                        if callback: callback("ok", pid)
                    else:
                        results[pid] = "warn"
                        if callback: callback("warn", pid, "No image (fallback)")
                except Exception as e2:
                    results[pid] = "fail"
                    if callback: callback("fail", pid, str(e2)[:80])

            time.sleep(4)

    except Exception as e:
        # Chat creation failed — fallback all panels to single shot
        if callback: callback("log", f"Chat failed for {section_name}, using single-shot", "warn")
        for pd in panels_data:
            if pd.get("stop"): break
            pid = pd["id"]
            out = Path(pd["output"])
            if out.exists(): continue
            if callback: callback("generating", pid, pd.get("info", ""))
            try:
                img = gen_single(client, pd["prompt"], pd.get("refs"))
                if img:
                    out.write_bytes(img)
                    results[pid] = "ok"
                    if callback: callback("ok", pid)
                else:
                    results[pid] = "warn"
            except Exception as e2:
                results[pid] = "fail"
                if callback: callback("fail", pid, str(e2)[:80])
            time.sleep(4)

    return results


# ═══════════════════════════════════════════════════════════
# L5: POST-PROCESSING
# ═══════════════════════════════════════════════════════════
def post_process(img_path, out_path=None):
    g = get_grade_params()
    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    arr = np.array(img, dtype=np.float32)

    # Desaturate
    if g["desat"] > 0:
        gray = np.mean(arr, axis=2, keepdims=True)
        arr = arr * (1 - g["desat"]) + gray * g["desat"]

    # Teal shadows, warm highlights
    lum = np.mean(arr, axis=2, keepdims=True) / 255.0
    shadow = np.clip(1.0 - lum * 2, 0, 1)
    arr[:,:,0] += shadow[:,:,0] * g["teal_r"]
    arr[:,:,1] += shadow[:,:,0] * g["teal_g"]
    arr[:,:,2] += shadow[:,:,0] * g["teal_b"]
    high = np.clip(lum * 2 - 1, 0, 1)
    arr[:,:,0] += high[:,:,0] * g["warm_r"]
    arr[:,:,1] += high[:,:,0] * g["warm_g"]
    arr[:,:,2] += high[:,:,0] * g["warm_b"]

    # Contrast
    arr = (arr - 128) * g["contrast"] + 128
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)

    # Vignette
    if g["vignette"] > 0:
        vg = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(vg)
        cx, cy = w // 2, h // 2
        mr = int((w**2 + h**2)**0.5 / 2)
        for i in range(mr, 0, -1):
            draw.ellipse([cx-i, cy-i, cx+i, cy+i], fill=int(255 * (i/mr)**0.5))
        vg_arr = np.array(vg, dtype=np.float32) / 255.0
        strength = (1 - g["vignette"]) + vg_arr * g["vignette"]
        img_arr = np.array(img, dtype=np.float32)
        for c in range(3):
            img_arr[:,:,c] *= strength
        img = Image.fromarray(np.clip(img_arr, 0, 255).astype(np.uint8))

    # Film grain
    if g["grain"] > 0:
        grain = np.random.normal(0, g["grain"], (h, w)).astype(np.float32)
        img_arr = np.array(img, dtype=np.float32)
        for c in range(3):
            img_arr[:,:,c] += grain
        img = Image.fromarray(np.clip(img_arr, 0, 255).astype(np.uint8))

    img.save(out_path or img_path, quality=95)


# ═══════════════════════════════════════════════════════════
# L6: MASTER SHOTS — Hero render per location
# ═══════════════════════════════════════════════════════════
MASTER_SHOT_DETAILS = {
    "vault_interior": "MASTER SHOT — HERO RENDER. Interior of massive underground bank vault in Antwerp Diamond Centre. Rows of numbered metal safe deposit boxes lining concrete walls floor to ceiling. Single dramatic overhead spotlight creating cone of light in center. Polished concrete floor reflecting light. Heavy industrial architecture, reinforced concrete pillars. Cold, sterile, imposing. Camera: wide symmetrical shot down center aisle. 16:9. No people.",
    "vault_door": "MASTER SHOT — HERO RENDER. Massive circular steel bank vault door, 2 meters diameter, set in thick reinforced concrete wall. Complex locking mechanism with multiple bolt rods visible. Single overhead light creating dramatic rim light on metal edges. Underground corridor stretching behind. Camera: straight-on medium shot. 16:9. No people.",
    "corridor": "MASTER SHOT — HERO RENDER. Dimly lit basement corridor of the Antwerp Diamond Centre. Concrete walls, industrial pipes running along ceiling. Fluorescent tube lights casting harsh greenish pools of light with deep shadows between. Metal handrail along one wall. Emergency exit sign glowing at far end. Institutional, claustrophobic. Camera: long perspective shot down corridor. 16:9. No people.",
    "office": "MASTER SHOT — HERO RENDER. Small rented office inside the Antwerp Diamond Centre building. Wooden desk with brass desk lamp casting warm pool of light. Single window showing overcast Belgian sky. Simple chair, empty shelves, dark wood door. Modest but clean 2000s European office. Camera: medium wide from doorway looking in. 16:9. No people.",
    "exterior": "MASTER SHOT — HERO RENDER. The Antwerp Diamond Centre building exterior. Imposing early 1900s Belgian stone architecture, ornate facade, heavy glass entrance doors. Hoveniersstraat street level. Overcast sky, wet cobblestones. Grand, institutional, fortress-like. Camera: dramatic low angle looking up at facade. 16:9. No people.",
    "diamond_district": "MASTER SHOT — HERO RENDER. Antwerp Diamond District at night. Narrow cobblestone street with jewelry shop windows casting warm golden light. Wet pavement reflecting lamplight. Shuttered storefronts, security cameras on poles. Deserted, atmospheric. Camera: wide establishing shot down the street. 16:9. No people.",
    "garage": "MASTER SHOT — HERO RENDER. Underground parking garage beneath the Diamond Centre. Concrete ramp descending into darkness. Yellow sodium vapor lights casting amber glow. Low concrete ceiling, painted markings on floor. Cold, industrial, nighttime. Camera: looking down the ramp from street level. 16:9. No people.",
    "apartment": "MASTER SHOT — HERO RENDER. Notarbartolo's rented Antwerp apartment. Sparse European flat. Simple wooden table center frame under single warm pendant light. Dark walls, drawn curtains. Minimal furniture — functional, temporary, anonymous. Night time. Camera: wide shot from corner of room. 16:9. No people.",
    "warehouse": "MASTER SHOT — HERO RENDER. Large abandoned warehouse outside Antwerp. Crude but functional replica vault door and antechamber constructed from steel plates and concrete blocks. Construction lights on stands illuminating the setup. Dark cavernous warehouse space beyond. Camera: wide reveal shot. 16:9. No people.",
    "workshop": "MASTER SHOT — HERO RENDER. Dimly lit Italian mechanic's workshop. Heavy workbench with scattered precision tools, lockpicks, metal files. Single overhead bulb creating harsh shadows. Metalworking vise bolted to bench edge. Shelves with parts and supplies. Gritty, industrial. Camera: medium wide from doorway. 16:9. No people.",
    "vancamp_property": "MASTER SHOT — HERO RENDER. Wooded roadside area near E19 motorway, 40km south of Antwerp. Bare winter trees, dead leaves on muddy ground. Highway visible through trees in background. Cold February morning light. Quiet, isolated, forensic atmosphere. Camera: wide establishing shot from path. 16:9. No people.",
    "highway": "MASTER SHOT — HERO RENDER. E19 motorway between Antwerp and Brussels at night. Two-lane highway stretching into darkness. Dense forest on both sides. Wet asphalt reflecting distant car lights. Road markings visible. Overcast winter night. Camera: center of road looking ahead. 16:9. No people.",
    "crime_scene": "MASTER SHOT — HERO RENDER. Muddy woodland clearing cordoned with police tape. Evidence markers placed on ground next to scattered garbage bags. Officers in dark uniforms visible at perimeter. Overcast sky. Forensic, methodical atmosphere. Camera: wide shot from tape line. 16:9. No people in foreground.",
    "prison": "MASTER SHOT — HERO RENDER. Stark Belgian prison interview room. Metal table with two chairs. Single harsh overhead light creating cone on table surface. Concrete walls, small barred window high up. Institutional, cold, confined. Camera: corner wide shot. 16:9. No people.",
    "factory_district": "MASTER SHOT — HERO RENDER. Industrial district of Turin, Italy at dusk. Massive Fiat factory buildings with smokestacks silhouetted against orange sky. Chain-link fencing, puddles reflecting factory lights. Gritty working-class atmosphere. Camera: wide panoramic. 16:9. No people.",
    "italian_rural": "MASTER SHOT — HERO RENDER. Modest rural property outside Turin, Italy at dusk. Small warehouse building with delivery truck parked outside. Rolling Piedmont hills in background. Warm amber light from single window. Peaceful but melancholy atmosphere. Camera: wide establishing shot. 16:9. No people.",
    "courtroom": "MASTER SHOT — HERO RENDER. Belgian courtroom interior. Elevated wooden judge's bench center frame, witness stand to the left. Dark wood paneling on walls. Institutional fluorescent and natural window light. Gallery seating with wooden pews. Formal, imposing, justice. Camera: wide symmetrical from gallery perspective. 16:9. No people.",
    "police_station": "MASTER SHOT — HERO RENDER. Belgian police station interrogation room. Metal table with two chairs facing each other. One-way mirror on wall. Single harsh overhead light creating cone of light on table. Concrete walls, institutional cold. Camera: corner wide shot. 16:9. No people.",
    "aerial_city": "MASTER SHOT — HERO RENDER. Dramatic aerial establishing shot of Antwerp at dusk. Diamond district buildings below, Cathedral of Our Lady spire visible. Scheldt river in background. Overcast sky with golden light breaking through. Cinematic drone perspective. Camera: high angle sweeping view. 16:9. No people.",
}

def get_master_shot_prompt(eid):
    """Build master shot prompt using active preset."""
    detail = MASTER_SHOT_DETAILS.get(eid, "")
    if not detail:
        return get_env_prompt(eid)
    return get_world_anchor() + get_primary_style() + detail


# ═══════════════════════════════════════════════════════════
# L7: VISUAL MEMORY BANK — Track best renders across sections
# ═══════════════════════════════════════════════════════════
class VisualMemoryBank:
    """
    Tracks the latest successful render for each character and environment.
    When @leo is rendered in S1, that render becomes a ref for @leo in S5.
    When vault is rendered in S1, that render anchors vault in S7.
    ABC stays ABC throughout the entire video.
    """
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.bank_file = self.output_dir / "memory_bank.json"
        self.char_latest = {}   # cid → path to latest successful scene render
        self.env_latest = {}    # eid → path to latest successful scene render
        self.load()

    def load(self):
        if self.bank_file.exists():
            try:
                data = json.loads(self.bank_file.read_text())
                self.char_latest = data.get("char_latest", {})
                self.env_latest = data.get("env_latest", {})
                # Verify paths still exist
                self.char_latest = {k: v for k, v in self.char_latest.items() if Path(v).exists()}
                self.env_latest = {k: v for k, v in self.env_latest.items() if Path(v).exists()}
            except:
                pass

    def save(self):
        self.bank_file.write_text(json.dumps({
            "char_latest": self.char_latest,
            "env_latest": self.env_latest,
        }, indent=2))

    def update_char(self, cid, scene_path):
        """After successfully rendering a scene with @cid, save as latest ref."""
        if Path(scene_path).exists():
            self.char_latest[cid] = str(scene_path)
            self.save()

    def update_env(self, eid, scene_path):
        """After successfully rendering a scene in this env, save as latest ref."""
        if Path(scene_path).exists():
            self.env_latest[eid] = str(scene_path)
            self.save()

    def get_char_refs(self, cid, portrait_refs):
        """
        Get best refs for a character:
        1. Original portraits (front + 3/4) — always included
        2. Latest successful scene render — if available, adds context
        Returns list of paths, max 3 images.
        """
        refs = list(portrait_refs)  # copy
        if cid in self.char_latest:
            latest = self.char_latest[cid]
            if latest not in refs:
                refs.append(latest)
        return refs[:3]  # max 3: front + 3/4 + latest scene

    def get_env_ref(self, eid, master_shot_path, env_ref_path=None):
        """
        Get best ref for an environment:
        1. Master shot (hero render) — primary anchor
        2. Latest successful scene render in that env — secondary anchor
        Returns list of paths, max 2 images.
        """
        refs = []
        if master_shot_path and Path(master_shot_path).exists():
            refs.append(master_shot_path)
        elif env_ref_path and Path(env_ref_path).exists():
            refs.append(env_ref_path)
        if eid in self.env_latest:
            latest = self.env_latest[eid]
            if latest not in refs:
                refs.append(latest)
        return refs[:2]  # max 2: master + latest scene


# ═══════════════════════════════════════════════════════════
# GUI
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
# PREMIUM GUI — CustomTkinter
# ═══════════════════════════════════════════════════════════
