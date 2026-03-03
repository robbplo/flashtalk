# FlashTalk API

Tiny FastAPI service that generates and caches Latvian phrase audio as MP3 using ElevenLabs.

`GET /say?phrase=...` can be used directly in HTML media tags.

## Features

- Cache-first flow: return existing local MP3 if present.
- Generate-on-miss with ElevenLabs v3 model.
- Process-local single-flight locking for concurrent same-phrase requests.
- Service-oriented design using protocols for external dependencies.
- Structured logging with `DEBUG`, `INFO`, `WARNING`, and `ERROR`.
- Unit and API tests with pytest.

## Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- ElevenLabs API key + voice ID

## Setup

1. Copy env template:

```bash
cp .env.example .env
```

2. Fill values in `.env`:

- `ELEVENLABS_API_KEY`
- `ELEVENLABS_VOICE_ID`

3. Install dependencies:

```bash
uv sync
```

## Run

```bash
uv run uvicorn flashtalk_api.app:create_app --factory --reload
```

API will be available at `http://127.0.0.1:8000`.

## Endpoint

### `GET /say`

Query parameters:

- `phrase` (required): Latvian text to synthesize.

Responses:

- `200` + `audio/mpeg` on cache hit or successful generation.
- `400` JSON when `phrase` is blank/invalid.
- `502` JSON when ElevenLabs fails on an uncached phrase.

Example:

```bash
curl -sS "http://127.0.0.1:8000/say?phrase=Labdien"
```

HTML usage:

```html
<audio controls src="/say?phrase=Labdien"></audio>
```

## Configuration

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `ELEVENLABS_API_KEY` | Yes | - | ElevenLabs API key |
| `ELEVENLABS_VOICE_ID` | Yes | - | ElevenLabs voice ID |
| `ELEVENLABS_MODEL_ID` | No | `eleven_v3` | TTS model ID |
| `AUDIO_DIR` | No | `./data` | Local cache directory |
| `LOG_LEVEL` | No | `INFO` | Application log level |

Audio output format is fixed to MP3 (`mp3_44100_128`).

## Development

Run tests:

```bash
uv run pytest
```

Lint:

```bash
uv run ruff check .
```

Type check:

```bash
uv run mypy src
```
