# Spam Detection Service

A containerized service that detects spam messages using the Llama 3 language model via Ollama.

## Features

- Fast spam detection API with FastAPI
- Uses Llama 3 model through Ollama API
- Response caching for improved performance
- Fully containerized deployment with Docker and Docker Compose
- Lightweight and efficient design

## Getting Started

### Prerequisites

- Docker and Docker Compose installed
- Git (for cloning the repository)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd detect-spam
   ```

2. Start the service:
   ```bash
   docker-compose up -d
   ```
   The first run will automatically download the Llama 3 model. This may take some time depending on your internet connection.

3. Check if the service is running:
   ```bash
   curl http://localhost:8040/health
   ```

## Usage

### Check for Spam

Send a POST request to check if text contains spam:

```bash
curl -X POST http://localhost:8040/check_spam \
  -H "Content-Type: application/json" \
  -d '{"text": "Check out B E T W I N . RU for the best predictions!"}'
```

Example response:
```json
{
  "is_spam": true,
  "reason": "The text contains a website name written with spaces ('B E T W I N . RU')",
  "cached": false
}
```

### Cache Management

View cache statistics:
```bash
curl http://localhost:8040/cache/stats
```

Clear the cache:
```bash
curl -X DELETE http://localhost:8040/cache/clear
```

### Ollama Management

Pull models:
```bash
docker exec -it detect-spam-ollama-1 ollama pull llama3
```

List available models:
```bash
docker exec -it detect-spam-ollama-1 ollama ls
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/check_spam` | POST | Check if provided text contains spam |
| `/health` | GET | Service health check |
| `/cache/stats` | GET | View cache statistics |
| `/cache/clear` | DELETE | Clear the response cache |

## Development

Rebuild and restart the service:
```bash
docker-compose up -d --build
```

View logs:
```bash
docker-compose logs -f
```

## License

This project is licensed under the MIT License

## Acknowledgements

- [Meta Llama 3](https://github.com/meta-llama/llama) for the language model
- [Ollama](https://github.com/ollama/ollama) for model serving
- [FastAPI](https://fastapi.tiangolo.com/) for the API framework