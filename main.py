"""
AI Embassy Staff - Main Entry Point

This module provides a CLI interface to demonstrate the multi-agent system workflow.
"""

import asyncio
import json
import sys
from typing import Optional
import logging
from datetime import datetime

# Add config import
from config.env_loader import config

# Import agents and models
from agents.embassy_concierge_agent import ConciergeAgent
from agents.embassy_orchestrator_agent import OrchestratorAgent
from agents.embassy_navigator_agent import NavigatorAgent
from agents.archivist_agent import ArchivistAgent
from models.embassy_models import UseCase, ProjectConstraints
from services.embassy_storage import get_storage

# Temporary debug info
print(f"🔍 Debug Info:")
print(f"   Azure configured: {config.is_azure_configured()}")
print(f"   Azure endpoint: {config.AZURE_OPENAI_ENDPOINT}")
print(f"   Deployment name: {config.AZURE_OPENAI_DEPLOYMENT_NAME}")

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("embassy.main")


class EmbassyStaffCLI:
    """CLI interface for the Embassy Staff system."""
    
    def __init__(self):
        self.storage = get_storage()
        self.concierge = ConciergeAgent()
        self.orchestrator = OrchestratorAgent()
        self.navigator = NavigatorAgent()
        self.archivist = ArchivistAgent()
        self.session_id = None
        self.use_case_id = None
        self.project_id = None
        self.user_id = "demo_user"
        self.last_response = None  # Track last response for proper routing
        
    async def run(self):
        """Main CLI loop."""
        # Validate configuration
        warnings = config.validate()
        if warnings:
            print("\n⚠️  Configuration warnings:")
            for warning in warnings:
                print(f"   - {warning}")
            print()
        
        print("\n" + "="*60)
        print("🏛️  Welcome to the NTT DATA TechHub AI Embassy Staff")
        print("="*60)
        print("\nThis is a demonstration of our intelligent multi-agent system")
        print("for capturing use cases and matching them to TechHub resources.\n")
        
        # Start with greeting
        context = {
            'user_name': 'Demo User',
            'user_id': self.user_id
        }
        
        response = await self.concierge.process(context)
        self.session_id = response.data.get('session_id')
        self.last_response = response
        
        print(response.message)
        print("\n" + "-"*60 + "\n")
        
        # Main interaction loop
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    await self._handle_exit()
                    break
                
                # Process user input based on current state
                await self._process_user_input(user_input)
                
            except KeyboardInterrupt:
                await self._handle_exit()
                break
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                print(f"\n❌ An error occurred: {str(e)}")
                print("Let's try again...\n")
    
    async def _process_user_input(self, user_input: str):
        """Process user input based on current context."""
        context = {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'user_input': user_input
        }
        
        # Log interaction
        await self.archivist.process({
            'action': 'log_interaction',
            'session_id': self.session_id,
            'interaction': {
                'agent': 'user',
                'action': 'input',
                'user_input': user_input
            }
        })
        
        # Use the last response's next_action to determine routing
        expected_action = self.last_response.next_action if self.last_response else None
        
        # Add any stored context data
        if self.last_response and self.last_response.data:
            context.update(self.last_response.data)
        
        if expected_action == 'project_choice':
            # Handle NEW/EXISTING choice
            context['action'] = 'project_choice'
            response = await self.concierge.process(context)
            
        elif expected_action == 'intake_form':
            # Handle intake form interaction - this is where the fix is needed
            context['action'] = 'intake_form'
            response = await self.concierge.process(context)
            
        elif expected_action == 'guided_intake_field':
            # Handle guided field input
            context['action'] = 'guided_intake_field'
            response = await self.concierge.process(context)
            
        elif expected_action == 'process_comprehensive':
            # Process comprehensive description
            context['action'] = 'process_comprehensive'
            response = await self.concierge.process(context)
            
        elif expected_action == 'confirm_extraction':
            # Handle confirmation of extracted data
            if user_input.upper() == 'YES':
                context['action'] = 'submit_intake'
                response = await self.concierge.process(context)
                
                # If intake is complete, trigger orchestration
                if response.next_action == 'orchestrate':
                    await self._handle_orchestration()
                    return
            else:
                # Handle edits or additional input
                context['action'] = 'edit_extraction'
                response = await self.concierge.process(context)
        
        elif expected_action == 'handle_resource_selection':
            # Handle post-results actions
            await self._handle_resource_action(user_input)
            return
            
        else:
            # Default to concierge handling with current action
            if not context.get('action'):
                context['action'] = expected_action or 'process_input'
            response = await self.concierge.process(context)
        
        # Store the response for next iteration
        self.last_response = response
        
        # Display response
        print(f"\n🤖 {response.agent_name}: {response.message}")
        print("\n" + "-"*60 + "\n")
        
        # Store response data
        if response.data:
            if response.data.get('use_case_id'):
                self.use_case_id = response.data['use_case_id']
            if response.data.get('project_id'):
                self.project_id = response.data['project_id']
        
        # Handle special next actions
        if response.next_action == 'orchestrate' and response.data.get('ready_for_orchestration'):
            await self._handle_orchestration()
    
    async def _handle_intake_completion(self):
        """Handle completion of intake and trigger orchestration."""
        print("\n🤖 ConciergeAgent: Great! Your intake is complete.")
        print("Now I'll hand you over to our Orchestrator to find matching resources...\n")
        
        # Log intake completion
        await self.archivist.process({
            'action': 'log_interaction',
            'session_id': self.session_id,
            'interaction': {
                'agent': 'ConciergeAgent',
                'action': 'intake_completed',
                'metadata': {'use_case_id': self.use_case_id}
            }
        })
        
        await self._handle_orchestration()
    
    async def _handle_orchestration(self):
        """Handle the orchestration workflow."""
        print("🔄 Starting orchestration workflow...")
        print("  ├─ Analyzing your requirements...")
        
        # Run full orchestration workflow
        start_time = datetime.now()
        
        try:
            orchestration_result = await self.orchestrator.orchestrate_full_workflow(self.use_case_id)
            
            if orchestration_result.success:
                print("  ├─ Searching TechHub resources...")
                print("  ├─ Generating Bill of Materials...")
                print("  └─ Creating project tracking entry...")
                
                # Extract results
                resource_matches = orchestration_result.data.get('resource_matches', [])
                generated_bom = orchestration_result.data.get('generated_bom', [])
                self.project_id = orchestration_result.data.get('project_id')
                
                # Present results
                await self._present_results(resource_matches, generated_bom)
                
                # Log workflow completion
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                await self.archivist.process({
                    'action': 'log_workflow',
                    'use_case_id': self.use_case_id,
                    'project_id': self.project_id,
                    'duration_ms': duration_ms,
                    'workflow_results': orchestration_result.data
                })
                
            else:
                print(f"\n❌ Orchestration failed: {orchestration_result.message}")
                
        except Exception as e:
            logger.error(f"Orchestration error: {str(e)}")
            print(f"\n❌ An error occurred during orchestration: {str(e)}")
    
    async def _present_results(self, resource_matches: list, generated_bom: list):
        """Present the final results to the user."""
        print("\n" + "="*60)
        print("📊 RESULTS")
        print("="*60)
        
        if resource_matches:
            print(f"\n✅ Found {len(resource_matches)} matching resources:\n")
            
            for i, match in enumerate(resource_matches[:5], 1):
                print(f"{i}. {match['title']} ({match['type']})")
                print(f"   Relevance: {match.get('relevance_score', 0):.1%}")
                print(f"   {match['description']}")
                print(f"   Link: {match['link']}\n")
        else:
            print("\n⚠️  No direct matches found in the current catalog.")
            print("   Consider creating a custom solution or consulting with our experts.\n")
        
        if generated_bom:
            print("\n📋 Generated Bill of Materials:")
            print("-" * 40)
            
            for item in generated_bom[:10]:
                required = "Required" if item.get('required', True) else "Optional"
                print(f"• {item['item']} ({item['category']}) - {required}")
            
            if len(generated_bom) > 10:
                print(f"  ... and {len(generated_bom) - 10} more items")
        
        print("\n" + "="*60)
        print(f"🎯 Project ID: {self.project_id}")
        print("="*60)
        
        print("\nWhat would you like to do next?")
        print("- Type 'report' to generate a project summary report")
        print("- Type 'new' to start a new project")
        print("- Type 'exit' to quit\n")
        
        # Update response state for next action
        self.last_response = type('obj', (object,), {
            'next_action': 'handle_resource_selection',
            'data': {'resource_matches': resource_matches, 'generated_bom': generated_bom}
        })
    
    async def _handle_resource_action(self, user_input: str):
        """Handle post-results user actions."""
        if user_input.lower() == 'report':
            # Generate report
            report_response = await self.archivist.process({
                'action': 'generate_report',
                'report_type': 'project_summary',
                'entity_id': self.project_id
            })
            
            if report_response.success:
                report = report_response.data['report']
                print(f"\n📄 Project Summary Report")
                print("="*60)
                print(f"Generated at: {report['generated_at']}")
                print(f"\nProject: {report['project']['title']}")
                print(f"Phase: {report['project']['current_phase']}")
                print(f"Created by: {report['project']['created_by']}")
                print(f"\nUse Case:")
                print(f"  Industry: {report['use_case']['industry']}")
                print(f"  Cloud: {report['use_case']['cloud']}")
                print(f"\nActivity Summary:")
                print(f"  Total activities: {report['activity_summary']['total_activities']}")
                print(f"  Agents involved: {', '.join(report['activity_summary']['agents_involved'])}")
                print(f"\nResources:")
                print(f"  Total matches: {report['resources']['total_matches']}")
                print("="*60)
        
        elif user_input.lower() == 'new':
            # Start new project flow
            print("\nStarting a new project...\n")
            self.use_case_id = None
            self.project_id = None
            context = {
                'action': 'greet',
                'user_name': 'Demo User',
                'user_id': self.user_id,
                'session_id': self.session_id
            }
            response = await self.concierge.process(context)
            self.last_response = response
            print(response.message)
        
        print("\n" + "-"*60 + "\n")
    
    async def _handle_exit(self):
        """Handle graceful exit."""
        print("\n" + "="*60)
        
        if self.session_id:
            # Archive session
            await self.archivist.process({
                'action': 'archive_session',
                'session_id': self.session_id
            })
            
            # Generate final report if project exists
            if self.project_id:
                report_response = await self.archivist.process({
                    'action': 'generate_report',
                    'report_type': 'project_summary',
                    'entity_id': self.project_id
                })
                
                if report_response.success:
                    report = report_response.data['report']
                    print(f"\n📄 Project Summary Report")
                    print("-" * 40)
                    print(f"Project: {report['project']['title']}")
                    print(f"Phase: {report['project']['current_phase']}")
                    print(f"Activities: {report['activity_summary']['total_activities']}")
                    print(f"Resources Found: {report['resources']['total_matches']}")
        
        print("\n👋 Thank you for using the AI Embassy Staff!")
        print("   Your session has been archived for future reference.")
        print("="*60 + "\n")
    
    async def demo_mode(self):
        """Run a pre-configured demo with sample data."""
        print("\n🎭 Running in DEMO MODE with pre-configured use case...")
        print("="*60 + "\n")
        
        # Create demo use case
        demo_use_case = UseCase(
            title="AI-Powered Document Processing Solution",
            description="""
            We need to build an AI-powered document processing solution for our finance client.
            The solution should be able to extract data from invoices, receipts, and contracts
            using Azure OpenAI and Azure Form Recognizer. It needs to integrate with their 
            existing SAP system and provide real-time analytics dashboards. The client requires
            GDPR compliance and prefers Azure cloud infrastructure. Timeline is 3 months with
            a budget of approximately $250,000. The solution should handle 10,000+ documents
            per day in production.
            """.strip(),
            industry_vertical="Finance",
            client_name="Demo Finance Corp",
            client_context="Large financial services company processing high volumes of documents",
            cloud_preference="Azure",
            project_constraints=ProjectConstraints(
                budget="$250,000",
                timeline="3 months",
                compliance_requirements=["GDPR", "SOC2"]
            ),
            engagement_stage="Design",
            success_criteria=["Process 10k+ docs/day", "99.9% uptime", "< 2s processing time"],
            resource_type_preference=["Solution", "Component"],
            created_by=self.user_id
        )
        
        # Store the use case
        await self.storage.create_item('use_cases', demo_use_case)
        self.use_case_id = demo_use_case.use_case_id
        
        print("📝 Demo Use Case Created:")
        print(f"   Title: {demo_use_case.title}")
        print(f"   Industry: {demo_use_case.industry_vertical}")
        print(f"   Cloud: {demo_use_case.cloud_preference}")
        print(f"   Timeline: {demo_use_case.project_constraints.timeline}")
        print("\n" + "-"*60 + "\n")
        
        # Run orchestration
        await self._handle_orchestration()
        
        # Wait for user input before exiting
        input("\nPress Enter to exit demo mode...")
        await self._handle_exit()


async def main():
    """Main entry point."""
    cli = EmbassyStaffCLI()
    
    # Check for demo mode
    if len(sys.argv) > 1 and sys.argv[1] == '--demo':
        await cli.demo_mode()
    else:
        await cli.run()


if __name__ == "__main__":
    asyncio.run(main())