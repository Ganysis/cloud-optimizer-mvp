#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cloud Optimizer MVP
db.py - Module d'accès à la base de données
"""

import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

logger = logging.getLogger(__name__)

# Création de la base pour les modèles SQLAlchemy
Base = declarative_base()

# Définition des modèles
class Resource(Base):
    """Modèle représentant une ressource cloud"""
    __tablename__ = 'resources'
    
    id = Column(Integer, primary_key=True)
    cloud_id = Column(String, unique=True, nullable=False)  # ID cloud de la ressource (AWS, Azure, etc.)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # EC2, RDS, S3, etc.
    region = Column(String, nullable=False)
    provider = Column(String, nullable=False)  # AWS, Azure, GCP, etc.
    tags = Column(JSON)
    created_at = Column(DateTime)
    last_updated = Column(DateTime)
    
    # Relations
    metrics = relationship("ResourceMetric", back_populates="resource")
    recommendations = relationship("Recommendation", back_populates="resource")


class ResourceMetric(Base):
    """Modèle représentant une métrique de ressource"""
    __tablename__ = 'resource_metrics'
    
    id = Column(Integer, primary_key=True)
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=False)
    metric_name = Column(String, nullable=False)  # CPU, mémoire, stockage, etc.
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    
    # Relations
    resource = relationship("Resource", back_populates="metrics")


class Recommendation(Base):
    """Modèle représentant une recommandation d'optimisation"""
    __tablename__ = 'recommendations'
    
    id = Column(Integer, primary_key=True)
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=False)
    type = Column(String, nullable=False)  # redimensionnement, arrêt, migration, etc.
    description = Column(String, nullable=False)
    impact = Column(String)  # faible, moyen, élevé
    estimated_savings = Column(Float)
    confidence = Column(Float)  # 0.0 à 1.0
    created_at = Column(DateTime, nullable=False)
    implemented = Column(Boolean, default=False)
    implemented_at = Column(DateTime)
    
    # Relations
    resource = relationship("Resource", back_populates="recommendations")


class User(Base):
    """Modèle représentant un utilisateur du système"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    aws_role_arn = Column(String)
    created_at = Column(DateTime, nullable=False)
    last_login = Column(DateTime)
    is_admin = Column(Boolean, default=False)


class DatabaseManager:
    """Gestionnaire de base de données pour le Cloud Optimizer"""
    
    def __init__(self, db_url=None):
        """
        Initialise le gestionnaire de base de données.
        
        Args:
            db_url: URL de connexion à la base de données (optionnel)
        """
        # Si aucune URL n'est fournie, utiliser la variable d'environnement ou une valeur par défaut
        self.db_url = db_url or os.getenv('DATABASE_URL', 'sqlite:///cloud_optimizer.db')
        self.engine = None
        self.Session = None
        
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialise le moteur SQLAlchemy."""
        try:
            self.engine = create_engine(self.db_url, echo=False)
            self.Session = sessionmaker(bind=self.engine)
            logger.info(f"Moteur de base de données initialisé: {self.db_url}")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du moteur de base de données: {e}")
            raise
    
    def create_tables(self):
        """Crée toutes les tables dans la base de données."""
        Base.metadata.create_all(self.engine)
        logger.info("Tables créées avec succès")
    
    def get_session(self):
        """
        Retourne une nouvelle session de base de données.
        
        Returns:
            Session SQLAlchemy
        """
        return self.Session()
    
    def add_resource(self, cloud_id, name, type, region, provider, tags=None, created_at=None):
        """
        Ajoute une nouvelle ressource à la base de données.
        
        Args:
            cloud_id: ID cloud de la ressource
            name: Nom de la ressource
            type: Type de ressource
            region: Région de la ressource
            provider: Fournisseur cloud
            tags: Tags de la ressource (optionnel)
            created_at: Date de création (optionnel)
            
        Returns:
            Resource: La ressource créée
        """
        session = self.get_session()
        try:
            resource = Resource(
                cloud_id=cloud_id,
                name=name,
                type=type,
                region=region,
                provider=provider,
                tags=tags or {},
                created_at=created_at,
                last_updated=created_at
            )
            session.add(resource)
            session.commit()
            return resource
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de l'ajout de la ressource: {e}")
            raise
        finally:
            session.close()
    
    def get_resources(self, provider=None, type=None, region=None):
        """
        Récupère les ressources selon les filtres.
        
        Args:
            provider: Fournisseur cloud (optionnel)
            type: Type de ressource (optionnel)
            region: Région de la ressource (optionnel)
            
        Returns:
            Liste des ressources
        """
        session = self.get_session()
        try:
            query = session.query(Resource)
            
            if provider:
                query = query.filter(Resource.provider == provider)
            if type:
                query = query.filter(Resource.type == type)
            if region:
                query = query.filter(Resource.region == region)
            
            return query.all()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des ressources: {e}")
            raise
        finally:
            session.close()
    
    def add_recommendation(self, resource_id, type, description, impact=None, estimated_savings=None, confidence=None, created_at=None):
        """
        Ajoute une nouvelle recommandation.
        
        Args:
            resource_id: ID de la ressource
            type: Type de recommandation
            description: Description de la recommandation
            impact: Impact (optionnel)
            estimated_savings: Économies estimées (optionnel)
            confidence: Confiance (optionnel)
            created_at: Date de création (optionnel)
            
        Returns:
            Recommendation: La recommandation créée
        """
        session = self.get_session()
        try:
            recommendation = Recommendation(
                resource_id=resource_id,
                type=type,
                description=description,
                impact=impact,
                estimated_savings=estimated_savings,
                confidence=confidence or 0.0,
                created_at=created_at,
                implemented=False
            )
            session.add(recommendation)
            session.commit()
            return recommendation
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de l'ajout de la recommandation: {e}")
            raise
        finally:
            session.close()


# Fonction utilitaire pour créer facilement un gestionnaire de base de données
def create_db_manager(db_url=None):
    """
    Crée et retourne un gestionnaire de base de données.
    
    Args:
        db_url: URL de connexion à la base de données (optionnel)
        
    Returns:
        Un gestionnaire de base de données initialisé
    """
    return DatabaseManager(db_url=db_url)


if __name__ == "__main__":
    # Exemple d'utilisation
    logging.basicConfig(level=logging.INFO)
    
    # Créer un gestionnaire de base de données avec SQLite en mémoire
    db_manager = create_db_manager(db_url='sqlite:///:memory:')
    
    # Créer les tables
    db_manager.create_tables()
    
    # Ajouter une ressource
    from datetime import datetime
    now = datetime.now()
    
    try:
        # Ajouter une ressource
        resource = db_manager.add_resource(
            cloud_id='i-1234567890abcdef0',
            name='web-server-1',
            type='EC2',
            region='us-east-1',
            provider='AWS',
            tags={'Environment': 'Production', 'Project': 'Website'},
            created_at=now
        )
        print(f"Ressource ajoutée: {resource.id} - {resource.name}")
        
        # Ajouter une recommandation
        recommendation = db_manager.add_recommendation(
            resource_id=resource.id,
            type='resize',
            description='Redimensionner l\'instance de t2.large à t2.medium',
            impact='medium',
            estimated_savings=30.45,
            confidence=0.85,
            created_at=now
        )
        print(f"Recommandation ajoutée: {recommendation.id} - {recommendation.type}")
        
        # Récupérer les ressources
        resources = db_manager.get_resources(provider='AWS', type='EC2')
        print(f"Ressources AWS EC2 récupérées: {len(resources)}")
        
    except Exception as e:
        print(f"Erreur lors de l'exécution de l'exemple: {e}")