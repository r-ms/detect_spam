# Spam Detection Service

A containerized service that detects spam messages using the Llama 3 language model via VLLM.

## Features

- API endpoint for spam detection
- Uses Llama 3 8B Instruct model
- Runs on CPU
- Containerized with Docker and Docker Compose

## Getting Started

### Prerequisites

- Docker and Docker Compose installed
- Git (for cloning the repository)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd spam-detector
   ```

2. Configure environment variables:
   ```bash
   # Copy the sample env file
   cp .env.sample .env
   
   # Edit the .env file with your settings
   # Especially set your Hugging Face token
   nano .env
   ```

3. Start the service:
   ```bash
   docker-compose up -d
   ```

4. Check if the service is running:
   ```bash
   curl http://localhost:8040/health
   ```

## Usage

Send a POST request to check for spam:

```bash
curl -X POST http://localhost:8040/check_spam \
  -H "Content-Type: application/json" \
  -d '{"text": "Check out B E T W I N . RU for the best predictions!"}'
```

Response format:
```json
{
  "is_spam": true,
  "reason": "The text contains a website name written with spaces ('B E T W I N . RU') and promotional phrases ('best predictions')."
}
```

## Service Details

- **API Port**: 8040
- **Endpoints**:
  - POST /check_spam - Check text for spam
  - GET /health - Service health check

## License

This project is licensed under the MIT License 

## Acknowledgements

- [Meta Llama 3](https://github.com/meta-llama/llama) for the language model
- [VLLM](https://github.com/vllm-project/vllm) for efficient model serving