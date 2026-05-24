<<<<<<< HEAD
# Vaani

Real-time multilingual live translation for one speaker and many listeners.

Vaani lets a speaker talk into a room and allows listeners to receive:

- live transcription
- translated text
- translated audio in their selected language

The project is built for Indian language use cases and currently supports:

- Hindi
- English
- Tamil
- Telugu
- Kannada
- Bengali
- Marathi
- Gujarati

## What It Does

The flow is simple:

1. A speaker creates a room.
2. Listeners join the room using the room code.
3. The speaker talks through the browser microphone.
4. The backend transcribes the speech, translates it, and generates translated audio.
5. Each listener receives the output in their chosen language.

## Use Cases

Vaani is useful anywhere one person needs to speak to a multilingual audience in real time.

- Live events where attendees prefer different Indian languages
- Classrooms and workshops with mixed-language participants
- Public announcements in offices, campuses, hospitals, or transport hubs
- Religious gatherings or community meetings
- Product demos, webinars, or onboarding sessions
- Accessibility support for listeners who want both text and translated audio

## How It Works

The backend pipeline is:

1. Browser captures microphone audio from the speaker
2. Audio is sent to the FastAPI backend over WebSocket
3. `faster-whisper` performs speech-to-text
4. `facebook/nllb-200-distilled-600M` performs translation
5. Sarvam TTS generates translated speech
6. Listeners receive translated text and audio in parallel

## Tech Stack

- Backend: FastAPI + Uvicorn
- Realtime transport: WebSockets
- Speech-to-text: `faster-whisper`
- Translation: `facebook/nllb-200-distilled-600M`
- Text-to-speech: Sarvam AI `bulbul:v3`
- Frontend: Vanilla HTML, CSS, and JavaScript
- Audio conversion: `ffmpeg`

## Project Structure

```text
live-translation/
├── backend/
│   ├── main.py
│   ├── room_manager.py
│   ├── stt_service.py
│   ├── translation_service.py
│   ├── tts_service.py
│   ├── requirements.txt
│   ├── .env.example
│   └── venv/
├── frontend/
│   ├── index.html
│   ├── speaker.html
│   └── listener.html
└── README.md
```

## Prerequisites

Before running the project, make sure you have:

- Python 3.10 or newer
- `ffmpeg` installed and available in your system `PATH`
- A Sarvam API key

## Installation

These are the setup steps for Windows PowerShell.

```powershell
cd D:\Mehul\live-translation\backend

python -m venv venv

venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
$env:KMP_DUPLICATE_LIB_OK="TRUE"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

After copying `.env.example` to `.env`, add your Sarvam API key inside the `.env` file.

Example:

```env
SARVAM_API_KEY=your_api_key_here
```

## Running the App

Once the backend is running, open:

```text
http://localhost:8000
```

## How To Use

### Speaker

1. Open the home page
2. Create a room
3. Copy the generated room code
4. Choose the speaker language
5. Start the microphone and speak

### Listener

1. Open the home page in another tab or device
2. Join using the room code
3. Select the preferred listening language
4. Enable audio playback in the browser if prompted
5. Receive translated text and translated audio live

## Example Demo Flow

1. Start the backend server
2. Open one browser tab as the speaker
3. Create a room
4. Open one or more listener tabs
5. Join the same room using the room code
6. Select different listener languages
7. Speak from the speaker tab
8. Observe live transcript, translated text, and translated audio on listener tabs

## Notes

- First startup can take longer because the local AI models may need to download
- Performance depends on your machine, especially for Whisper and translation inference
- Listener audio playback may require a user click because browsers restrict autoplay
- Better CPU or GPU hardware can improve latency significantly

## Future Improvements

- Lower-latency streaming audio
- Better queueing and chunk tuning
- More languages
- Persistent room state
- Authentication and room management
- Production deployment support

## License

This project is provided for assessment, experimentation, and learning.
=======
---
title: Live Translation
emoji: 🐨
colorFrom: red
colorTo: green
sdk: docker
pinned: false
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference
>>>>>>> a27a45c4e75b082d845efcc16ed663b86072ef51
