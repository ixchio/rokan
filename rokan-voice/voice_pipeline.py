"""
Rokan Voice Pipeline
Wake word → Whisper.cpp STT → LLM → Piper TTS
"""

import os
import subprocess
import tempfile
import wave
from typing import Callable, Optional
from dataclasses import dataclass
from pathlib import Path

# Optional imports
try:
    import openwakeword
    from openwakeword.model import Model
    HAS_WAKEWORD = True
except ImportError:
    HAS_WAKEWORD = False

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False


@dataclass
class VoiceConfig:
    """Voice pipeline configuration"""
    wake_word_model: str = "hey_rokan"
    whisper_model: str = "~/.rokan/models/whisper-base.bin"
    piper_model: str = "~/.rokan/models/piper/voice.onnx"
    sample_rate: int = 16000
    chunk_size: int = 1024


class VoicePipeline:
    """
    Local voice pipeline for Rokan
    Fully offline voice interaction
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.voice_config = VoiceConfig()
        
        # Paths
        self.whisper_path = os.path.expanduser(
            self.config.get("stt", {}).get("model_path", self.voice_config.whisper_model)
        )
        self.piper_path = os.path.expanduser(
            self.config.get("tts", {}).get("model_path", self.voice_config.piper_model)
        )
        
        # State
        self.is_listening = False
        self.wake_word_detected = False
        self.on_wake_word: Optional[Callable] = None
        self.on_speech: Optional[Callable] = None
        
        # Audio
        self.audio = None
        if HAS_PYAUDIO:
            self.audio = pyaudio.PyAudio()
        
        # Wake word model
        self.wake_model = None
        if HAS_WAKEWORD:
            try:
                self.wake_model = Model(wakeword_models=[self.voice_config.wake_word_model])
            except:
                pass
    
    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe audio file using Whisper.cpp
        
        Args:
            audio_path: Path to audio file (wav)
        
        Returns:
            Transcribed text
        """
        if not os.path.exists(self.whisper_path):
            return "Error: Whisper model not found. Run setup first."
        
        try:
            result = subprocess.run(
                ["whisper.cpp", "-m", self.whisper_path, "-f", audio_path, "--no-timestamps"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Transcription error: {result.stderr}"
        
        except subprocess.TimeoutExpired:
            return "Transcription timed out"
        except Exception as e:
            return f"Transcription failed: {e}"
    
    def speak(self, text: str) -> bool:
        """
        Synthesize speech using Piper
        
        Args:
            text: Text to speak
        
        Returns:
            True if successful
        """
        if not os.path.exists(self.piper_path):
            print("Error: Piper model not found. Run setup first.")
            return False
        
        try:
            # Create temp file for audio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                audio_path = f.name
            
            # Generate speech
            piper_cmd = [
                "piper",
                "--model", self.piper_path,
                "--output_file", audio_path
            ]
            
            result = subprocess.run(
                piper_cmd,
                input=text,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"Piper error: {result.stderr}")
                return False
            
            # Play audio
            self._play_audio(audio_path)
            
            # Cleanup
            os.unlink(audio_path)
            
            return True
        
        except Exception as e:
            print(f"Speech synthesis failed: {e}")
            return False
    
    def _play_audio(self, audio_path: str):
        """Play audio file"""
        try:
            # Try aplay (ALSA)
            subprocess.run(
                ["aplay", "-q", audio_path],
                check=True,
                timeout=60
            )
        except:
            try:
                # Fallback to paplay (PulseAudio)
                subprocess.run(
                    ["paplay", audio_path],
                    check=True,
                    timeout=60
                )
            except:
                pass
    
    def record_audio(self, duration: int = 5, output_path: str = None) -> str:
        """
        Record audio from microphone
        
        Args:
            duration: Recording duration in seconds
            output_path: Output file path (auto if None)
        
        Returns:
            Path to recorded file
        """
        if not HAS_PYAUDIO:
            return None
        
        if output_path is None:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                output_path = f.name
        
        # Open stream
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.voice_config.sample_rate,
            input=True,
            frames_per_buffer=self.voice_config.chunk_size
        )
        
        frames = []
        for _ in range(0, int(self.voice_config.sample_rate / self.voice_config.chunk_size * duration)):
            data = stream.read(self.voice_config.chunk_size)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        
        # Save wav
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.voice_config.sample_rate)
            wf.writeframes(b''.join(frames))
        
        return output_path
    
    def start_listening(self, on_wake: Callable = None, on_speech: Callable = None):
        """
        Start wake word detection and listening
        
        Args:
            on_wake: Callback when wake word detected
            on_speech: Callback with transcribed speech
        """
        self.on_wake_word = on_wake
        self.on_speech = on_speech
        self.is_listening = True
        
        print("Voice pipeline started. Say 'Hey Rokan' to activate.")
        
        # Simple implementation - in production, use continuous stream
        # with VAD (Voice Activity Detection)
        while self.is_listening:
            try:
                # Record short chunk
                audio_path = self.record_audio(duration=3)
                
                # Transcribe
                text = self.transcribe(audio_path)
                
                # Check for wake word
                if "rokan" in text.lower() or "hey" in text.lower():
                    self.wake_word_detected = True
                    
                    if self.on_wake_word:
                        self.on_wake_word()
                    
                    # Speak acknowledgment
                    self.speak("I'm listening.")
                    
                    # Record command
                    command_audio = self.record_audio(duration=5)
                    command = self.transcribe(command_audio)
                    
                    if self.on_speech:
                        self.on_speech(command)
                
                # Cleanup
                os.unlink(audio_path)
                
            except Exception as e:
                print(f"Listening error: {e}")
    
    def stop_listening(self):
        """Stop voice pipeline"""
        self.is_listening = False
        print("Voice pipeline stopped.")


# OpenClaw skill interface
class RokanVoiceSkill:
    """OpenClaw skill interface for rokan-voice"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.pipeline = VoicePipeline(config)
    
    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file"""
        return self.pipeline.transcribe(audio_path)
    
    def speak(self, text: str) -> str:
        """Speak text"""
        success = self.pipeline.speak(text)
        return "Spoke." if success else "Failed to speak."
    
    def record(self, duration: int = 5) -> str:
        """Record audio"""
        path = self.pipeline.record_audio(duration)
        return f"Recorded to: {path}"
    
    def enable(self) -> str:
        """Enable voice mode"""
        # This would integrate with OpenClaw's voice system
        return "Voice mode enabled. Say 'Hey Rokan' to activate."
    
    def disable(self) -> str:
        """Disable voice mode"""
        self.pipeline.stop_listening()
        return "Voice mode disabled."


# Export for OpenClaw
skill = RokanVoiceSkill
