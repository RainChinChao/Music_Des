from __future__ import annotations

from typing import Any

STYLES = [
    "Pop", "Funk", "Punk", "Indie", "Classical", "Rock", "Hard rock",
    "Metal", "Heavy metal", "Instrumental", "Orchestral", "City pop",
    "Electronic EDM",
]

INSTRUMENTS = [
    "Piano", "Electric Piano", "Drums", "Bass", "Electric Guitar",
    "Acoustic Guitar", "Vocal", "Violin", "Viola", "Cello", "Contrabass",
    "Harp", "Studio Strings", "String Ensemble", "Choir", "Trumpet",
    "Trombone", "French Horn", "Tuba", "Soprano Sax", "Alto Sax",
    "Tenor Sax", "Flute", "Piccolo", "Clarinet", "Oboe", "Bassoon",
    "Organ", "Accordion", "Harmonica", "Marimba", "Vibraphone",
    "Xylophone", "Celesta", "Synth Lead", "Synth Pad", "Synth Bass",
    "Sampler", "Alchemy", "Vintage Mellotron",
]

PRESETS = [
    "Default", "Solo Violin", "Violin 1 Section", "Violin 2 Section",
    "Full Strings", "Disco Strings", "Violins Solo", "String Ensemble",
    "Hybrid Strings", "Cinematic Violins", "Textured Bows", "1 Violins",
    "3 Violins",
]

ARTICULATIONS = ["Legato", "Staccato", "Spiccato", "Pizzicato", "Tremolo"]
AUDIO_FX = ["Channel EQ", "Space Designer", "Sample Delay"]

REQUIREMENT_TYPES = ["lyrics", "scene", "feeling"]

MUSIC_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "tempo_bpm", "time_signature", "ticks_per_beat", "tracks"],
    "properties": {
        "title": {"type": "string"},
        "tempo_bpm": {"type": "integer", "minimum": 20, "maximum": 400},
        "time_signature": {
            "type": "array", "minItems": 2, "maxItems": 2,
            # OpenAI Structured Outputs requires `items` on every array and
            # does not accept tuple-only `prefixItems` here. The denominator's
            # power-of-two constraint is enforced again by generate_midi().
            "items": {"type": "integer", "minimum": 1, "maximum": 32},
        },
        "ticks_per_beat": {"type": "integer", "minimum": 24, "maximum": 9600},
        "tracks": {
            "type": "array", "minItems": 1, "maxItems": 16,
            "items": {"$ref": "#/$defs/track"},
        },
    },
    "$defs": {
        "eq": {
            "type": "object", "additionalProperties": False,
            "required": ["brightness", "resonance", "low", "mid", "high"],
            "properties": {k: {"type": "integer", "minimum": 0, "maximum": 127}
                           for k in ["brightness", "resonance", "low", "mid", "high"]},
        },
        "settings": {
            "type": "object", "additionalProperties": False,
            "required": ["volume", "velocity", "sustain", "mute", "pan", "eq"],
            "properties": {
                "volume": {"type": "integer", "minimum": 0, "maximum": 127},
                "velocity": {"type": "integer", "minimum": 1, "maximum": 127},
                "sustain": {"type": "boolean"}, "mute": {"type": "boolean"},
                "pan": {"type": "integer", "minimum": 0, "maximum": 127},
                "eq": {"$ref": "#/$defs/eq"},
            },
        },
        "note": {
            "type": "object", "additionalProperties": False,
            "required": ["pitch", "start", "duration", "velocity"],
            "properties": {
                "pitch": {"anyOf": [{"type": "integer", "minimum": 0, "maximum": 127},
                                     {"type": "string"}]},
                "start": {"type": "number", "minimum": 0},
                "duration": {"type": "number", "exclusiveMinimum": 0},
                "velocity": {"type": "integer", "minimum": 1, "maximum": 127},
            },
        },
        "automation": {
            "type": "object", "additionalProperties": False,
            "required": ["type", "beat", "value"],
            "properties": {
                "type": {"type": "string", "enum": ["volume", "pan", "sustain", "mute",
                    "eq_brightness", "eq_resonance", "eq_low", "eq_mid", "eq_high"]},
                "beat": {"type": "number", "minimum": 0},
                "value": {"anyOf": [{"type": "integer", "minimum": 0, "maximum": 127},
                                    {"type": "boolean"}]},
            },
        },
        "track": {
            "type": "object", "additionalProperties": False,
            "required": ["name", "instrument", "preset", "articulation",
                         "audio_fx", "settings", "notes", "automation"],
            "properties": {
                "name": {"type": "string"},
                "instrument": {"type": "string", "enum": INSTRUMENTS},
                "preset": {"type": "string", "enum": PRESETS},
                "articulation": {"type": "string", "enum": ARTICULATIONS},
                "audio_fx": {
                    "type": "array", "maxItems": 3,
                    "items": {
                        "type": "object", "additionalProperties": False,
                        "required": ["type", "enabled", "amount"],
                        "properties": {
                            "type": {"type": "string", "enum": AUDIO_FX},
                            "enabled": {"type": "boolean"},
                            "amount": {"type": "integer", "minimum": 0, "maximum": 127},
                        },
                    },
                },
                "settings": {"$ref": "#/$defs/settings"},
                "notes": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/note"}},
                "automation": {"type": "array", "items": {"$ref": "#/$defs/automation"}},
            },
        },
    },
}
