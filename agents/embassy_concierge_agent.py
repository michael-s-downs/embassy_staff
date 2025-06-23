"""
Concierge Agent - Handles user interaction, intake forms, and guides the conversation flow.
"""

from typing import Dict, Any, List, Optional
from models.embassy_models import UseCase, ProjectConstraints, AgentResponse, ChatSession
from agents.embassy_base_agent import BaseAgent
from services.embassy_storage import get_storage
import json


class ConciergeAgent(BaseAgent):
    """Agent responsible for user interaction and intake management."""
    
    def __init__(self):
        super().__init__(
            name="ConciergeAgent",
            description="Handles user interaction, intake forms, and conversation flow"
        )
        self.storage = get_storage()
        
        # Intake form template
        self.intake_fields = {
            "title": "Project title or brief name",
            "description": "Business or technical use-case description",
            "industry_vertical": "Industry vertical (e.g., Finance, Healthcare, Retail)",
            "client_name": "Specific client name",
            "client_context": "Client use-case context and background",
            "internal_contacts": "Internal NTT contacts involved (comma-separated)",
            "cloud_preference": "Client cloud choice (Azure, AWS, GCP, Multi-cloud)",
            "budget": "Budget constraints or estimates",
            "timeline": "Expected delivery timeline or deadlines",
            "known_dependencies": "Known dependencies or blockers (comma-separated)",
            "compliance_requirements": "Compliance or security requirements (comma-separated)",
            "engagement_stage": "Stage of engagement (Discovery, Design, Build, Pilot, Production)",
            "success_criteria": "Primary success criteria and goals (comma-separated)",
            "resource_type_preference": "Desired TechHub resource types: Demo, Solution, Component (comma-separated)"
        }
    
    async def process(self, context: Dict[str, Any]) -> AgentResponse:
        """Process user interaction based on context."""
        action = context.get('action', 'greet')
        
        if action == 'greet':
            return await self._handle_greeting(context)
        elif action == 'project_choice':
            return await self._handle_project_choice(context)
        elif action == 'intake_form':
            return await self._handle_intake_form(context)
        elif action == 'submit_intake':
            return await self._handle_intake_submission(context)
        elif action == 'existing_project':
            return await self._handle_existing_project(context)
        else:
            return self.create_response(
                success=False,
                message=f"Unknown action: {action}",
                next_action="greet"
            )
    
    async def _handle_greeting(self, context: Dict[str, Any]) -> AgentResponse:
        """Handle initial user greeting and project type selection."""
        user_name = context.get('user_name', 'there')
        
        # Create or retrieve chat session
        session_id = context.get('session_id')
        user_id = context.get('user_id', 'anonymous')
        
        if not session_id:
            session = ChatSession(user_id=user_id)
            await self.storage.create_item('chat_sessions', session)
            session_id = session.session_id
        
        greeting_message = f"""
Hello {user_name}! 👋 

Welcome to the NTT DATA TechHub Embassy. I'm your Concierge Agent, here to help you navigate our resources and turn your ideas into reality.

To get started, I need to understand what you're working on today:

**Is this a NEW project or an EXISTING project we'll discuss today?**

Please respond with:
- `NEW` - for a brand new project or use case
- `EXISTING` - to continue work on an existing project

I'm standing by to guide you through whichever path you choose!
        """.strip()
        
        return self.create_response(
            success=True,
            message=greeting_message,
            data={
                'session_id': session_id,
                'awaiting_input': 'project_choice',
                'valid_options': ['NEW', 'EXISTING']
            },
            next_action='project_choice'
        )
    
    async def _handle_project_choice(self, context: Dict[str, Any]) -> AgentResponse:
        """Handle user's choice between new or existing project."""
        choice = context.get('user_input', '').upper().strip()
        
        if choice == 'NEW':
            return await self._present_intake_form(context)
        elif choice == 'EXISTING':
            return await self._handle_existing_project_selection(context)
        else:
            return self.create_response(
                success=False,
                message="I didn't understand that choice. Please respond with 'NEW' for a new project or 'EXISTING' for an existing project.",
                data={'valid_options': ['NEW', 'EXISTING']},
                next_action='project_choice'
            )
    
    async def _present_intake_form(self, context: Dict[str, Any]) -> AgentResponse:
        """Present the intake form for a new project."""
        form_message = """
Perfect! Let's capture the details for your new project. I'll guide you through our intake form - don't worry about having all the details perfect right now. We can fill in what you know and refine the rest as we go.

**Project Intake Form**

I'll ask you about each field one by one, or you can provide a comprehensive description and I'll help structure it. Here's what we'll cover:

📋 **Core Information:**
- Project title and description
- Industry vertical and client context
- Internal contacts and stakeholders

🔧 **Technical Details:**
- Cloud preferences
- Resource type preferences (Demos, Solutions, Components)
- Known dependencies

📅 **Project Constraints:**
- Budget considerations
- Timeline and deadlines
- Compliance requirements

🎯 **Success Criteria:**
- Engagement stage
- Primary goals and success metrics

Would you like to:
1. **Fill out fields one by one** (guided approach)
2. **Provide a comprehensive description** and let me structure it
3. **Upload or paste existing project details** for me to process

Just let me know how you'd prefer to proceed!
        """.strip()
        
        return self.create_response(
            success=True,
            message=form_message,
            data={
                'form_fields': self.intake_fields,
                'intake_mode': 'ready',
                'options': ['guided', 'comprehensive', 'upload']
            },
            next_action='intake_form'
        )
    
    async def _handle_intake_form(self, context: Dict[str, Any]) -> AgentResponse:
        """Handle intake form interaction."""
        user_input = context.get('user_input', '').strip().lower()
        
        if user_input in ['1', 'guided', 'guide', 'one by one']:
            return await self._start_guided_intake(context)
        elif user_input in ['2', 'comprehensive', 'description', 'describe']:
            return await self._start_comprehensive_intake(context)
        elif user_input in ['3', 'upload', 'paste', 'existing']:
            return await self._start_upload_intake(context)
        else:
            # Try to parse as comprehensive input
            return await self._process_comprehensive_input(context)
    
    async def _start_guided_intake(self, context: Dict[str, Any]) -> AgentResponse:
        """Start guided field-by-field intake."""
        first_field = list(self.intake_fields.keys())[0]
        field_description = self.intake_fields[first_field]
        
        message = f"""
Great! Let's go through this step by step.

**Field 1 of {len(self.intake_fields)}: {first_field.replace('_', ' ').title()}**

{field_description}

Please provide your answer, or type 'skip' if you don't have this information yet.
        """.strip()
        
        return self.create_response(
            success=True,
            message=message,
            data={
                'guided_mode': True,
                'current_field': first_field,
                'field_index': 0,
                'collected_data': {}
            },
            next_action='guided_intake_field'
        )
    
    async def _start_comprehensive_intake(self, context: Dict[str, Any]) -> AgentResponse:
        """Start comprehensive description intake."""
        message = """
Perfect! Please provide a comprehensive description of your project. Include as much detail as you can about:

- What you're trying to build or solve
- Who the client is and their industry
- Technical requirements or preferences
- Timeline and constraints
- Success criteria

I'll analyze your description and structure it into our intake form, then ask for any missing details.

Go ahead and share your project details:
        """.strip()
        
        return self.create_response(
            success=True,
            message=message,
            data={'comprehensive_mode': True},
            next_action='process_comprehensive'
        )
    
    async def _process_comprehensive_input(self, context: Dict[str, Any]) -> AgentResponse:
        """Process comprehensive project description and extract structured data."""
        description = context.get('user_input', '')
        user_id = context.get('user_id', 'anonymous')
        
        if len(description.strip()) < 20:
            return self.create_response(
                success=False,
                message="That description seems quite brief. Could you provide more details about your project? The more information you share, the better I can help match you with relevant resources.",
                next_action='process_comprehensive'
            )
        
        # Extract structured data from description (simplified AI parsing simulation)
        extracted_data = await self._extract_use_case_data(description, user_id)
        
        # Create UseCase object
        try:
            use_case = UseCase(**extracted_data)
            await self.storage.create_item('use_cases', use_case)
            
            # Format the extracted data for user review
            formatted_data = self._format_extracted_data(extracted_data)
            
            message = f"""
Excellent! I've analyzed your description and extracted the following structured information:

{formatted_data}

**Does this look accurate?** 

You can:
- Type `YES` to proceed with this information
- Type `EDIT [field_name]` to modify specific fields (e.g., "EDIT budget")
- Type `ADD [field_name]` to add missing information
- Provide additional details and I'll incorporate them

What would you like to do?
            """.strip()
            
            return self.create_response(
                success=True,
                message=message,
                data={
                    'use_case_id': use_case.use_case_id,
                    'extracted_data': extracted_data,
                    'awaiting_confirmation': True
                },
                next_action='confirm_extraction'
            )
            
        except Exception as e:
            self.logger.error(f"Error creating use case: {str(e)}")
            return self.create_response(
                success=False,
                message="I had trouble processing your description. Could you try providing the information in a different format?",
                next_action='intake_form'
            )
    
    async def _extract_use_case_data(self, description: str, user_id: str) -> Dict[str, Any]:
        """Extract structured data from user description (simplified AI parsing simulation)."""
        # This is a simplified simulation - in production, this would use LLM parsing
        
        # Default structure
        extracted = {
            'title': 'New Project',
            'description': description,
            'created_by': user_id,
            'project_constraints': {},
            'internal_contacts': [],
            'success_criteria': [],
            'resource_type_preference': []
        }
        
        # Simple keyword-based extraction (in production, use proper NLP/LLM)
        description_lower = description.lower()
        
        # Extract industry
        industries = ['finance', 'healthcare', 'retail', 'manufacturing', 'education', 'government']
        for industry in industries:
            if industry in description_lower:
                extracted['industry_vertical'] = industry.title()
                break
        
        # Extract cloud preferences
        if 'azure' in description_lower:
            extracted['cloud_preference'] = 'Azure'
        elif 'aws' in description_lower:
            extracted['cloud_preference'] = 'AWS'
        elif 'gcp' in description_lower or 'google cloud' in description_lower:
            extracted['cloud_preference'] = 'GCP'
        
        # Extract resource types
        if 'demo' in description_lower:
            extracted['resource_type_preference'].append('Demo')
        if 'solution' in description_lower:
            extracted['resource_type_preference'].append('Solution')
        if 'component' in description_lower:
            extracted['resource_type_preference'].append('Component')
        
        # Extract timeline keywords
        timeline_keywords = ['urgent', 'asap', 'month', 'week', 'quarter', 'deadline']
        for keyword in timeline_keywords:
            if keyword in description_lower:
                extracted['project_constraints']['timeline'] = f"Contains timeline reference: {keyword}"
                break
        
        # Try to extract a title from first sentence
        sentences = description.split('.')
        if sentences:
            first_sentence = sentences[0].strip()
            if len(first_sentence) < 100:  # Reasonable title length
                extracted['title'] = first_sentence
        
        return extracted
    
    def _format_extracted_data(self, data: Dict[str, Any]) -> str:
        """Format extracted data for user review."""
        lines = []
        
        lines.append(f"📝 **Title:** {data.get('title', 'Not specified')}")
        lines.append(f"📋 **Description:** {data.get('description', 'Not specified')[:200]}...")
        
        if data.get('industry_vertical'):
            lines.append(f"🏢 **Industry:** {data['industry_vertical']}")
        
        if data.get('cloud_preference'):
            lines.append(f"☁️ **Cloud Preference:** {data['cloud_preference']}")
        
        if data.get('resource_type_preference'):
            lines.append(f"🛠️ **Resource Types:** {', '.join(data['resource_type_preference'])}")
        
        constraints = data.get('project_constraints', {})
        if constraints:
            lines.append("⏰ **Constraints:**")
            for key, value in constraints.items():
                lines.append(f"  - {key.replace('_', ' ').title()}: {value}")
        
        return '\n'.join(lines)
    
    async def _handle_intake_submission(self, context: Dict[str, Any]) -> AgentResponse:
        """Handle final intake form submission."""
        use_case_id = context.get('use_case_id')
        
        if not use_case_id:
            return self.create_response(
                success=False,
                message="I couldn't find the use case information. Let's start over.",
                next_action='greet'
            )
        
        # Log the activity
        activity = self.log_activity(
            action="intake_completed",
            summary=f"Completed intake for use case {use_case_id}"
        )
        
        success_message = """
🎉 **Intake Complete!**

Perfect! I've captured all your project information. Now I'm going to hand you over to our Orchestrator who will:

1. **Analyze your requirements** and determine the best approach
2. **Spawn our Navigator Agent** to search our TechHub resources
3. **Generate a Bill of Materials (BOM)** with recommended resources
4. **Create a project tracking entry** for lifecycle management

This should only take a moment. Please hold while I coordinate with the team...
        """.strip()
        
        return self.create_response(
            success=True,
            message=success_message,
            data={
                'use_case_id': use_case_id,
                'activity_log': activity.model_dump(),
                'ready_for_orchestration': True
            },
            next_action='orchestrate'
        )
    
    async def _handle_existing_project_selection(self, context: Dict[str, Any]) -> AgentResponse:
        """Handle selection of existing project."""
        user_id = context.get('user_id', 'anonymous')
        
        # Get user's projects
        projects = await self.storage.get_user_projects(user_id)
        
        if not projects:
            message = """
I don't see any existing projects for your account yet. 

Would you like to:
1. **Start a NEW project** instead
2. **Search for projects** you might be collaborating on
3. **Contact support** if you think this is an error

What would you prefer?
            """.strip()
            
            return self.create_response(
                success=True,
                message=message,
                data={'no_existing_projects': True},
                next_action='handle_no_projects'
            )
        
        # Format project list
        project_list = [
            f"{i+1}. **{project.title}** (Stage: {project.current_phase}) - Last updated: {project.last_updated.strftime('%Y-%m-%d')}"
            for i, project in enumerate(projects[:10])  # Limit to 10 most recent
        ]
        
        message = f"""
Here are your existing projects:

{chr(10).join(project_list)}

Please select a project by number (1-{len(project_list)}), or type:
- `MORE` to see additional projects
- `SEARCH [keyword]` to search your projects
- `NEW` to start a new project instead

Which project would you like to work on?
        """.strip()
        
        return self.create_response(
            success=True,
            message=message,
            data={
                'projects': [p.model_dump() for p in projects],
                'awaiting_selection': True
            },
            next_action='select_existing_project'
        )
    
    async def present_resource_matches(self, context: Dict[str, Any]) -> AgentResponse:
        """Present resource matching results to the user."""
        matches = context.get('resource_matches', [])
        bom = context.get('generated_bom', [])
        
        if not matches:
            message = """
I've completed the analysis of your requirements, but I wasn't able to find any direct matches in our current TechHub catalog.

However, this doesn't mean we can't help! Here are your options:

1. **Broaden the search** - I can look for related resources
2. **Create a custom solution** - We can start building something new
3. **Connect with experts** - I can route you to relevant internal teams
4. **Schedule a consultation** - Meet with our solution architects

What would you like to do next?
            """.strip()
            
            return self.create_response(
                success=True,
                message=message,
                data={'no_matches': True},
                next_action='handle_no_matches'
            )
        
        # Format matches
        match_list = []
        for i, match in enumerate(matches[:5], 1):  # Top 5 matches
            match_list.append(f"""
{i}. **{match['title']}** ({match['type']})
   📊 Relevance: {match.get('relevance_score', 0):.1%}
   📝 {match['description']}
   🔗 [View Resource]({match['link']})
            """.strip())
        
        # Format BOM if available
        bom_section = ""
        if bom:
            bom_items = [f"   • {item['item']} ({item['category']})" for item in bom[:10]]
            bom_section = f"""

**📋 Generated Bill of Materials:**
{chr(10).join(bom_items)}
{f"   ... and {len(bom) - 10} more items" if len(bom) > 10 else ""}
            """.strip()
        
        message = f"""
🎯 **Great news!** I found {len(matches)} matching resources for your project:

{chr(10).join(match_list)}

{bom_section}

**Next Steps:**
- Type the number of any resource to learn more
- Type `ALL` to get detailed information about all matches
- Type `BOM` to see the complete Bill of Materials
- Type `PROJECT` to create a tracked project from these matches
- Type `REFINE` to adjust the search criteria

What would you like to do?
        """.strip()
        
        return self.create_response(
            success=True,
            message=message,
            data={
                'resource_matches': matches,
                'generated_bom': bom,
                'awaiting_action': True
            },
            next_action='handle_resource_selection'
        )
