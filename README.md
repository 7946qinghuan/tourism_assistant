# Tourism Assistant API

A backend service for planning trips using a multi-agent AI system. This service uses FastAPI to provide an API and leverages the `camel-ai` framework to orchestrate specialized AI agents for tasks like finding attractions, checking weather, and booking hotels.

## Features

- **Multi-Agent Orchestration**: Dynamically uses different AI agents to build a comprehensive travel plan.
- **FastAPI Backend**: A robust and fast asynchronous API layer.
- **Configurable**: Server host, port, and LLM settings can be configured via an `.env` file.
- **Developer Friendly**: Comes with a `Makefile` for easy access to common commands like running and formatting.

---

## Setup and Installation

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd tourism-assistant
```

### 2. Install Dependencies

This project uses `uv` for package management. Ensure you have it installed.

Install the project dependencies, including the local `sdk` in editable mode:

```bash
uv pip install -e ./sdk
uv pip install .
```

### 3. Configure Environment

Create a `.env` file in the root of the project. This file will hold your secret keys and environment-specific settings.

```bash
touch .env
```

Open the `.env` file and add the following configuration. Be sure to replace the placeholder values with your actual API keys and settings.

```env
# LLM Provider Settings
LLM_BASE_NAME="<your_model_name>"
LLM_BASE_URL="<your_llm_provider_url>"
LLM_BASE_API_KEY="<your_api_key>"
AMAP_MCP_TOOL_CONFIG_PATH="<path_to_your_amap_config_file>"

# Server Settings (Optional)
TOURISM_HOST="0.0.0.0"
TOURISM_PORT="27000"
```

---

## Running the Application

To start the FastAPI server, use the `make` command:

```bash
make run
```

The server will start on the host and port specified in your `.env` file (or `0.0.0.0:27000` by default). The service includes hot-reloading, so it will automatically restart when you make changes to the code.

---

## API Usage Example

You can test the main endpoint using `curl` or any API client. Send a `POST` request to `/api/v1/plan` with your travel preferences.

### cURL Request

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/v1/plan' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "city": "成都",
    "start_date": "2026-02-21",
    "end_date": "2026-02-28",
    "travel_days": 7,
    "transportation": "飞机",
    "accommodation": "五星级酒店",
    "preferences": ["博物馆", "古镇", "美食"],
    "free_text_input": "我喜欢吃辣，也想看熊猫"
  }'
```

### Response

The API will return a JSON object containing the generated travel plan:

```json
{
  "plan": "这是一个由AI生成的详细旅行计划..."
}
```
