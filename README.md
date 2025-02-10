# Whisper Shark 🦈

A minimal, floating speech-to-text transcription tool powered by OpenAI's Whisper model.

## Description

Whisper Shark is a lightweight, always-on-top application that converts speech to text in real-time. It features a modern, minimal interface that stays out of your way while providing quick access to transcription services. Perfect for quick dictation into any text field or document.

## Features

- **Minimal Interface**: Compact, draggable window that stays on top of other applications
- **Real-time Transcription**: Powered by OpenAI's Whisper base model
- **Universal Clipboard Integration**: Works with any application that accepts text input
- **Modern Dark Theme**: Easy on the eyes with a professional look
- **One-Click Operations**: Simple recording and copying controls

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/whisper-shark.git
cd whisper-shark
```

2. Install system dependencies (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install python3-tk portaudio19-dev python3-dev ffmpeg
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
python app.py
```

2. The interface will appear in the top-right corner of your screen with three controls:
   - ⏺ (Record): Click to start recording
   - ⏹ (Stop): Click to stop recording and process speech
   - ⎘ (Copy): Click to copy the last transcription again

3. Workflow:
   - Click the record button (⏺) and speak
   - Click stop (⏹) when finished
   - The text is automatically copied to your clipboard
   - Paste (Ctrl+V/Cmd+V) anywhere you need the text
   - Use the copy button (⎘) if you need to copy the text again

4. Interface Elements:
   - Title bar: Drag to move the window
   - Status label: Shows current state and any error messages
   - ✕ (Close): Click to exit the application

## Technical Details

- Built with Python and Tkinter
- Uses OpenAI's Whisper base model for speech recognition
- Supports multiple audio input devices
- Thread-safe recording and processing
- Clipboard integration for universal compatibility

## Requirements

- Python 3.9+
- FFmpeg
- PortAudio
- Python packages (see `requirements.txt`):
  - openai-whisper
  - numpy
  - sounddevice
  - soundfile

## Troubleshooting

1. **No audio input detected**:
   - Check your microphone permissions
   - Verify your microphone is selected as the default input device

2. **Interface not visible**:
   - The window starts in the top-right corner
   - Look for a small dark window with "Whisper Shark" title

3. **Error messages**:
   - Check the terminal output for detailed error logs
   - Verify all dependencies are installed correctly

## License

[Add your chosen license here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.