"""
Database engine configuration and session management.
Provides database connection and session factories.
"""
import os
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel
from contextlib import contextmanager

from .models import ModelRegistry


class DatabaseConfig:
    """Database configuration and connection management."""
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./rssbot.db")
        self._engine = None
        
    @property
    def engine(self) -> Engine:
        """Get or create database engine."""
        if self._engine is None:
            # Configure engine based on database type
            if self.database_url.startswith("sqlite"):
                self._engine = create_engine(
                    self.database_url,
                    echo=os.getenv("LOG_LEVEL", "INFO") == "DEBUG",
                    connect_args={"check_same_thread": False}
                )
                # Enable foreign key constraints for SQLite
                @event.listens_for(self._engine, "connect")
                def set_sqlite_pragma(dbapi_connection, connection_record):
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.close()
            else:
                self._engine = create_engine(
                    self.database_url,
                    echo=os.getenv("LOG_LEVEL", "INFO") == "DEBUG",
                    pool_pre_ping=True
                )
        return self._engine
    
    def create_tables(self):
        """Create all database tables."""
        SQLModel.metadata.create_all(self.engine)
    
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session generator."""
        with Session(self.engine) as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
    
    @contextmanager
    def get_session_context(self):
        """Get database session context manager."""
        session = Session(self.engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_model_info(self) -> dict:
        """Get information about registered models."""
        models = ModelRegistry.get_models()
        info = {}
        
        for name, model_class in models.items():
            # Get model fields
            fields = {}
            relationships = []
            
            if hasattr(model_class, '__fields__'):
                for field_name, field_info in model_class.__fields__.items():
                    fields[field_name] = {
                        'type': str(field_info.type_),
                        'required': field_info.is_required(),
                        'default': getattr(field_info, 'default', None)
                    }
            
            # Get relationships
            if hasattr(model_class, '__sqlmodel_relationships__'):
                relationships = list(model_class.__sqlmodel_relationships__.keys())
            
            info[name] = {
                'fields': fields,
                'relationships': relationships,
                'table_name': getattr(model_class, '__tablename__', None)
            }
        
        return info
    
    def get_table_info(self) -> dict:
        """Get database table information."""
        tables = {}
        inspector = self.engine.dialect.inspector(self.engine)
        
        for table_name in inspector.get_table_names():
            columns = []
            primary_keys = []
            foreign_keys = []
            
            # Get column information
            for column in inspector.get_columns(table_name):
                columns.append(column['name'])
                
            # Get primary key information
            pk_constraint = inspector.get_pk_constraint(table_name)
            if pk_constraint:
                primary_keys = pk_constraint.get('constrained_columns', [])
            
            # Get foreign key information  
            for fk in inspector.get_foreign_keys(table_name):
                foreign_keys.extend(fk.get('constrained_columns', []))
            
            tables[table_name] = {
                'columns': columns,
                'primary_key': primary_keys,
                'foreign_keys': foreign_keys
            }
        
        return tables


# Global database configuration instance
db_config = DatabaseConfig()