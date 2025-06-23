# AI Embassy Staff - Multi-Agent System for TechHub

A Python-based intelligent multi-agent system that assists internal users in capturing use cases and matching them to TechHub resources (Demos, Solutions, and Components).

## 🏛️ Overview

The AI Embassy Staff system transforms static TechHub resources into an interactive, agent-guided experience using a centralizing state-management concept of shared and tracked 'Projects.'  The Staff helps sales teams, solution builders, and infrastructure leads work together on Projects by:

- Capturing and refining business use cases
- Matching defined use-cases to existing TechHub resources that can implement them
- Generating Bills of Materials (BOMs) and Project Implementation Outlines
- Managing project lifecycles from intake to catalog promotion (feeding back as searchable data for future users of the system)

## 🏗️ Architecture

### Core Agents

1. **ConciergeAgent** - Handles user interaction, intake forms, and conversation flow
2. **OrchestratorAgent** - Central coordinator that analyzes intents and spawns appropriate agents
3. **NavigatorAgent** - Searches TechHub resources and generates resource matches and BOMs
4. **ArchivistAgent** - Stores dialogue history, project status, and generates reports

### Data Models

- **UseCase** - Captures all intake information
- **TechHubProject** - Tracks the full lifecycle of a use case
- **ResourceMatch** - Contains matched resources and generated BOMs
- **ChatSession** - Manages conversation state

## 📁 Project Structure

```
embassy-staff/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py         # Base agent class and utilities
│   ├── concierge_agent.py    # User interaction agent
│   ├── orchestrator_agent.py # Central coordination agent
│   ├── navigator_agent.py    # Resource matching agent
│   └── archivist_agent.py    # Logging and archival agent
├── models/
│   ├── __init__.py
│   └── data_models.py        # Pydantic data models
├── services/
│   ├── __init__.py
│   └── storage_service.py    # JSON-based storage service
├── data/                     # JSON storage directory (created on first run)
├── main.py                   # CLI entry point
├── api.py                    # FastAPI web interface
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Installation

1. Clone the repository or extract the project files:
   
   ```bash
   mkdir embassy-staff
   cd embassy-staff
   ```

2. Create a virtual environment:
   
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   
   ```bash
   pip install -r requirements.txt
   ```

### Create Project Structure

Create the necessary directories:

```bash
mkdir -p agents models services data
```

Place the provided Python files in their respective directories:

- `embassy_base_agent.py` → `agents/base_agent.py`
- `embassy_concierge_agent.py` → `agents/concierge_agent.py`
- `embassy_orchestrator_agent.py` → `agents/orchestrator_agent.py`
- `embassy_navigator_agent.py` → `agents/navigator_agent.py`
- `embassy_archivist_agent.py` → `agents/archivist_agent.py`
- `embassy_models.py` → `models/data_models.py`
- `embassy_storage.py` → `services/storage_service.py`

Create `__init__.py` files in each directory:

```bash
touch agents/__init__.py models/__init__.py services/__init__.py
```

## 🎮 Usage

### CLI Mode

Run the interactive CLI demo:

```bash
python main.py
```

Run with pre-configured demo data:

```bash
python main.py --demo
```

### Web API Mode

Start the FastAPI server:

```bash
python api.py
```

The API will be available at `http://localhost:8000`. Access the interactive API docs at `http://localhost:8000/docs`.

## 📋 Dependencies

Create a `requirements.txt` file with:

```
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.4.2
python-multipart==0.0.6
websockets==12.0
```

## 🔧 Configuration

The system uses file-based JSON storage by default. Data is stored in the `./data` directory:

- `use_cases/` - Use case records
- `projects/` - Project tracking
- `resource_matches/` - Resource matching results
- `chat_sessions/` - Conversation history

## 📡 API Endpoints

Key endpoints include:

- `POST /chat/start` - Start a new chat session
- `POST /chat/message` - Send a message in existing session
- `POST /intake/submit` - Submit a complete intake form
- `POST /workflow/orchestrate` - Start orchestration workflow
- `GET /projects/{project_id}` - Get project details
- `GET /users/{user_id}/projects` - Get user's projects
- `POST /resources/search` - Search TechHub resources
- `POST /reports/generate` - Generate reports

## 🎯 Example Workflow

1. **Start Session**: User initiates embassy-chat
2. **Project Choice**: Select NEW or EXISTING project
3. **Intake Form**: Provide project details (guided or comprehensive)
4. **Orchestration**: System analyzes requirements
5. **Resource Matching**: Navigator searches TechHub catalog
6. **BOM Generation**: Creates bill of materials
7. **Project Creation**: Tracks project for lifecycle management

## 🔄 Future Enhancements

### Additional Agents (Pluggable)

- **ResearchAgent** - Searches precedent patterns and client analogs
- **InfraAgent** - Validates infrastructure requirements
- **ComplianceAgent** - Checks regulatory compliance
- **CostAgent** - Estimates project costs

### Production Considerations

- Replace JSON storage with CosmosDB
- Implement proper authentication/authorization
- Add comprehensive error handling and retry logic
- Integrate with real TechHub catalog API
- Deploy to Azure Functions or Container Apps
- Add monitoring and analytics
- Implement rate limiting and caching

## 🧪 Testing

Run the demo mode to test the full workflow:

```bash
python main.py --demo
```

This will:

1. Create a sample use case for document processing
2. Run the complete orchestration workflow
3. Display matched resources and generated BOM
4. Generate a project summary report

## 📝 Notes

- The current implementation uses a mock resource catalog with sample data
- Storage is file-based JSON for prototype simplicity
- In production, integrate with actual TechHub APIs and Azure services
- The system is designed for extensibility with new agents and capabilities

## 🤝 Contributing

To add new agents:

1. Create a new agent class inheriting from `BaseAgent`
2. Implement the `process` method
3. Register the agent in the orchestrator's routing logic
4. Update the agent execution order if needed

## 📄 License

This is a prototype implementation for NTT DATA internal use.
