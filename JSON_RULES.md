# JSON Rules

Root fields are `title`,
`tempo_bpm` (20-400), `time_signature`, `ticks_per_beat` (24-9600), and
`tracks`. Supported instruments are Piano, Electric Piano, Drums, Bass,
Electric Guitar, Acoustic Guitar, Vocal, Studio Strings, Sampler, Alchemy and
Vintage Mellotron.

Every AI-generated track contains `preset`, `articulation` and `audio_fx`.
Presets are: Default, Solo Violin, Violin 1 Section, Violin 2 Section, Full
Strings, Disco Strings, Violins Solo, String Ensemble, Hybrid Strings,
Cinematic Violins, Textured Bows, 1 Violins and 3 Violins.

Articulations are Legato, Staccato, Spiccato, Pizzicato and Tremolo. `audio_fx`
entries contain `type`, `enabled` and `amount` (0-127). Types are Channel EQ,
Space Designer and Sample Delay. Logic-specific names are preserved as MIDI
text metadata. General MIDI approximates Pizzicato/Tremolo programs and Space
Designer with reverb CC91; exact patches/effects require Logic Pro.

Each AI-generated note contains `pitch`, `start` in beats, `duration` in beats
and `velocity`. Each track supports initial `volume`, `velocity`, `sustain`,
`mute`, `pan` and EQ. Automation types are `volume`, `pan`, `sustain`, `mute`,
`eq_brightness`, `eq_resonance`, `eq_low`, `eq_mid` and `eq_high`.

AI-generated JSON is constrained by the stricter schema in
`src/deterministic_midi/music_schema.py`, then passed to the deterministic
generator for final validation. Older hand-written JSON can omit new production
metadata; deterministic defaults are `Default`, `Legato` and an empty FX list.
