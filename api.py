"""
FastAPI Web Interface for AI Embassy Staff

This module provides HTTP endpoints for the multi-agent system.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime
import uuid
from config.env_loader import config

# Import agents and models
from agents.embassy_concierge_agent import ConciergeAgent
from agents.embassy_orchestrator_agent import OrchestratorAgent
from agents.embassy_navigator_agent import NavigatorAgent
from agents.archivist_agent import ArchivistAgent
from models.embassy_models import UseCase, ChatSession, TechHubProject
from services.embassy_storage import get_storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("embassy.api")

# Create FastAPI app
app = FastAPI(
    title="AI Embassy Staff API",
    description="Multi-agent system for TechHub resource discovery",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents
concierge = ConciergeAgent()
orchestrator = OrchestratorAgent()
navigator = NavigatorAgent()
archivist = ArchivistAgent()
storage = get_storage()


# Request/Response Models
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    user_id: str
    message: str
    context: Optional[Dict[str, Any]] = {}


class ChatResponse(BaseModel):
    session_id: str
    agent: str
    message: str
    data: Optional[Dict[str, Any]] = {}
    next_action: Optional[str] = None


class IntakeRequest(BaseModel):
    user_id: str
    use_case_data: Dict[str, Any]


class WorkflowRequest(BaseModel):
    use_case_id: str
    user_id: str


class ProjectStatusRequest(BaseModel):
    project_id: str
    new_status: str
    status_notes: Optional[str] = None


# Endpoints
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "AI Embassy Staff",
        "status": "active",
        "version": "1.0.0",
        "agents": ["ConciergeAgent", "OrchestratorAgent", "NavigatorAgent", "ArchivistAgent"]
    }


@app.post("/chat/start", response_model=ChatResponse)
async def start_chat(user_id: str = "anonymous"):
    """Start a new chat session."""
    try:
        # Start greeting flow
        context = {
            'user_name': user_id,
            'user_id': user_id
        }
        
        response = await concierge.process(context)
        
        # Log session start
        await archivist.process({
            'action': 'log_interaction',
            'session_id': response.data.get('session_id'),
            'interaction': {
                'agent': 'ConciergeAgent',
                'action': 'session_started',
                'user_input': None,
                'agent_response': response.message
            }
        })
        
        return ChatResponse(
            session_id=response.data.get('session_id'),
            agent=response.agent_name,
            message=response.message,
            data=response.data,
            next_action=response.next_action
        )
        
    except Exception as e:
        logger.error(f"Error starting chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a message in an existing chat session."""
    try:
        # Prepare context
        context = {
            'session_id': request.session_id,
            'user_id': request.user_id,
            'user_input': request.message,
            **request.context
        }
        
        # Log user message
        await archivist.process({
            'action': 'log_interaction',
            'session_id': request.session_id,
            'interaction': {
                'agent': 'user',
                'action': 'message',
                'user_input': request.message
            }
        })
        
        # Route to appropriate agent based on context
        # For now, default to concierge
        response = await concierge.process(context)
        
        # Log agent response
        await archivist.process({
            'action': 'log_interaction',
            'session_id': request.session_id,
            'interaction': {
                'agent': response.agent_name,
                'action': 'response',
                'agent_response': response.message
            }
        })
        
        return ChatResponse(
            session_id=request.session_id or response.data.get('session_id'),
            agent=response.agent_name,
            message=response.message,
            data=response.data,
            next_action=response.next_action
        )
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/intake/submit")
async def submit_intake(request: IntakeRequest):
    """Submit a complete intake form."""
    try:
        # Create UseCase from submitted data
        use_case_data = {
            'created_by': request.user_id,
            **request.use_case_data
        }
        
        use_case = UseCase(**use_case_data)
        await storage.create_item('use_cases', use_case)
        
        return {
            'success': True,
            'use_case_id': use_case.use_case_id,
            'message': 'Intake submitted successfully',
            'next_action': 'orchestrate'
        }
        
    except Exception as e:
        logger.error(f"Error submitting intake: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/workflow/orchestrate")
async def orchestrate_workflow(request: WorkflowRequest, background_tasks: BackgroundTasks):
    """Start the orchestration workflow for a use case."""
    try:
        # Verify use case exists
        use_case = await storage.get_item('use_cases', request.use_case_id, UseCase)
        if not use_case:
            raise HTTPException(status_code=404, detail="Use case not found")
        
        # Start orchestration in background
        background_tasks.add_task(
            run_orchestration_workflow,
            request.use_case_id,
            request.user_id
        )
        
        return {
            'success': True,
            'message': 'Orchestration workflow started',
            'use_case_id': request.use_case_id,
            'status': 'processing'
        }
        
    except Exception as e:
        logger.error(f"Error starting orchestration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_orchestration_workflow(use_case_id: str, user_id: str):
    """Run the full orchestration workflow asynchronously."""
    try:
        # Run orchestration
        result = await orchestrator.orchestrate_full_workflow(use_case_id)
        
        # Log workflow completion
        await archivist.process({
            'action': 'log_workflow',
            'use_case_id': use_case_id,
            'project_id': result.data.get('project_id') if result.success else None,
            'workflow_results': result.data
        })
        
    except Exception as e:
        logger.error(f"Error in orchestration workflow: {str(e)}")


@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details."""
    try:
        project = await storage.get_item('projects', project_id, TechHubProject)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get related data
        use_case = await storage.get_item('use_cases', project.use_case_id, UseCase)
        matches = await storage.get_project_matches(project_id)
        
        return {
            'project': project.model_dump(),
            'use_case': use_case.model_dump() if use_case else None,
            'resource_matches': [m.model_dump() for m in matches]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/projects/{project_id}/status")
async def update_project_status(project_id: str, request: ProjectStatusRequest):
    """Update project status."""
    try:
        response = await archivist.process({
            'action': 'update_project_status',
            'project_id': project_id,
            'status': request.new_status,
            'status_notes': request.status_notes
        })
        
        if not response.success:
            raise HTTPException(status_code=400, detail=response.message)
        
        return {
            'success': True,
            'message': 'Project status updated',
            'data': response.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}/projects")
async def get_user_projects(user_id: str):
    """Get all projects for a user."""
    try:
        projects = await storage.get_user_projects(user_id)
        
        return {
            'user_id': user_id,
            'total_projects': len(projects),
            'projects': [p.model_dump() for p in projects]
        }
        
    except Exception as e:
        logger.error(f"Error getting user projects: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}/history")
async def get_user_history(user_id: str, limit: int = 10):
    """Get user activity history."""
    try:
        response = await archivist.process({
            'action': 'retrieve_history',
            'history_type': 'user',
            'user_id': user_id,
            'limit': limit
        })
        
        if not response.success:
            raise HTTPException(status_code=400, detail=response.message)
        
        return response.data['history']
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/resources/search")
async def search_resources(query: str, resource_type: Optional[str] = None, 
                         industry: Optional[str] = None):
    """Search TechHub resources directly."""
    try:
        # Use navigator to search
        catalog = navigator.resource_catalog
        results = catalog.search_resources(
            query=query,
            resource_type=resource_type,
            industry=industry
        )
        
        return {
            'query': query,
            'total_results': len(results),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Error searching resources: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reports/generate")
async def generate_report(report_type: str, entity_id: str):
    """Generate a report."""
    try:
        response = await archivist.process({
            'action': 'generate_report',
            'report_type': report_type,
            'entity_id': entity_id
        })
        
        if not response.success:
            raise HTTPException(status_code=400, detail=response.message)
        
        return response.data['report']
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time updates (optional)
from fastapi import WebSocket, WebSocketDisconnect
from typing import Set

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_update(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)

manager = ConnectionManager()


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat updates."""
    await manager.connect(websocket, session_id)
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_json()
            
            # Process message
            response = await send_message(ChatRequest(
                session_id=session_id,
                user_id=data.get('user_id', 'anonymous'),
                message=data.get('message', ''),
                context=data.get('context', {})
            ))
            
            # Send response
            await websocket.send_json(response.model_dump())
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info(f"WebSocket disconnected: {session_id}")


if __name__ == "__main__":
    import uvicorn
    
    # Import config at the top of the file if not already done
    from config.env_loader import config
    
    # Validate configuration
    warnings = config.validate()
    if warnings:
        print("\n⚠️  Configuration warnings:")
        for warning in warnings:
            print(f"   - {warning}")
        print()
    
    print(f"\n🚀 Starting AI Embassy Staff API")
    print(f"   Host: {config.API_HOST}")
    print(f"   Port: {config.API_PORT}")
    print(f"   Environment: {config.ENVIRONMENT}")
    print(f"   Docs: http://{config.API_HOST}:{config.API_PORT}/docs\n")
    
    uvicorn.run(
        app, 
        host=config.API_HOST, 
        port=config.API_PORT, 
        reload=config.ENVIRONMENT == "development"
    )
