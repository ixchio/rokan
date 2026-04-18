# rokan-voice

**Rokan's Local Voice Pipeline** — Wake word → Whisper.cpp STT → LLM → Piper TTS. Fully offline, sub-200ms latency.

## Description

Complete voice interface for Rokan using only local, open-source components. No cloud APIs for voice processing — everything runs on your Linux machine.

## Pipeline

```
[Audio Input] → [openWakeWord] → [Whisper.cpp] → [LLM] → [Piper TTS] → [Audio Output]
     ↑               ↑                  ↑           ↑           ↑              ↓
  Mic stream    "Hey Rokan"      Transcribe    Think      Synthesize    Speak
```

## When to Use

- User enables voice mode or says wake word
- Hands-free operation needed
- Quick voice commands while working
- Accessibility requirements

## Setup

```bash
# 1. Install system dependencies
sudo apt-get install portaudio19-dev libasound2-dev

# 2. Install Python dependencies
pip install openwakeword pyaudio webrtcvad numpy scipy

# 3. Install Whisper.cpp
# Option A: Pre-built
wget https://github.com/ggerganov/whisper.cpp/releases/download/v1.7.5/whisper-bin-x64.zip
unzip whisper-bin-x64.zip -d ~/.local/bin/

# Option B: Build from source
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp && make && cp main ~/.local/bin/whisper.cpp

# 4. Download Whisper model
mkdir -p ~/.rokan/models
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin -O ~/.rokan/models/whisper-base.bin

# 5. Install Piper TTS
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz
tar -xzf piper_amd64.tar.gz -C ~/.local/bin/

# 6. Download Piper voice model
mkdir -p ~/.rokan/models/piper
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx -O ~/.rokan/models/piper/voice.onnx
```

## Configuration

Add to `~/.openclaw/config.yaml`:

```yaml
skills:
  rokan-voice:
    enabled: true
    wake_word:
      enabled: true
      engine: openwakeword
      model: hey_rokan
      sensitivity: 0.5
    stt:
      engine: whisper.cpp
      model_path: ~/.rokan/models/whisper-base.bin
      language: en
      device: cpu  # or cuda
    tts:
      engine: piper
      model_path: ~/.rokan/models/piper/voice.onnx
      speed: 1.0
      volume: 0.8
    audio:
      sample_rate: 16000
      chunk_size: 1024
      vad_aggressiveness: 2
```

## Usage

### Wake Word Activation
```
[User]: "Hey Rokan"
[Rokan]: *wake sound* "I'm listening."
```

### Voice Command
```
[User]: "What's my system status?"
[Rokan]: "CPU at 23%, 16GB RAM available, 3 processes using high CPU."
```

### Disable Voice
```
User: "Rokan, disable voice mode"
→ Returns to text-only mode
```

## API

### `voice.start_listening()`
Start wake word detection and audio pipeline.

### `voice.stop_listening()`
Stop voice pipeline.

### `voice.transcribe(audio_path)`
Transcribe audio file to text using Whisper.cpp.

### `voice.speak(text)`
Synthesize and play text using Piper TTS.

### `voice.is_speaking()`
Check if TTS is currently playing.

## Performance

| Component | Latency | Hardware |
|-----------|---------|----------|
| Wake Word | ~50ms | CPU |
| STT (Whisper) | ~100ms | CPU |
| TTS (Piper) | ~30ms | CPU |
| **Total** | **~180ms** | **CPU-only** |

## Custom Wake Word

Train your own wake word:
```bash
# Using openWakeWord training
openwakeword train --model-name "hey_rokan" --samples ./wake_word_samples/
```

## Files

- `voice_pipeline.py` — Main orchestrator
- `wake.py` — Wake word detection
- `stt.py` — Whisper.cpp wrapper
- `tts.py` — Piper wrapper
- `audio_stream.py` — Audio I/O handling

## License

MIT — Part of Rokan Skill Pack for OpenClaw
