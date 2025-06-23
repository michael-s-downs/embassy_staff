"""
Configuration management for AI Embassy Staff
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Central configuration class"""
    
    # Azure OpenAI
    AZURE_OPENAI_API_KEY: str = os.getenv('AZURE_OPENAI_API_KEY', '')
    AZURE_OPENAI_ENDPOINT: str = os.getenv('AZURE_OPENAI_ENDPOINT', '')
    AZURE_OPENAI_DEPLOYMENT_NAME: str = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o')
    AZURE_OPENAI_API_VERSION: str = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview') # Default to latest preview version
    
    # Azure Cognitive Search
    AZURE_SEARCH_ENDPOINT: str = os.getenv('AZURE_SEARCH_ENDPOINT', '')
    AZURE_SEARCH_API_KEY: str = os.getenv('AZURE_SEARCH_API_KEY', '')
    AZURE_SEARCH_INDEX_NAME: str = os.getenv('AZURE_SEARCH_INDEX_NAME', 'techhub-resources')
    AZURE_SEARCH_SEMANTIC_CONFIG: str = os.getenv('AZURE_SEARCH_SEMANTIC_CONFIG', '')
    
    # Storage
    STORAGE_TYPE: str = os.getenv('STORAGE_TYPE', 'local')
    STORAGE_PATH: str = os.getenv('STORAGE_PATH', './data')
    
    # Cosmos DB
    COSMOS_ENDPOINT: str = os.getenv('COSMOS_ENDPOINT', '')
    COSMOS_KEY: str = os.getenv('COSMOS_KEY', '')
    COSMOS_DATABASE_NAME: str = os.getenv('COSMOS_DATABASE_NAME', 'embassy-staff')
    COSMOS_CONTAINER_PREFIX: str = os.getenv('COSMOS_CONTAINER_PREFIX', 'embassy_')
    
    # Application
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')
    API_HOST: str = os.getenv('API_HOST', '0.0.0.0')
    API_PORT: int = int(os.getenv('API_PORT', '8000'))
    
    # Session
    SESSION_TIMEOUT_MINUTES: int = int(os.getenv('SESSION_TIMEOUT_MINUTES', '30'))
    MAX_CONVERSATION_HISTORY: int = int(os.getenv('MAX_CONVERSATION_HISTORY', '100'))
    
    # Agent Configuration
    ORCHESTRATOR_TIMEOUT_SECONDS: int = int(os.getenv('ORCHESTRATOR_TIMEOUT_SECONDS', '60'))
    NAVIGATOR_MAX_RESULTS: int = int(os.getenv('NAVIGATOR_MAX_RESULTS', '20'))
    ARCHIVIST_RETENTION_DAYS: int = int(os.getenv('ARCHIVIST_RETENTION_DAYS', '90'))
    
    # Feature Flags
    ENABLE_WEBSOCKET: bool = os.getenv('ENABLE_WEBSOCKET', 'true').lower() == 'true'
    ENABLE_BACKGROUND_TASKS: bool = os.getenv('ENABLE_BACKGROUND_TASKS', 'true').lower() == 'true'
    ENABLE_MOCK_CATALOG: bool = os.getenv('ENABLE_MOCK_CATALOG', 'true').lower() == 'true'
    
    # TechHub API
    TECHHUB_API_URL: str = os.getenv('TECHHUB_API_URL', '')
    TECHHUB_API_KEY: str = os.getenv('TECHHUB_API_KEY', '')
    
    # Application Insights
    APPLICATIONINSIGHTS_CONNECTION_STRING: str = os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING', '')
    
    @classmethod
    def is_azure_configured(cls) -> bool:
        """Check if Azure OpenAI is properly configured"""
        return bool(cls.AZURE_OPENAI_API_KEY and cls.AZURE_OPENAI_ENDPOINT)
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production"""
        return cls.ENVIRONMENT == 'production'
    
    @classmethod
    def validate(cls) -> list[str]:
        """Validate configuration and return list of warnings"""
        warnings = []
        
        if not cls.is_azure_configured():
            warnings.append("Azure OpenAI not configured - AI features will be limited")
        
        if cls.STORAGE_TYPE == 'cosmos' and not (cls.COSMOS_ENDPOINT and cls.COSMOS_KEY):
            warnings.append("Cosmos DB selected but credentials missing - falling back to local storage")
            cls.STORAGE_TYPE = 'local'
        
        if not cls.ENABLE_MOCK_CATALOG and not cls.TECHHUB_API_URL:
            warnings.append("Real catalog enabled but TechHub API URL not provided")
        
        return warnings


# Create singleton instance
config = Config()