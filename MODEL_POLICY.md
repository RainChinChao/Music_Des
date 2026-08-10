# Commercial Model Policy

No generative model can be described as legally risk-free. Before a production
release, verify the exact model/checkpoint licence, required notices, provider
terms, training-data claims, generated-output similarity, user-provided lyrics
and reference-file permissions with qualified legal counsel.

## Default

`qwen2.5:7b-instruct` is the default local structured-JSON engine. The official
Qwen2.5 release states that the 7B variant uses Apache License 2.0. Preserve its
licence and NOTICE obligations and verify the exact Ollama model manifest used
in the released product.

## Optional music-specific reference engines

- ACE-Step: official source is Apache-2.0. It produces audio rather than this
  system's editable composition JSON, so its output is accepted only as a
  reference asset. Review the exact checkpoint terms and generated similarity.
- NotaGen: its official source repository is MIT-licensed and is primarily a
  classical symbolic-music system. Verify that the exact checkpoint and all
  dependencies/datasets carry compatible terms before bundling it.
- MIDI-LLM: directly generates MIDI, but the official checkpoint uses the
  Llama 3.2 Community License rather than Apache/MIT. It is not enabled or
  bundled by default. If integrated, comply with all Llama attribution,
  redistribution, acceptable-use and commercial-scale provisions, and review
  the MIDI training-data implications.

## Product controls

- Record model provider, exact model name/version and licence alongside releases.
- Keep all required third-party licence and NOTICE files.
- Do not invite prompts that imitate a living artist or reproduce a protected song.
- Require users to confirm permission for uploaded lyrics, MIDI, scores and audio.
- Run similarity/originality review before commercial publication.
- Do not train on user feedback/reference assets without explicit contractual
  permission. Local retrieval for that same user's generations should be
  disclosed and controllable.

## Training-provider routing

The separate runtime trainer may use Ollama, Google AI Studio/Gemini, OpenAI,
Claude, DeepSeek or OpenRouter. Selecting a training provider does not change
the music-generation provider. DeepSeek and OpenRouter are API services rather
than a single licence grant; for OpenRouter, the terms and licence of the exact
routed `provider/model` also apply. Do not assume a free route is automatically
approved for confidential or commercial data.
