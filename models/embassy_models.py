"""
Data models for the AI Embassy Staff multi-agent system.
These models define the core data structures used throughout the system.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from uuid import uuid4, UUID


class ProjectConstraints(BaseModel):
    """Project constraints including budget, timeline, and requirements."""
    budget: Optional[Union[str, float]] = None
    timeline: Optional[str] = None
    known_dependencies: List[str] = Field(default_factory=list)
    compliance_requirements: List[str] = Field(default_factory=list)


class UseCase(BaseModel):
    """Core use case model capturing all intake information."""
    use_case_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str
    industry_vertical: Optional[str] = None
    client_name: Optional[str] = None
    client_context: Optional[str] = None
    internal_contacts: List[str] = Field(default_factory=list)
    cloud_preference: Optional[str] = None
    project_constraints: ProjectConstraints = Field(default_factory=ProjectConstraints)
    engagement_stage: Optional[str] = None
    success_criteria: List[str] = Field(default_factory=list)
    resource_type_preference: List[str] = Field(default_factory=list)  # Demo, Solution, Component
    status: str = "new"
    created_by: str
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)


class AgentActivityLog(BaseModel):
    """Log entry for agent activities."""
    agent: str
    timestamp: datetime = Field(default_factory=datetime.now)
    action: str
    summary: str


class TechHubProject(BaseModel):
    """Project model tracking the full lifecycle of a use case."""
    project_id: str = Field(default_factory=lambda: str(uuid4()))
    use_case_id: str
    title: str
    current_phase: str = "intake"
    created_by: str
    collaborators: List[str] = Field(default_factory=list)
    agent_activity_log: List[AgentActivityLog] = Field(default_factory=list)
    status_notes: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.now)
    archived: bool = False
    promoted_to_resource_catalog: bool = False
    final_linked_assets: List[str] = Field(default_factory=list)
    repository_url: Optional[str] = None
    repository_visibility: str = "Private"  # Public, Private, Internal


class RecommendedResource(BaseModel):
    """Individual resource recommendation."""
    resource_id: str
    title: str
    type: str  # Demo, Solution, Component
    relevance_score: float = Field(ge=0.0, le=1.0)
    description: str
    link: str


class BOMItem(BaseModel):
    """Bill of Materials item."""
    item: str
    category: str
    source: str
    required: bool = True


class ResourceMatch(BaseModel):
    """Resource matching results and generated BOM."""
    match_id: str = Field(default_factory=lambda: str(uuid4()))
    use_case_id: str
    matched_on: datetime = Field(default_factory=datetime.now)
    matched_by: str  # Agent name
    recommended_resources: List[RecommendedResource] = Field(default_factory=list)
    generated_bom: List[BOMItem] = Field(default_factory=list)
    notes: Optional[str] = None
    status: str = "active"


class ChatSession(BaseModel):
    """Chat session state management."""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    current_use_case_id: Optional[str] = None
    current_project_id: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    status: str = "active"  # active, completed, archived


class AgentResponse(BaseModel):
    """Standardized agent response format."""
    agent_name: str
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    next_action: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
