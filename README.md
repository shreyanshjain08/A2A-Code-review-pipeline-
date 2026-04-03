# 🧑‍💻 A2A Code Review Pipeline

A premium, multi-agent autonomous coding pipeline built with Google's **Agent-to-Agent (A2A) Protocol** and powered by the massive open-weights **Gemma-4-31B** model.

Three completely independent AI agents collaborate continuously to generate, thoroughly review, and perfectly refactor code based on your prompts—all communicating seamlessly via the A2A JSON-RPC protocol.

![A2A Protocol](https://img.shields.io/badge/A2A-Protocol-6366f1?style=for-the-badge)
![Gemma AI](https://img.shields.io/badge/Google-Gemma_4_31B-4285F4?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge)

## ✨ Features

- **3 Specialized A2A Agents** that discover each other and communicate dynamically via A2A
- **Code Writer Agent** — Transmutes sheer natural language into functional framework code
- **Code Reviewer Agent** — Acts as a senior engineer to identify anti-patterns, edge cases, and bugs 
- **Code Refactorer Agent** — Produces the final, highly optimized clean code structure
- **Premium SaaS UI** — A beautiful, dark-mode, animated interface to watch the agents execute in real-time
- **Docker Ready** — Completely containerized deployment logic included 

## 🏗️ Architecture Flow

```text
User → Web UI → Orchestrator → Code Writer (A2A) → Code Reviewer (A2A) → Code Refactorer (A2A)
                     ↑                                                            |
                     └────────────────── Final Result ────────────────────────────┘
```

Each agent is a 100% independent server that operates by:
1. Hosting an **Agent Card** at `/.well-known/agent-card.json` advertising its schema
2. Accepting **JSON-RPC 2.0** requests via the `message/send` method
3. Utilizing Google GenAI SDK (Gemma-4-31B) to analyze code contexts
4. Returning strictly structured target **Artifacts** to the pipeline

## 🚀 Quick Start (Local Setup)

### Prerequisites

- Python 3.10+
- [Google Generative AI Key](https://aistudio.google.com) (free!)

### Basic Installation

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd A2A

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment
cp .env.example .env
# Edit .env and paste your GEMINI_API_KEY inside!

# 5. Start the Multi-Agent Hive!
chmod +x start.sh
./start.sh
```

Open **http://localhost:3000** in your browser 🎉

### 🐳 With Docker (Production Grade)

Are you tired of configuring python environments? Use Docker Compose to instantly boot all four microservices securely!

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

docker-compose up --build
```

## 📁 Repository Structure

```text
A2A/
├── agents/             
│   ├── code_writer/       # A2A Agent on Port 5001
│   ├── code_reviewer/     # A2A Agent on Port 5002
│   └── code_refactorer/   # A2A Agent on Port 5003
├── orchestrator/
│   └── server.py          # FastAPI Orchestrator on Port 3000
├── frontend/              # Premium Aesthetic Static UI
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── start.sh               # Local Bootstrapper
└── .env.example
```

## 🛠️ Technology Stack

| Architecture Layer | Technology |
|-----------|-----------|
| Inter-Agent Communication | `a2a-sdk` (Official Protocol SDK) |
| Neural Engine | `models/gemma-4-31b-it` |
| Orchestrator & Backends | `FastAPI` + `Uvicorn` |
| View Layer | Highly customized CSS3 + Glassmorphism + JS |
| Deployment | `Docker` / Local Shell |

## 📄 License

MIT License — Feel free to use this architecture in your own portfolio!

---

*Built with ❤️ utilizing the [Google A2A Protocol](https://github.com/a2aproject/A2A)*
