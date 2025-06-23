"""
Base agent class and common utilities for the AI Embassy Staff system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from models.embassy_models import AgentResponse, AgentActivityLog
from config.env_loader import config

class BaseAgent(ABC):
    """Abstract base class for all Embassy agents."""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"embassy.{name}")
        
    @abstractmethod
    async def process(self, context: Dict[str, Any]) -> AgentResponse:
        """Process a request with given context and return standardized response."""
        pass
    
    def log_activity(self, action: str, summary: str) -> AgentActivityLog:
        """Create a standardized activity log entry."""
        return AgentActivityLog(
            agent=self.name,
            action=action,
            summary=summary
        )
    
    def create_response(self, success: bool, message: str, 
                       data: Optional[Dict[str, Any]] = None,
                       next_action: Optional[str] = None) -> AgentResponse:
        """Create a standardized agent response."""
        return AgentResponse(
            agent_name=self.name,
            success=success,
            message=message,
            data=data,
            next_action=next_action
        )


class AgentContext:
    """Shared context and utilities for agents."""
    
    def __init__(self):
        self.session_data: Dict[str, Any] = {}
        self.project_memory: Dict[str, Any] = {}
        
    def get_session_value(self, key: str, default: Any = None) -> Any:
        """Get value from session context."""
        return self.session_data.get(key, default)
    
    def set_session_value(self, key: str, value: Any) -> None:
        """Set value in session context."""
        self.session_data[key] = value
        
    def get_project_memory(self, project_id: str) -> Dict[str, Any]:
        """Get project-specific memory."""
        return self.project_memory.get(project_id, {})
    
    def update_project_memory(self, project_id: str, updates: Dict[str, Any]) -> None:
        """Update project-specific memory."""
        if project_id not in self.project_memory:
            self.project_memory[project_id] = {}
        self.project_memory[project_id].update(updates)


class MockResourceCatalog:
    """Mock TechHub resource catalog for prototype."""
    
    def __init__(self):
        self.resources = [
            {
                "resource_id": "demo-001",
                "title": "Azure OpenAI Chat Demo",
                "type": "Demo",
                "description": "Interactive chat demo showcasing Azure OpenAI integration",
                "tags": ["ai", "chat", "azure", "openai"],
                "industry": ["general"],
                "link": "https://techhub.internal/demos/azure-openai-chat"
            },
            {
                "resource_id": "solution-001", 
                "title": "Document Intelligence Pipeline",
                "type": "Solution",
                "description": "Complete solution for document processing with AI extraction",
                "tags": ["ai", "document", "processing", "pipeline"],
                "industry": ["finance", "legal", "healthcare"],
                "link": "https://techhub.internal/solutions/doc-intelligence"
            },
            {
                "resource_id": "component-001",
                "title": "Azure Functions Auth Handler",
                "type": "Component", 
                "description": "Reusable authentication component for Azure Functions",
                "tags": ["auth", "azure", "functions", "security"],
                "industry": ["general"],
                "link": "https://techhub.internal/components/auth-handler"
            },
            {
                "resource_id": "demo-002",
                "title": "Power BI Embedded Dashboard",
                "type": "Demo",
                "description": "Embedded analytics dashboard with Power BI",
                "tags": ["powerbi", "analytics", "dashboard", "embedded"],
                "industry": ["retail", "manufacturing", "finance"],
                "link": "https://techhub.internal/demos/powerbi-embedded"
            },
            {
                "resource_id": "solution-002",
                "title": "IoT Device Management Platform",
                "type": "Solution",
                "description": "Complete IoT device lifecycle management solution",
                "tags": ["iot", "device", "management", "azure"],
                "industry": ["manufacturing", "agriculture", "utilities"],
                "link": "https://techhub.internal/solutions/iot-platform"
            }
        ]
    
    def search_resources(self, query: str = "", 
                        resource_type: Optional[str] = None,
                        industry: Optional[str] = None,
                        tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search resources based on criteria."""
        results = self.resources.copy()
        
        if resource_type:
            results = [r for r in results if r["type"].lower() == resource_type.lower()]
            
        if industry:
            results = [r for r in results if industry.lower() in [i.lower() for i in r["industry"]]]
            
        if tags:
            results = [r for r in results if any(tag.lower() in [t.lower() for t in r["tags"]] for tag in tags)]
            
        if query:
            query_lower = query.lower()
            results = [r for r in results if 
                      query_lower in r["title"].lower() or 
                      query_lower in r["description"].lower() or
                      any(query_lower in tag.lower() for tag in r["tags"])]
        
        return results
    
    def get_resource_by_id(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get specific resource by ID."""
        for resource in self.resources:
            if resource["resource_id"] == resource_id:
                return resource
        return None
