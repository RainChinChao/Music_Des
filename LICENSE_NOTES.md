# Model and Asset Licence Notes

The default local model is `qwen2.5:7b-instruct`. Qwen's official Qwen2.5
release notice states that its open-source models except the 3B and 72B
variants use Apache 2.0:
https://qwenlm.github.io/blog/qwen2.5/

The optional `mistral:7b-instruct` model is based on Mistral 7B. Mistral's
official release states that Mistral 7B uses Apache 2.0:
https://mistral.ai/news/announcing-mistral-7b/

Apache 2.0 is generally permissive for business use, but required notices and
other obligations still apply. Do not assume that similarly named, newer,
fine-tuned, hosted, 3B, 72B or third-party model variants have the same terms.
Review the exact model card and licence before production deployment.

The automatic installer downloads `MuseScore_General.sf3` and its accompanying
MIT licence from the official MuseScore mirror into `~/Music/SoundFonts`.
Preserve `MuseScore_General_LICENSE.txt` and include the required notice in
associated product/audio documentation when distributing it or rendered audio.
Other SoundFonts remain separate assets: confirm that any replacement permits
the intended commercial use and redistribution.

Online GPT, Gemini and Claude use is governed by their providers' current
service terms rather than an open-source model licence. This file is technical
guidance and is not legal advice.

Google AI Studio is an explicit Gemini Developer API option. Free-tier quotas
and model eligibility can change, and Google's current pricing documentation
states that free-tier content may be used to improve its products. Review the
current Google terms and use an appropriate paid/confidential tier for sensitive
commercial data.

See `MODEL_POLICY.md` for the conservative commercial policy covering Qwen,
ACE-Step, NotaGen, MIDI-LLM, reference uploads, provenance and originality
review. A permissive code licence alone is not a guarantee about checkpoints,
training data, outputs or third-party content.
