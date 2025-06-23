"""
Orchestrator Agent - Central coordinator that analyzes intents and spawns appropriate agents.
"""

from typing import Dict, Any, List, Optional
from models.embassy_models import UseCase, TechHubProject, AgentResponse, AgentActivityLog
from agents.embassy_base_agent import BaseAgent
from services.embassy_storage import get_storage
import asyncio


class OrchestratorAgent(BaseAgent):
    """Central orchestrator that manages agent spawning and coordination."""
    
    def __init__(self):
        super().__init__(
            name="OrchestratorAgent", 
            description="Central coordinator for agent spawning and task orchestration"
        )
        self.storage = get_storage()
        self.active_agents = {}
        
    async def process(self, context: Dict[str, Any]) -> AgentResponse:
        """Process orchestration requests and spawn appropriate agents."""
        action = context.get('action', 'analyze_intent')
        
        if action == 'analyze_intent':
            return await self._analyze_intent(context)
        elif action == 'spawn_navigator':
            return await self._spawn_navigator(context)
        elif action == 'create_project':
            return await self._create_project(context)
        elif action == 'coordinate_agents':
            return await self._coordinate_agents(context)
        else:
            return self.create_response(
                success=False,
                message=f"Unknown orchestration action: {action}",
                next_action="analyze_intent"
            )
    
    async def _analyze_intent(self, context: Dict[str, Any]) -> AgentResponse:
        """Analyze user intent and determine required agents."""
        use_case_id = context.get('use_case_id')
        
        if not use_case_id:
            return self.create_response(
                success=False,
                message="No use case provided for analysis",
                next_action="error"
            )
        
        # Retrieve use case
        use_case = await self.storage.get_item('use_cases', use_case_id, UseCase)
        if not use_case:
            return self.create_response(
                success=False,
                message=f"Use case {use_case_id} not found",
                next_action="error"
            )
        
        # Analyze intent and determine required agents
        analysis = await self._perform_intent_analysis(use_case)
        
        # Log analysis activity
        activity = self.log_activity(
            action="intent_analysis",
            summary=f"Analyzed use case {use_case_id}: {analysis['intent_type']}"
        )
        
        return self.create_response(
            success=True,
            message=f"Intent analysis complete. Identified: {analysis['intent_type']}",
            data={
                'use_case_id': use_case_id,
                'analysis': analysis,
                'activity_log': activity.model_dump(),
                'required_agents': analysis['required_agents']
            },
            next_action='spawn_agents'
        )
    
    async def _perform_intent_analysis(self, use_case: UseCase) -> Dict[str, Any]:
        """Perform detailed intent analysis on the use case."""
        analysis = {
            'intent_type': 'resource_discovery',
            'complexity_level': 'medium',
            'required_agents': ['NavigatorAgent', 'ArchivistAgent'],
            'priority': 'normal',
            'estimated_effort': 'low',
            'special_requirements': []
        }
        
        # Analyze description for complexity indicators
        description_lower = use_case.description.lower()
        
        # Determine complexity
        complexity_indicators = {
            'high': ['enterprise', 'scale', 'production', 'mission-critical', 'compliance'],
            'medium': ['integration', 'custom', 'solution', 'multiple'],
            'low': ['demo', 'proof', 'prototype', 'simple']
        }
        
        for level, indicators in complexity_indicators.items():
            if any(indicator in description_lower for indicator in indicators):
                analysis['complexity_level'] = level
                break
        
        # Determine priority based on timeline
        if use_case.project_constraints.timeline:
            timeline_lower = use_case.project_constraints.timeline.lower()
            if any(urgent in timeline_lower for urgent in ['urgent', 'asap', 'immediate']):
                analysis['priority'] = 'high'
            elif any(quick in timeline_lower for quick in ['week', 'days']):
                analysis['priority'] = 'medium'
        
        # Determine required agents based on use case characteristics
        agents = ['NavigatorAgent', 'ArchivistAgent']  # Always needed
        
        # Add specialized agents based on requirements
        if use_case.project_constraints.compliance_requirements:
            agents.append('ComplianceAgent')
            analysis['special_requirements'].append('compliance_review')
        
        if use_case.project_constraints.budget:
            agents.append('CostAgent')
            analysis['special_requirements'].append('cost_analysis')
        
        if 'infrastructure' in description_lower or 'deployment' in description_lower:
            agents.append('InfraAgent')
            analysis['special_requirements'].append('infrastructure_planning')
        
        if analysis['complexity_level'] == 'high':
            agents.append('ResearchAgent')
            analysis['special_requirements'].append('precedent_research')
        
        analysis['required_agents'] = agents
        
        # Adjust effort estimate
        if analysis['complexity_level'] == 'high':
            analysis['estimated_effort'] = 'high'
        elif len(agents) > 3:
            analysis['estimated_effort'] = 'medium'
        
        return analysis
    
    async def _spawn_navigator(self, context: Dict[str, Any]) -> AgentResponse:
        """Spawn Navigator Agent to handle resource matching."""
        use_case_id = context.get('use_case_id')
        analysis = context.get('analysis', {})
        
        # Import here to avoid circular imports
        from agents.embassy_navigator_agent import NavigatorAgent
        
        # Create navigator agent
        navigator = NavigatorAgent()
        
        # Prepare navigator context
        navigator_context = {
            'action': 'search_resources',
            'use_case_id': use_case_id,
            'analysis': analysis,
            'orchestrator_id': self.name
        }
        
        # Execute navigator agent
        try:
            navigator_response = await navigator.process(navigator_context)
            
            if navigator_response.success:
                # Log spawning activity
                activity = self.log_activity(
                    action="agent_spawned",
                    summary=f"Successfully spawned NavigatorAgent for use case {use_case_id}"
                )
                
                return self.create_response(
                    success=True,
                    message="Navigator Agent completed resource matching",
                    data={
                        'navigator_response': navigator_response.model_dump(),
                        'activity_log': activity.model_dump()
                    },
                    next_action='process_navigation_results'
                )
            else:
                return self.create_response(
                    success=False,
                    message=f"Navigator Agent failed: {navigator_response.message}",
                    next_action='error'
                )
                
        except Exception as e:
            self.logger.error(f"Error spawning NavigatorAgent: {str(e)}")
            return self.create_response(
                success=False,
                message=f"Failed to spawn Navigator Agent: {str(e)}",
                next_action='error'
            )
    
    async def _create_project(self, context: Dict[str, Any]) -> AgentResponse:
        """Create a TechHub project from the use case and matches."""
        use_case_id = context.get('use_case_id')
        resource_matches = context.get('resource_matches', [])
        
        if not use_case_id:
            return self.create_response(
                success=False,
                message="No use case ID provided for project creation",
                next_action='error'
            )
        
        # Get the use case
        use_case = await self.storage.get_item('use_cases', use_case_id, UseCase)
        if not use_case:
            return self.create_response(
                success=False,
                message=f"Use case {use_case_id} not found",
                next_action='error'
            )
        
        # Create TechHub project
        project = TechHubProject(
            use_case_id=use_case_id,
            title=use_case.title,
            current_phase="resource_matching",
            created_by=use_case.created_by,
            status_notes=f"Project created from use case. Found {len(resource_matches)} matching resources."
        )
        
        # Add initial activity log
        initial_activity = AgentActivityLog(
            agent=self.name,
            action="project_created",
            summary=f"Created project from use case {use_case_id}"
        )
        project.agent_activity_log.append(initial_activity)
        
        # Store the project
        try:
            await self.storage.create_item('projects', project)
            
            # Log orchestrator activity
            activity = self.log_activity(
                action="project_created",
                summary=f"Created TechHub project {project.project_id} from use case {use_case_id}"
            )
            
            return self.create_response(
                success=True,
                message=f"Successfully created TechHub project: {project.title}",
                data={
                    'project_id': project.project_id,
                    'project': project.model_dump(),
                    'activity_log': activity.model_dump()
                },
                next_action='project_created'
            )
            
        except Exception as e:
            self.logger.error(f"Error creating project: {str(e)}")
            return self.create_response(
                success=False,
                message=f"Failed to create project: {str(e)}",
                next_action='error'
            )
    
    async def _coordinate_agents(self, context: Dict[str, Any]) -> AgentResponse:
        """Coordinate multiple agents for complex workflows."""
        required_agents = context.get('required_agents', [])
        use_case_id = context.get('use_case_id')
        
        if not required_agents:
            return self.create_response(
                success=False,
                message="No agents specified for coordination",
                next_action='error'
            )
        
        coordination_results = []
        
        # Execute agents in appropriate order
        agent_order = self._determine_agent_execution_order(required_agents)
        
        for agent_name in agent_order:
            try:
                result = await self._execute_agent(agent_name, context)
                coordination_results.append({
                    'agent': agent_name,
                    'success': result.success,
                    'message': result.message,
                    'data': result.data
                })
                
                # If agent failed and it's critical, stop coordination
                if not result.success and agent_name in ['NavigatorAgent', 'ArchivistAgent']:
                    break
                    
                # Update context with agent results for next agent
                if result.data:
                    context.update(result.data)
                    
            except Exception as e:
                self.logger.error(f"Error executing agent {agent_name}: {str(e)}")
                coordination_results.append({
                    'agent': agent_name,
                    'success': False,
                    'message': f"Execution failed: {str(e)}",
                    'data': None
                })
        
        # Determine overall success
        successful_agents = [r for r in coordination_results if r['success']]
        overall_success = len(successful_agents) >= len(required_agents) // 2  # At least half successful
        
        # Log coordination activity
        activity = self.log_activity(
            action="agent_coordination",
            summary=f"Coordinated {len(required_agents)} agents for use case {use_case_id}. Success: {len(successful_agents)}/{len(required_agents)}"
        )
        
        return self.create_response(
            success=overall_success,
            message=f"Agent coordination completed. {len(successful_agents)}/{len(required_agents)} agents succeeded.",
            data={
                'coordination_results': coordination_results,
                'activity_log': activity.model_dump(),
                'successful_agents': len(successful_agents),
                'total_agents': len(required_agents)
            },
            next_action='coordination_complete'
        )
    
    def _determine_agent_execution_order(self, required_agents: List[str]) -> List[str]:
        """Determine the optimal execution order for agents."""
        # Define agent dependencies and priorities
        priorities = {
            'NavigatorAgent': 1,      # Must run first to find resources
            'ResearchAgent': 2,       # Should run early for context
            'ArchivistAgent': 9,      # Should run last to log everything
            'ComplianceAgent': 3,     # Run after navigator but before cost
            'CostAgent': 4,           # Run after compliance
            'InfraAgent': 5,          # Run after basic analysis
        }
        
        # Sort agents by priority, keeping unknown agents in middle
        ordered_agents = sorted(
            required_agents,
            key=lambda x: priorities.get(x, 5)
        )
        
        return ordered_agents
    
    async def _execute_agent(self, agent_name: str, context: Dict[str, Any]) -> AgentResponse:
        """Execute a specific agent with given context."""
        # Import agents dynamically to avoid circular imports
        agent_classes = {
            'NavigatorAgent': 'agents.navigator_agent.NavigatorAgent',
            'ArchivistAgent': 'agents.archivist_agent.ArchivistAgent',
            # Add other agents as they're implemented
        }
        
        if agent_name not in agent_classes:
            return self.create_response(
                success=False,
                message=f"Agent {agent_name} not implemented yet",
                next_action='error'
            )
        
        # For now, only handle implemented agents
        if agent_name == 'NavigatorAgent':
            from agents.embassy_navigator_agent import NavigatorAgent
            agent = NavigatorAgent()
            return await agent.process(context)
        elif agent_name == 'ArchivistAgent':
            from agents.archivist_agent import ArchivistAgent
            agent = ArchivistAgent()
            return await agent.process(context)
        else:
            # Placeholder for unimplemented agents
            return self.create_response(
                success=True,
                message=f"Agent {agent_name} executed (placeholder)",
                data={'agent_name': agent_name, 'placeholder': True}
            )
    
    async def orchestrate_full_workflow(self, use_case_id: str) -> AgentResponse:
        """Orchestrate the complete workflow from intake to resource matching."""
        try:
            # Step 1: Analyze intent
            analysis_context = {'action': 'analyze_intent', 'use_case_id': use_case_id}
            analysis_result = await self.process(analysis_context)
            
            if not analysis_result.success:
                return analysis_result
            
            # Step 2: Spawn navigator
            navigator_context = {
                'action': 'spawn_navigator',
                'use_case_id': use_case_id,
                'analysis': analysis_result.data.get('analysis')
            }
            navigator_result = await self.process(navigator_context)
            
            if not navigator_result.success:
                return navigator_result
            
            # Step 3: Create project
            project_context = {
                'action': 'create_project',
                'use_case_id': use_case_id,
                'resource_matches': navigator_result.data.get('navigator_response', {}).get('data', {}).get('resource_matches', [])
            }
            project_result = await self.process(project_context)
            
            # Step 4: Archive with ArchivistAgent
            from agents.archivist_agent import ArchivistAgent
            archivist = ArchivistAgent()
            archive_context = {
                'action': 'log_workflow',
                'use_case_id': use_case_id,
                'project_id': project_result.data.get('project_id') if project_result.success else None,
                'workflow_results': {
                    'analysis': analysis_result.data,
                    'navigation': navigator_result.data,
                    'project_creation': project_result.data
                }
            }
            await archivist.process(archive_context)
            
            # Compile final response
            return self.create_response(
                success=True,
                message="Complete workflow orchestration successful",
                data={
                    'use_case_id': use_case_id,
                    'project_id': project_result.data.get('project_id') if project_result.success else None,
                    'resource_matches': navigator_result.data.get('navigator_response', {}).get('data', {}).get('resource_matches', []),
                    'generated_bom': navigator_result.data.get('navigator_response', {}).get('data', {}).get('generated_bom', []),
                    'workflow_complete': True
                },
                next_action='present_results'
            )
            
        except Exception as e:
            self.logger.error(f"Error in full workflow orchestration: {str(e)}")
            return self.create_response(
                success=False,
                message=f"Workflow orchestration failed: {str(e)}",
                next_action='error'
            )
