"""
Storage service for the AI Embassy Staff system.
Provides JSON-based persistence with CosmosDB-style interface for prototyping.
"""

import json
import os
from typing import Dict, Any, List, Optional, Type, TypeVar
from datetime import datetime, timezone
from pathlib import Path
import logging
from models.embassy_models import UseCase, TechHubProject, ResourceMatch, ChatSession
from config.env_loader import config
T = TypeVar('T')

class StorageService:
    """JSON-based storage service with CosmosDB-style interface."""
    
    def __init__(self, storage_path: str = config.STORAGE_PATH):
        """Initialize storage service with specified path."""
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.logger = logging.getLogger("embassy.storage")
        
        # Initialize collection directories
        self.collections = {
            'use_cases': self.storage_path / 'use_cases',
            'projects': self.storage_path / 'projects', 
            'resource_matches': self.storage_path / 'resource_matches',
            'chat_sessions': self.storage_path / 'chat_sessions'
        }
        
        for collection_path in self.collections.values():
            collection_path.mkdir(exist_ok=True)
    
    def _get_file_path(self, collection: str, item_id: str) -> Path:
        """Get file path for a specific item."""
        return self.collections[collection] / f"{item_id}.json"
    
    def _serialize_item(self, item: Any) -> Dict[str, Any]:
        """Serialize item to JSON-compatible format."""
        if hasattr(item, 'model_dump'):
            # Pydantic model
            return item.model_dump(mode='json')
        elif hasattr(item, 'dict'):
            # Pydantic v1 style
            return item.dict()
        else:
            # Assume it's already a dict
            return item
    
    def _deserialize_item(self, data: Dict[str, Any], model_class: Type[T]) -> T:
        """Deserialize JSON data to model instance."""
        if hasattr(model_class, 'model_validate'):
            # Pydantic v2
            return model_class.model_validate(data)
        elif hasattr(model_class, 'parse_obj'):
            # Pydantic v1
            return model_class.parse_obj(data)
        else:
            # Assume it's a dict
            return data
    
    async def create_item(self, collection: str, item: Any) -> str:
        """Create a new item in the specified collection."""
        try:
            item_data = self._serialize_item(item)
            item_id = item_data.get('use_case_id') or item_data.get('project_id') or item_data.get('match_id') or item_data.get('session_id')
            
            if not item_id:
                raise ValueError("Item must have an ID field")
            
            file_path = self._get_file_path(collection, item_id)
            
            # Add metadata
            item_data['_metadata'] = {
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'collection': collection
            }
            
            with open(file_path, 'w') as f:
                json.dump(item_data, f, indent=2, default=str)
            
            self.logger.info(f"Created item {item_id} in collection {collection}")
            return item_id
            
        except Exception as e:
            self.logger.error(f"Error creating item in {collection}: {str(e)}")
            raise
    
    async def get_item(self, collection: str, item_id: str, model_class: Type[T]) -> Optional[T]:
        """Get an item by ID from the specified collection."""
        try:
            file_path = self._get_file_path(collection, item_id)
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Remove metadata before deserializing
            data.pop('_metadata', None)
            
            return self._deserialize_item(data, model_class)
            
        except Exception as e:
            self.logger.error(f"Error getting item {item_id} from {collection}: {str(e)}")
            return None
    
    async def update_item(self, collection: str, item_id: str, item: Any) -> bool:
        """Update an existing item in the specified collection."""
        try:
            file_path = self._get_file_path(collection, item_id)
            
            if not file_path.exists():
                return False
            
            item_data = self._serialize_item(item)
            
            # Preserve creation metadata, update modification time
            existing_metadata = {}
            if file_path.exists():
                with open(file_path, 'r') as f:
                    existing_data = json.load(f)
                    existing_metadata = existing_data.get('_metadata', {})
            
            item_data['_metadata'] = {
                **existing_metadata,
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'collection': collection
            }
            
            with open(file_path, 'w') as f:
                json.dump(item_data, f, indent=2, default=str)
            
            self.logger.info(f"Updated item {item_id} in collection {collection}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating item {item_id} in {collection}: {str(e)}")
            return False
    
    async def delete_item(self, collection: str, item_id: str) -> bool:
        """Delete an item from the specified collection."""
        try:
            file_path = self._get_file_path(collection, item_id)
            
            if not file_path.exists():
                return False
            
            file_path.unlink()
            self.logger.info(f"Deleted item {item_id} from collection {collection}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting item {item_id} from {collection}: {str(e)}")
            return False
    
    async def query_items(self, collection: str, filter_func: Optional[callable] = None, 
                         model_class: Type[T] = dict) -> List[T]:
        """Query items from a collection with optional filtering."""
        try:
            results = []
            collection_path = self.collections[collection]
            
            for file_path in collection_path.glob("*.json"):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Remove metadata before filtering/deserializing
                data.pop('_metadata', None)
                
                if filter_func is None or filter_func(data):
                    if model_class != dict:
                        item = self._deserialize_item(data, model_class)
                    else:
                        item = data
                    results.append(item)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error querying collection {collection}: {str(e)}")
            return []
    
    async def get_user_projects(self, user_id: str) -> List[TechHubProject]:
        """Get all projects for a specific user."""
        def user_filter(data):
            return data.get('created_by') == user_id or user_id in data.get('collaborators', [])
        
        return await self.query_items('projects', user_filter, TechHubProject)
    
    async def get_recent_sessions(self, user_id: str, limit: int = 10) -> List[ChatSession]:
        """Get recent chat sessions for a user."""
        def user_filter(data):
            return data.get('user_id') == user_id
        
        sessions = await self.query_items('chat_sessions', user_filter, ChatSession)
        return sorted(sessions, key=lambda x: x.last_activity, reverse=True)[:limit]
    
    async def get_project_matches(self, project_id: str) -> List[ResourceMatch]:
        """Get all resource matches for a project."""
        use_case = await self.get_item('projects', project_id, TechHubProject)
        if not use_case:
            return []
        
        def match_filter(data):
            return data.get('use_case_id') == use_case.use_case_id
        
        return await self.query_items('resource_matches', match_filter, ResourceMatch)


# Singleton storage instance
_storage_instance = None

def get_storage() -> StorageService:
    """Get the global storage service instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = StorageService()
    return _storage_instance
