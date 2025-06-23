"""
Navigator Agent - Searches TechHub resources and generates resource matches and BOMs.
"""

from typing import Dict, Any, List, Optional
from models.embassy_models import UseCase, ResourceMatch, RecommendedResource, BOMItem, AgentResponse
from agents.embassy_base_agent import BaseAgent, MockResourceCatalog
from services.embassy_storage import get_storage
import re
from datetime import datetime


class NavigatorAgent(BaseAgent):
    """Agent responsible for resource discovery and matching."""
    
    def __init__(self):
        super().__init__(
            name="NavigatorAgent",
            description="Searches TechHub resources and generates resource matches and BOMs"
        )
        self.storage = get_storage()
        self.resource_catalog = MockResourceCatalog()
        
        # Keyword mapping for better matching
        self.keyword_mapping = {
            'ai': ['artificial intelligence', 'machine learning', 'ml', 'openai', 'cognitive'],
            'chat': ['chatbot', 'conversation', 'dialogue', 'messaging'],
            'document': ['doc', 'pdf', 'file', 'paper', 'text'],
            'analytics': ['analysis', 'reporting', 'insights', 'metrics', 'dashboard'],
            'iot': ['internet of things', 'sensors', 'devices', 'telemetry'],
            'auth': ['authentication', 'authorization', 'security', 'login'],
            'cloud': ['azure', 'aws', 'gcp', 'infrastructure']
        }
    
    async def process(self, context: Dict[str, Any]) -> AgentResponse:
        """Process resource matching requests."""
        action = context.get('action', 'search_resources')
        
        if action == 'search_resources':
            return await self._search_resources(context)
        elif action == 'generate_bom':
            return await self._generate_bom(context)
        else:
            return self.create_response(
                success=False,
                message=f"Unknown navigation action: {action}",
                next_action="error"
            )
    
    async def _search_resources(self, context: Dict[str, Any]) -> AgentResponse:
        """Search for matching resources based on use case."""
        use_case_id = context.get('use_case_id')
        
        if not use_case_id:
            return self.create_response(
                success=False,
                message="No use case ID provided for resource search",
                next_action="error"
            )
        
        # Get the use case
        use_case = await self.storage.get_item('use_cases', use_case_id, UseCase)
        if not use_case:
            return self.create_response(
                success=False,
                message=f"Use case {use_case_id} not found",
                next_action="error"
            )
        
        # Extract search terms from use case
        search_terms = self._extract_search_terms(use_case)
        
        # Search resources
        matching_resources = self._search_catalog(search_terms, use_case)
        
        # Score and rank resources
        scored_resources = self._score_resources(matching_resources, use_case)
        
        # Create ResourceMatch object
        resource_match = ResourceMatch(
            use_case_id=use_case_id,
            matched_by=self.name,
            recommended_resources=[
                RecommendedResource(
                    resource_id=r['resource']['resource_id'],
                    title=r['resource']['title'],
                    type=r['resource']['type'],
                    relevance_score=r['score'],
                    description=r['resource']['description'],
                    link=r['resource']['link']
                )
                for r in scored_resources[:10]  # Top 10 matches
            ],
            notes=f"Found {len(matching_resources)} potential matches, returning top {min(10, len(scored_resources))}"
        )
        
        # Generate BOM
        bom_items = self._generate_bom_items(scored_resources, use_case)
        resource_match.generated_bom = bom_items
        
        # Store the match
        try:
            await self.storage.create_item('resource_matches', resource_match)
            
            # Log activity
            activity = self.log_activity(
                action="resource_search_completed",
                summary=f"Found {len(resource_match.recommended_resources)} matches for use case {use_case_id}"
            )
            
            return self.create_response(
                success=True,
                message=f"Successfully matched {len(resource_match.recommended_resources)} resources",
                data={
                    'match_id': resource_match.match_id,
                    'resource_matches': [r.model_dump() for r in resource_match.recommended_resources],
                    'generated_bom': [b.model_dump() for b in resource_match.generated_bom],
                    'activity_log': activity.model_dump()
                },
                next_action='present_matches'
            )
            
        except Exception as e:
            self.logger.error(f"Error storing resource match: {str(e)}")
            return self.create_response(
                success=False,
                message=f"Failed to store resource match: {str(e)}",
                next_action='error'
            )
    
    def _extract_search_terms(self, use_case: UseCase) -> Dict[str, List[str]]:
        """Extract search terms from use case."""
        terms = {
            'keywords': [],
            'resource_types': use_case.resource_type_preference,
            'industry': use_case.industry_vertical,
            'cloud': use_case.cloud_preference
        }
        
        # Extract keywords from description
        description_lower = use_case.description.lower()
        
        # Check for keyword mappings
        for base_term, variations in self.keyword_mapping.items():
            if base_term in description_lower or any(v in description_lower for v in variations):
                terms['keywords'].append(base_term)
        
        # Extract additional keywords from title and description
        words = re.findall(r'\b\w+\b', use_case.title + ' ' + use_case.description)
        tech_keywords = ['api', 'database', 'web', 'mobile', 'integration', 'platform', 
                        'service', 'application', 'system', 'solution', 'framework']
        
        for word in words:
            if word.lower() in tech_keywords and word.lower() not in terms['keywords']:
                terms['keywords'].append(word.lower())
        
        return terms
    
    def _search_catalog(self, search_terms: Dict[str, List[str]], use_case: UseCase) -> List[Dict[str, Any]]:
        """Search the resource catalog."""
        all_matches = []
        
        # Search by keywords
        for keyword in search_terms['keywords']:
            matches = self.resource_catalog.search_resources(query=keyword)
            for match in matches:
                if match not in all_matches:
                    all_matches.append(match)
        
        # Search by resource type
        for res_type in search_terms['resource_types']:
            matches = self.resource_catalog.search_resources(resource_type=res_type)
            for match in matches:
                if match not in all_matches:
                    all_matches.append(match)
        
        # Search by industry
        if search_terms['industry']:
            matches = self.resource_catalog.search_resources(industry=search_terms['industry'])
            for match in matches:
                if match not in all_matches:
                    all_matches.append(match)
        
        return all_matches
    
    def _score_resources(self, resources: List[Dict[str, Any]], use_case: UseCase) -> List[Dict[str, Any]]:
        """Score and rank resources based on relevance."""
        scored_resources = []
        
        for resource in resources:
            score = 0.0
            
            # Score based on title match
            if any(word in resource['title'].lower() for word in use_case.title.lower().split()):
                score += 0.3
            
            # Score based on description match
            use_case_words = set(use_case.description.lower().split())
            resource_words = set(resource['description'].lower().split())
            overlap = len(use_case_words.intersection(resource_words))
            score += min(0.3, overlap * 0.02)
            
            # Score based on resource type preference
            if resource['type'] in use_case.resource_type_preference:
                score += 0.2
            
            # Score based on industry match
            if use_case.industry_vertical and use_case.industry_vertical.lower() in [i.lower() for i in resource['industry']]:
                score += 0.15
            
            # Score based on tag matches
            use_case_tags = self._extract_search_terms(use_case)['keywords']
            tag_matches = sum(1 for tag in resource['tags'] if tag in use_case_tags)
            score += min(0.25, tag_matches * 0.05)
            
            # Ensure score is between 0 and 1
            score = min(1.0, max(0.0, score))
            
            scored_resources.append({
                'resource': resource,
                'score': score
            })
        
        # Sort by score descending
        scored_resources.sort(key=lambda x: x['score'], reverse=True)
        
        return scored_resources
    
    def _generate_bom_items(self, scored_resources: List[Dict[str, Any]], use_case: UseCase) -> List[BOMItem]:
        """Generate Bill of Materials based on matched resources and use case."""
        bom_items = []
        
        # Add matched resources as BOM items
        for item in scored_resources[:5]:  # Top 5 resources
            resource = item['resource']
            bom_items.append(BOMItem(
                item=resource['title'],
                category=f"TechHub {resource['type']}",
                source="TechHub Catalog",
                required=item['score'] > 0.7  # High relevance = required
            ))
        
        # Add infrastructure requirements based on cloud preference
        if use_case.cloud_preference:
            cloud_items = self._get_cloud_requirements(use_case.cloud_preference)
            bom_items.extend(cloud_items)
        
        # Add compliance-related items
        if use_case.project_constraints.compliance_requirements:
            compliance_items = self._get_compliance_requirements(use_case.project_constraints.compliance_requirements)
            bom_items.extend(compliance_items)
        
        # Add standard project items
        bom_items.extend([
            BOMItem(
                item="Project Management",
                category="Process",
                source="Standard Practice",
                required=True
            ),
            BOMItem(
                item="Technical Documentation",
                category="Deliverable",
                source="Standard Practice",
                required=True
            )
        ])
        
        # Add timeline-specific items
        if use_case.project_constraints.timeline and 'urgent' in use_case.project_constraints.timeline.lower():
            bom_items.append(BOMItem(
                item="Rapid Deployment Framework",
                category="Process",
                source="Best Practice",
                required=True
            ))
        
        return bom_items
    
    def _get_cloud_requirements(self, cloud_preference: str) -> List[BOMItem]:
        """Get cloud-specific BOM items."""
        items = []
        
        if cloud_preference.lower() == 'azure':
            items.extend([
                BOMItem(item="Azure Subscription", category="Infrastructure", source="Azure", required=True),
                BOMItem(item="Azure DevOps", category="Tools", source="Azure", required=True),
                BOMItem(item="Azure Monitor", category="Operations", source="Azure", required=False)
            ])
        elif cloud_preference.lower() == 'aws':
            items.extend([
                BOMItem(item="AWS Account", category="Infrastructure", source="AWS", required=True),
                BOMItem(item="CodePipeline", category="Tools", source="AWS", required=True),
                BOMItem(item="CloudWatch", category="Operations", source="AWS", required=False)
            ])
        elif cloud_preference.lower() == 'gcp':
            items.extend([
                BOMItem(item="GCP Project", category="Infrastructure", source="GCP", required=True),
                BOMItem(item="Cloud Build", category="Tools", source="GCP", required=True),
                BOMItem(item="Cloud Monitoring", category="Operations", source="GCP", required=False)
            ])
        
        return items
    
    def _get_compliance_requirements(self, requirements: List[str]) -> List[BOMItem]:
        """Get compliance-specific BOM items."""
        items = []
        
        for req in requirements:
            req_lower = req.lower()
            if 'gdpr' in req_lower:
                items.append(BOMItem(item="GDPR Compliance Framework", category="Compliance", source="Regulatory", required=True))
            elif 'hipaa' in req_lower:
                items.append(BOMItem(item="HIPAA Compliance Tools", category="Compliance", source="Regulatory", required=True))
            elif 'soc2' in req_lower:
                items.append(BOMItem(item="SOC2 Audit Preparation", category="Compliance", source="Regulatory", required=True))
            elif 'pci' in req_lower:
                items.append(BOMItem(item="PCI-DSS Compliance Suite", category="Compliance", source="Regulatory", required=True))
        
        return items
    
    async def _generate_bom(self, context: Dict[str, Any]) -> AgentResponse:
        """Generate a standalone BOM for a use case."""
        use_case_id = context.get('use_case_id')
        
        if not use_case_id:
            return self.create_response(
                success=False,
                message="No use case ID provided for BOM generation",
                next_action="error"
            )
        
        # Get the use case
        use_case = await self.storage.get_item('use_cases', use_case_id, UseCase)
        if not use_case:
            return self.create_response(
                success=False,
                message=f"Use case {use_case_id} not found",
                next_action="error"
            )
        
        # Generate BOM items
        bom_items = self._generate_bom_items([], use_case)  # Empty resources list for standalone BOM
        
        # Log activity
        activity = self.log_activity(
            action="bom_generated",
            summary=f"Generated BOM with {len(bom_items)} items for use case {use_case_id}"
        )
        
        return self.create_response(
            success=True,
            message=f"Generated BOM with {len(bom_items)} items",
            data={
                'use_case_id': use_case_id,
                'generated_bom': [b.model_dump() for b in bom_items],
                'activity_log': activity.model_dump()
            },
            next_action='bom_complete'
        )
