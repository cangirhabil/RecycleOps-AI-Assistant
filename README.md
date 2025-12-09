# RecycleOps AI Assistant

An AI-powered assistant that automatically reads error logs and solution conversations on Slack, learns from them, and provides instant solutions to the technical team when similar issues occur in the future.

## 🎯 Purpose

The system's primary goal is to build **"Organizational Memory"** and accelerate technical support.

## ⚙️ How the System Works

The system operates in a continuous loop across 3 stages:

1. **Listening and Tracking**: Monitors all machine failure notifications and comments in Slack channels.
2. **Smart Analysis and Learning**: When a conversation about a failure ends (12 hours after the last message), the AI reads the entire conversation and saves the solution to its memory.
3. **Support and Solutions**: When a new failure occurs, the assistant reviews past experiences in its memory and suggests solutions.

## ✨ Core Features

| Feature | Command | Description |
|---------|---------|----------|
| Automatic Learning | - | Automatically analyzes conversations using the 12-hour rule |
| Smart Search | `/search [issue]` | Searches past solutions |
| In-Thread Suggestions | `/cozum-getir` | Suggests solutions for thread issues |
| Quick Save | `/cozum-ekle` | Instantly saves conversation to memory |
| Proactive Support | - | Automatically suggests solutions for new errors |
| Expert Routing | - | Suggests experts when no solution is found |

## 🏗️ Technology Stack

- **Backend**: Python 3.11+
- **Slack**: Slack Bolt SDK
- **Vector DB**: ChromaDB (local)
- **SQL DB**: PostgreSQL
- **RAG**: LangChain + OpenAI
- **Scheduling**: APScheduler

## 📦 Installation

### Requirements

- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose (optional)

### 1. Clone the Repository

```bash
git clone https://github.com/cangirhabil/RecycleOps-AI-Assistant.git
cd RecycleOps-AI-Assistant
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -e ".[dev]"
```

### 4. Environment Variables

```bash
cp .env.example .env
# Edit .env and enter required values
```

### 5. Initialize Database

```bash
# With Docker
docker-compose up -d postgres

# Run migrations
alembic upgrade head
```

### 6. Start the Application

```bash
python -m src.main
```

## 🔧 Slack App Setup

1. Create a new app on [Slack API](https://api.slack.com/apps)
2. Enable **Socket Mode**
3. Add these events under **Event Subscriptions**:
   - `message.channels`
   - `message.groups`
   - `app_mention`
4. Add **Slash Commands**:
   - `/search`
   - `/cozum-getir`
   - `/cozum-ekle`
5. Configure **OAuth Scopes** (Bot Token Scopes):
   - `channels:history`
   - `channels:read`
   - `chat:write`
   - `commands`
   - `groups:history`
   - `groups:read`
   - `users:read`

## 📁 Project Structure

```
RecycleOps-AI-Assistant/
├── src/
│   ├── main.py              # Application entry point
│   ├── config.py            # Configuration management
│   ├── slack/               # Slack bot modules
│   ├── rag/                 # RAG pipeline modules
│   ├── learning/            # Automatic learning modules
│   ├── database/            # Database modules
│   ├── services/            # Business logic services
│   └── utils/               # Helper functions
├── tests/                   # Test files
├── migrations/              # Alembic migrations
└── data/chroma/             # ChromaDB data
```

## 🧪 Testing

```bash
pytest tests/ -v --cov=src
```

## 📝 License

MIT License

