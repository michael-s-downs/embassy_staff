"""
Archivist Agent - Stores dialogue history, project status, and user metadata.
"""

from typing import Dict, Any, List, Optional
from models.embassy_models import (
    AgentResponse, ChatSession, TechHubProject, UseCase, 
    AgentActivityLog, ResourceMatch
)
from agents.embassy_base_agent import BaseAgent
from services.embassy_storage import get_storage
from datetime import datetime, timezone
import json


class ArchivistAgent(BaseAgent):
    """Agent responsible for logging, archiving, and retrieving system history."""
    
    def __init__(self):
        super().__init__(
            name="ArchivistAgent",
            description="Stores dialogue history, project status, and user metadata"
        )
        self.storage = get_storage()
    
    async def process(self, context: Dict[str, Any]) -> AgentResponse:
        """Process archival requests."""
        action = context.get('action', 'log_interaction')
        
        if action == 'log_interaction':
            return await self._log_interaction(context)
        elif action == 'log_workflow':
            return await self._log_workflow(context)
        elif action == 'update_project_status':
            return await self._update_project_status(context)
        elif action == 'retrieve_history':
            return await self._retrieve_history(context)
        elif action == 'archive_session':
            return await self._archive_session(context)
        elif action == 'generate_report':
            return await self._generate_report(context)
        else:
            return self.create_response(
                success=False,
                message=f"Unknown archival action: {action}",
                next_action="error"
            )
    
    async def _log_interaction(self, context: Dict[str, Any]) -> AgentResponse:
        """Log a single interaction to session history."""
        session_id = context.get('session_id')
        interaction = context.get('interaction', {})
        
        if not session_id:
            return self.create_response(
                success=False,
                message="No session ID provided for logging",
                next_action="error"
            )
        
        # Get or create session
        session = await self.storage.get_item('chat_sessions', session_id, ChatSession)
        if not session:
            session = ChatSession(
                session_id=session_id,
                user_id=context.get('user_id', 'anonymous')
            )
        
        # Add interaction to history
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'agent': interaction.get('agent', 'unknown'),
            'action': interaction.get('action', 'unknown'),
            'user_input': interaction.get('user_input'),
            'agent_response': interaction.get('agent_response'),
            'metadata': interaction.get('metadata', {})
        }
        
        session.conversation_history.append(log_entry)
        session.last_activity = datetime.now(timezone.utc)
        
        # Update session with current context
        if context.get('use_case_id'):
            session.current_use_case_id = context['use_case_id']
        if context.get('project_id'):
            session.current_project_id = context['project_id']
        
        # Store updated session
        try:
            await self.storage.update_item('chat_sessions', session_id, session)
            
            activity = self.log_activity(
                action="interaction_logged",
                summary=f"Logged interaction for session {session_id}"
            )
            
            return self.create_response(
                success=True,
                message="Interaction logged successfully",
                data={
                    'session_id': session_id,
                    'log_entry': log_entry,
                    'activity_log': activity.model_dump()
                },
                next_action='logged'
            )
            
        except Exception as e:
            self.logger.error(f"Error logging interaction: {str(e)}")
            return self.create_response(
                success=False,
                message=f"Failed to log interaction: {str(e)}",
                next_action='error'
            )
    
    async def _log_workflow(self, context: Dict[str, Any]) -> AgentResponse:
        """Log complete workflow execution."""
        use_case_id = context.get('use_case_id')
        project_id = context.get('project_id')
        workflow_results = context.get('workflow_results', {})
        
        if not use_case_id:
            return self.create_response(
                success=False,
                message="No use case ID provided for workflow logging",
                next_action="error"
            )
        
        # Create workflow summary
        workflow_summary = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'use_case_id': use_case_id,
            'project_id': project_id,
            'workflow_type': 'intake_to_resource_matching',
            'steps_completed': [],
            'overall_success': True,
            'duration_ms': context.get('duration_ms', 0)
        }
        
        # Analyze workflow results
        for step_name, step_data in workflow_results.items():
            step_success = step_data.get('success', False) if isinstance(step_data, dict) else True
            workflow_summary['steps_completed'].append({
                'step': step_name,
                'success': step_success,
                'timestamp': step_data.get('timestamp') if isinstance(step_data, dict) else None
            })
            if not step_success:
                workflow_summary['overall_success'] = False
        
        # Update project if exists
        if project_id:
            project = await self.storage.get_item('projects', project_id, TechHubProject)
            if project:
                project.agent_activity_log.append(AgentActivityLog(
                    agent=self.name,
                    action="workflow_completed",
                    summary=f"Workflow completed with overall success: {workflow_summary['overall_success']}"
                ))
                project.last_updated = datetime.now(timezone.utc)
                await self.storage.update_item('projects', project_id, project)
        
        # Store workflow log
        workflow_log_path = self.storage.storage_path / 'workflow_logs' / f"{use_case_id}_workflow.json"
        workflow_log_path.parent.mkdir(exist_ok=True)
        
        try:
            with open(workflow_log_path, 'w') as f:
                json.dump(workflow_summary, f, indent=2)
            
            activity = self.log_activity(
                action="workflow_logged",
                summary=f"Logged workflow for use case {use_case_id}"
            )
            
            return self.create_response(
                success=True,
                message="Workflow logged successfully",
                data={
                    'workflow_summary': workflow_summary,
                    'activity_log': activity.model_dump()
                },
                next_action='workflow_logged'
            )
            
        except Exception as e:
            self.logger.error(f"Error logging workflow: {str(e)}")
            return self.create_response(
                success=False,
                message=f"Failed to log workflow: {str(e)}",
                next_action='error'
            )
    
    async def _update_project_status(self, context: Dict[str, Any]) -> AgentResponse:
        """Update project status and log the change."""
        project_id = context.get('project_id')
        new_status = context.get('status')
        status_notes = context.get('status_notes', '')
        
        if not project_id or not new_status:
            return self.create_response(
                success=False,
                message="Project ID and status required for update",
                next_action="error"
            )
        
        # Get project
        project = await self.storage.get_item('projects', project_id, TechHubProject)
        if not project:
            return self.create_response(
                success=False,
                message=f"Project {project_id} not found",
                next_action="error"
            )
        
        # Update project
        old_phase = project.current_phase
        project.current_phase = new_status
        project.status_notes = status_notes or project.status_notes
        project.last_updated = datetime.now(timezone.utc)
        
        # Add activity log
        project.agent_activity_log.append(AgentActivityLog(
            agent=self.name,
            action="status_updated",
            summary=f"Project phase changed from '{old_phase}' to '{new_status}'"
        ))
        
        # Handle special statuses
        if new_status == 'archived':
            project.archived = True
        elif new_status == 'promoted':
            project.promoted_to_resource_catalog = True
        
        # Store updated project
        try:
            await self.storage.update_item('projects', project_id, project)
            
            activity = self.log_activity(
                action="project_status_updated",
                summary=f"Updated project {project_id} status to {new_status}"
            )
            
            return self.create_response(
                success=True,
                message=f"Project status updated to {new_status}",
                data={
                    'project_id': project_id,
                    'old_phase': old_phase,
                    'new_phase': new_status,
                    'activity_log': activity.model_dump()
                },
                next_action='status_updated'
            )
            
        except Exception as e:
            self.logger.error(f"Error updating project status: {str(e)}")
            return self.create_response(
                success=False,
                message=f"Failed to update project status: {str(e)}",
                next_action='error'
            )
    
    async def _retrieve_history(self, context: Dict[str, Any]) -> AgentResponse:
        """Retrieve historical data based on criteria."""
        history_type = context.get('history_type', 'session')
        entity_id = context.get('entity_id')
        user_id = context.get('user_id')
        limit = context.get('limit', 50)
        
        if history_type == 'session' and entity_id:
            # Retrieve session history
            session = await self.storage.get_item('chat_sessions', entity_id, ChatSession)
            if not session:
                return self.create_response(
                    success=False,
                    message=f"Session {entity_id} not found",
                    next_action="error"
                )
            
            history_data = {
                'type': 'session',
                'session_id': entity_id,
                'conversation_count': len(session.conversation_history),
                'last_activity': session.last_activity.isoformat(),
                'recent_history': session.conversation_history[-limit:]
            }
            
        elif history_type == 'project' and entity_id:
            # Retrieve project history
            project = await self.storage.get_item('projects', entity_id, TechHubProject)
            if not project:
                return self.create_response(
                    success=False,
                    message=f"Project {entity_id} not found",
                    next_action="error"
                )
            
            history_data = {
                'type': 'project',
                'project_id': entity_id,
                'activity_count': len(project.agent_activity_log),
                'current_phase': project.current_phase,
                'recent_activities': [a.model_dump() for a in project.agent_activity_log[-limit:]]
            }
            
        elif history_type == 'user' and user_id:
            # Retrieve user history
            sessions = await self.storage.get_recent_sessions(user_id, limit=10)
            projects = await self.storage.get_user_projects(user_id)
            
            history_data = {
                'type': 'user',
                'user_id': user_id,
                'total_sessions': len(sessions),
                'total_projects': len(projects),
                'recent_sessions': [
                    {
                        'session_id': s.session_id,
                        'last_activity': s.last_activity.isoformat(),
                        'conversation_count': len(s.conversation_history)
                    }
                    for s in sessions
                ],
                'projects': [
                    {
                        'project_id': p.project_id,
                        'title': p.title,
                        'phase': p.current_phase,
                        'last_updated': p.last_updated.isoformat()
                    }
                    for p in projects
                ]
            }
        else:
            return self.create_response(
                success=False,
                message="Invalid history retrieval parameters",
                next_action="error"
            )
        
        activity = self.log_activity(
            action="history_retrieved",
            summary=f"Retrieved {history_type} history"
        )
        
        return self.create_response(
            success=True,
            message=f"Retrieved {history_type} history successfully",
            data={
                'history': history_data,
                'activity_log': activity.model_dump()
            },
            next_action='history_retrieved'
        )
    
    async def _archive_session(self, context: Dict[str, Any]) -> AgentResponse:
        """Archive a completed session."""
        session_id = context.get('session_id')
        
        if not session_id:
            return self.create_response(
                success=False,
                message="No session ID provided for archiving",
                next_action="error"
            )
        
        # Get session
        session = await self.storage.get_item('chat_sessions', session_id, ChatSession)
        if not session:
            return self.create_response(
                success=False,
                message=f"Session {session_id} not found",
                next_action="error"
            )
        
        # Update session status
        session.status = 'archived'
        session.last_activity = datetime.now(timezone.utc)
        
        # Create archive summary
        archive_summary = {
            'session_id': session_id,
            'user_id': session.user_id,
            'archived_at': datetime.now(timezone.utc).isoformat(),
            'total_interactions': len(session.conversation_history),
            'duration_minutes': (session.last_activity - session.created_at).total_seconds() / 60,
            'associated_use_case': session.current_use_case_id,
            'associated_project': session.current_project_id
        }
        
        # Store archive summary
        archive_path = self.storage.storage_path / 'archives' / f"session_{session_id}_archive.json"
        archive_path.parent.mkdir(exist_ok=True)
        
        try:
            with open(archive_path, 'w') as f:
                json.dump(archive_summary, f, indent=2)
            
            # Update session
            await self.storage.update_item('chat_sessions', session_id, session)
            
            activity = self.log_activity(
                action="session_archived",
                summary=f"Archived session {session_id}"
            )
            
            return self.create_response(
                success=True,
                message="Session archived successfully",
                data={
                    'archive_summary': archive_summary,
                    'activity_log': activity.model_dump()
                },
                next_action='archived'
            )
            
        except Exception as e:
            self.logger.error(f"Error archiving session: {str(e)}")
            return self.create_response(
                success=False,
                message=f"Failed to archive session: {str(e)}",
                next_action='error'
            )
    
    async def _generate_report(self, context: Dict[str, Any]) -> AgentResponse:
        """Generate a report based on historical data."""
        report_type = context.get('report_type', 'project_summary')
        entity_id = context.get('entity_id')
        
        if report_type == 'project_summary' and entity_id:
            # Generate project summary report
            project = await self.storage.get_item('projects', entity_id, TechHubProject)
            if not project:
                return self.create_response(
                    success=False,
                    message=f"Project {entity_id} not found",
                    next_action="error"
                )
            
            # Get related data
            use_case = await self.storage.get_item('use_cases', project.use_case_id, UseCase)
            matches = await self.storage.get_project_matches(entity_id)
            
            report = {
                'report_type': 'project_summary',
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'project': {
                    'id': project.project_id,
                    'title': project.title,
                    'current_phase': project.current_phase,
                    'created_by': project.created_by,
                    'collaborators': project.collaborators,
                    'is_archived': project.archived,
                    'is_promoted': project.promoted_to_resource_catalog
                },
                'use_case': {
                    'title': use_case.title if use_case else 'Unknown',
                    'description': use_case.description if use_case else 'N/A',
                    'industry': use_case.industry_vertical if use_case else 'N/A',
                    'cloud': use_case.cloud_preference if use_case else 'N/A'
                },
                'activity_summary': {
                    'total_activities': len(project.agent_activity_log),
                    'agents_involved': list(set(a.agent for a in project.agent_activity_log)),
                    'last_activity': project.agent_activity_log[-1].model_dump() if project.agent_activity_log else None
                },
                'resources': {
                    'total_matches': len(matches[0].recommended_resources) if matches else 0,
                    'top_resources': [r.model_dump() for r in matches[0].recommended_resources[:3]] if matches else []
                }
            }
            
        elif report_type == 'user_activity':
            user_id = context.get('user_id')
            if not user_id:
                return self.create_response(
                    success=False,
                    message="User ID required for user activity report",
                    next_action="error"
                )
            
            # Generate user activity report
            projects = await self.storage.get_user_projects(user_id)
            sessions = await self.storage.get_recent_sessions(user_id, limit=20)
            
            report = {
                'report_type': 'user_activity',
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'user_id': user_id,
                'summary': {
                    'total_projects': len(projects),
                    'active_projects': len([p for p in projects if not p.archived]),
                    'promoted_projects': len([p for p in projects if p.promoted_to_resource_catalog]),
                    'total_sessions': len(sessions)
                },
                'recent_activity': {
                    'last_session': sessions[0].last_activity.isoformat() if sessions else None,
                    'recent_projects': [
                        {
                            'title': p.title,
                            'phase': p.current_phase,
                            'last_updated': p.last_updated.isoformat()
                        }
                        for p in sorted(projects, key=lambda x: x.last_updated, reverse=True)[:5]
                    ]
                }
            }
        else:
            return self.create_response(
                success=False,
                message=f"Unknown report type: {report_type}",
                next_action="error"
            )
        
        activity = self.log_activity(
            action="report_generated",
            summary=f"Generated {report_type} report"
        )
        
        return self.create_response(
            success=True,
            message=f"Generated {report_type} report successfully",
            data={
                'report': report,
                'activity_log': activity.model_dump()
            },
            next_action='report_generated'
        )
