<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![Status: Beta](https://img.shields.io/badge/status-Beta-17b6a7)
[![CI](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertoTorino/bazzite-console/actions/workflows/ci.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

# Nexus TTS

Nexus TTS speaks an English text in a natural voice and saves the speech as an Ogg Vorbis, MP3, FLAC or WAV
file. Type or paste the text, choose one of 15 female voices, American or British, set a speed, and click Speak. The
first sentence plays while the app makes the next ones. The voices run on the machine itself, and nothing of your text leaves it. It is a
development app, so it runs from the checkout and has no releases. Start it from [Nexus Dashboard](../dash), or:

| | Linux |
|---|---|
| Open it | `dev/text/run.sh` |
| Menu entry and Desktop icon | `dev/text/install.sh` (`--no-desktop-shortcut`, `--uninstall`, `--uninstall --purge`) |

Nothing is copied: the entry starts the app of the checkout you installed it from.

The first time, click Set up the speech engine in the window. It downloads the speech engine and the voice model,
about 350 MB together, into `~/.local/share/nexus-text-to-speech/`. The setup needs [uv](https://docs.astral.sh/uv/)
(`brew install uv`), or a Python from 3.10 to 3.13 on the PATH.

How to use it: [Nexus TTS in the wiki](https://robertotorino.github.io/bazzite-console/development/dashboard/#nexus-tts).

## License

GPL-3.0-or-later, see [LICENSE](LICENSE). The speech engine's packages and the model are downloaded. They are not
part of this repository. [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) is MIT, and the
[Kokoro model](https://huggingface.co/hexgrad/Kokoro-82M) is Apache-2.0.
