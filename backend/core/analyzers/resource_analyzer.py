#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cloud Optimizer MVP
resource_analyzer.py - Analyseur générique de ressources cloud
"""

import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class ResourceAnalyzer:
    """Classe de base pour l'analyse des ressources cloud"""
    
    def __init__(self, aws_client=None, db_manager=None):
        """
        Initialise l'analyseur de ressources.
        
        Args:
            aws_client: Client AWS pour accéder aux services AWS
            db_manager: Gestionnaire de base de données
        """
        self.aws_client = aws_client
        self.db_manager = db_manager
    
    def analyze_resource_utilization(self, resource_id, resource_type, period_days=14):
        """
        Analyse l'utilisation d'une ressource sur une période donnée.
        
        Args:
            resource_id: ID de la ressource
            resource_type: Type de ressource (EC2, RDS, etc.)
            period_days: Nombre de jours à analyser (défaut: 14)
            
        Returns:
            dict: Données d'utilisation et analyse
        """
        # Vérifier si les clients sont disponibles
        if not self.aws_client:
            raise ValueError("AWS client non configuré")
        
        # Définir la période d'analyse
        end_time = datetime.now()
        start_time = end_time - timedelta(days=period_days)
        
        # Obtenir les métriques appropriées selon le type de ressource
        metrics = self._get_metrics_for_resource_type(resource_type)
        
        # Récupérer les données pour chaque métrique
        utilization_data = {}
        
        for metric in metrics:
            metric_data = self._get_metric_data(
                resource_id=resource_id,
                resource_type=resource_type,
                metric_name=metric["name"],
                namespace=metric["namespace"],
                start_time=start_time,
                end_time=end_time
            )
            
            if metric_data:
                utilization_data[metric["name"]] = metric_data
        
        # Analyser les données d'utilisation
        analysis_results = self._analyze_utilization_data(utilization_data, resource_type)
        
        return {
            "resource_id": resource_id,
            "resource_type": resource_type,
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "days": period_days
            },
            "utilization_data": utilization_data,
            "analysis": analysis_results
        }
    
    def _get_metrics_for_resource_type(self, resource_type):
        """
        Retourne les métriques à analyser pour un type de ressource.
        
        Args:
            resource_type: Type de ressource
            
        Returns:
            Liste des métriques
        """
        metrics_by_type = {
            "EC2": [
                {"name": "CPUUtilization", "namespace": "AWS/EC2"},
                {"name": "NetworkIn", "namespace": "AWS/EC2"},
                {"name": "NetworkOut", "namespace": "AWS/EC2"},
                {"name": "DiskReadOps", "namespace": "AWS/EC2"},
                {"name": "DiskWriteOps", "namespace": "AWS/EC2"}
            ],
            "RDS": [
                {"name": "CPUUtilization", "namespace": "AWS/RDS"},
                {"name": "DatabaseConnections", "namespace": "AWS/RDS"},
                {"name": "FreeableMemory", "namespace": "AWS/RDS"},
                {"name": "ReadIOPS", "namespace": "AWS/RDS"},
                {"name": "WriteIOPS", "namespace": "AWS/RDS"}
            ],
            "S3": [
                {"name": "BucketSizeBytes", "namespace": "AWS/S3"},
                {"name": "NumberOfObjects", "namespace": "AWS/S3"},
                {"name": "AllRequests", "namespace": "AWS/S3"},
                {"name": "GetRequests", "namespace": "AWS/S3"},
                {"name": "PutRequests", "namespace": "AWS/S3"}
            ]
        }
        
        return metrics_by_type.get(resource_type, [])
    
    def _get_metric_data(self, resource_id, resource_type, metric_name, namespace, start_time, end_time, period=3600):
        """
        Récupère les données métriques depuis CloudWatch.
        
        Args:
            resource_id: ID de la ressource
            resource_type: Type de ressource
            metric_name: Nom de la métrique
            namespace: Espace de nom de la métrique
            start_time: Heure de début
            end_time: Heure de fin
            period: Période en secondes (défaut: 1 heure)
            
        Returns:
            Liste des valeurs métriques
        """
        # Déterminer les dimensions en fonction du type de ressource
        dimensions = self._get_dimensions(resource_id, resource_type)
        
        try:
            metric_data = self.aws_client.get_metric_data(
                namespace=namespace,
                metric_name=metric_name,
                dimensions=dimensions,
                start_time=start_time,
                end_time=end_time,
                period=period
            )
            
            if metric_data and 'Timestamps' in metric_data and 'Values' in metric_data:
                # Créer un DataFrame pandas pour faciliter l'analyse
                df = pd.DataFrame({
                    'timestamp': metric_data['Timestamps'],
                    'value': metric_data['Values']
                })
                
                # Trier par timestamp
                df = df.sort_values('timestamp')
                
                return {
                    'times': df['timestamp'].tolist(),
                    'values': df['value'].tolist(),
                    'min': float(df['value'].min()) if not df.empty else None,
                    'max': float(df['value'].max()) if not df.empty else None,
                    'avg': float(df['value'].mean()) if not df.empty else None,
                    'p95': float(df['value'].quantile(0.95)) if not df.empty else None
                }
            
            return None
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données métriques pour {resource_id} ({metric_name}): {e}")
            return None
    
    def _get_dimensions(self, resource_id, resource_type):
        """
        Détermine les dimensions CloudWatch en fonction du type de ressource.
        
        Args:
            resource_id: ID de la ressource
            resource_type: Type de ressource
            
        Returns:
            Liste des dimensions
        """
        if resource_type == "EC2":
            return [{"Name": "InstanceId", "Value": resource_id}]
        elif resource_type == "RDS":
            return [{"Name": "DBInstanceIdentifier", "Value": resource_id}]
        elif resource_type == "S3":
            return [{"Name": "BucketName", "Value": resource_id}]
        
        return []
    
    def _analyze_utilization_data(self, utilization_data, resource_type):
        """
        Analyse les données d'utilisation pour déterminer les opportunités d'optimisation.
        
        Args:
            utilization_data: Données d'utilisation
            resource_type: Type de ressource
            
        Returns:
            Résultats de l'analyse
        """
        analysis = {
            "underutilized": False,
            "overutilized": False,
            "idle": False,
            "recommendations": []
        }
        
        # Analyse spécifique pour EC2
        if resource_type == "EC2" and "CPUUtilization" in utilization_data:
            cpu_data = utilization_data["CPUUtilization"]
            
            # Vérifier si l'instance est sous-utilisée
            if cpu_data["avg"] < 10 and cpu_data["p95"] < 20:
                analysis["underutilized"] = True
                analysis["recommendations"].append({
                    "type": "resize",
                    "description": "Envisager de redimensionner l'instance à une taille inférieure",
                    "impact": "medium",
                    "confidence": 0.85 if cpu_data["p95"] < 15 else 0.7
                })
            
            # Vérifier si l'instance est sur-utilisée
            elif cpu_data["avg"] > 80 or cpu_data["p95"] > 95:
                analysis["overutilized"] = True
                analysis["recommendations"].append({
                    "type": "upgrade",
                    "description": "Envisager de redimensionner l'instance à une taille supérieure pour éviter les problèmes de performance",
                    "impact": "high",
                    "confidence": 0.9 if cpu_data["p95"] > 95 else 0.8
                })
            
            # Vérifier si l'instance est inactive
            if cpu_data["avg"] < 2 and cpu_data["max"] < 5:
                analysis["idle"] = True
                analysis["recommendations"].append({
                    "type": "shutdown",
                    "description": "Envisager d'arrêter ou de supprimer cette instance qui semble inactive",
                    "impact": "high",
                    "confidence": 0.95
                })
        
        # Analyse spécifique pour RDS
        elif resource_type == "RDS" and "CPUUtilization" in utilization_data:
            cpu_data = utilization_data["CPUUtilization"]
            
            # Vérifier si l'instance RDS est sous-utilisée
            if cpu_data["avg"] < 5 and cpu_data["p95"] < 15:
                analysis["underutilized"] = True
                analysis["recommendations"].append({
                    "type": "resize",
                    "description": "Envisager de redimensionner l'instance RDS à une classe inférieure",
                    "impact": "medium",
                    "confidence": 0.8
                })
        
        # Analyse spécifique pour S3
        elif resource_type == "S3" and "GetRequests" in utilization_data and "PutRequests" in utilization_data:
            get_data = utilization_data["GetRequests"]
            put_data = utilization_data["PutRequests"]
            
            # Vérifier si le bucket est principalement en lecture seule et rarement mis à jour
            if get_data["avg"] > 0 and put_data["avg"] < (get_data["avg"] * 0.01):
                analysis["recommendations"].append({
                    "type": "lifecycle",
                    "description": "Envisager d'implémenter des règles de cycle de vie pour archiver les données plus anciennes",
                    "impact": "low",
                    "confidence": 0.7
                })
        
        return analysis
    
    def get_optimization_recommendations(self, provider="AWS", resource_types=None, min_confidence=0.7):
        """
        Obtient des recommandations d'optimisation pour les ressources.
        
        Args:
            provider: Fournisseur cloud (défaut: AWS)
            resource_types: Types de ressources à analyser (optionnel)
            min_confidence: Confiance minimale des recommandations (défaut: 0.7)
            
        Returns:
            Liste des recommandations
        """
        recommendations = []
        
        # Vérifier si le gestionnaire de base de données est disponible
        if not self.db_manager:
            raise ValueError("Gestionnaire de base de données non configuré")
        
        # Récupérer les ressources
        resources = self.db_manager.get_resources(provider=provider, type=resource_types[0] if resource_types else None)
        
        # Analyser chaque ressource
        for resource in resources:
            try:
                analysis = self.analyze_resource_utilization(
                    resource_id=resource.cloud_id,
                    resource_type=resource.type
                )
                
                # Ajouter les recommandations si elles ont une confiance suffisante
                for rec in analysis["analysis"]["recommendations"]:
                    if rec["confidence"] >= min_confidence:
                        # Ajouter la recommandation à la base de données
                        db_rec = self.db_manager.add_recommendation(
                            resource_id=resource.id,
                            type=rec["type"],
                            description=rec["description"],
                            impact=rec["impact"],
                            estimated_savings=0.0,  # À calculer séparément
                            confidence=rec["confidence"],
                            created_at=datetime.now()
                        )
                        
                        # Ajouter à la liste de recommandations
                        recommendations.append({
                            "id": db_rec.id,
                            "resource_id": resource.id,
                            "resource_name": resource.name,
                            "resource_type": resource.type,
                            "type": db_rec.type,
                            "description": db_rec.description,
                            "impact": db_rec.impact,
                            "confidence": db_rec.confidence
                        })
            
            except Exception as e:
                logger.error(f"Erreur lors de l'analyse de la ressource {resource.id}: {e}")
        
        return recommendations


# Fonction utilitaire pour créer facilement un analyseur de ressources
def create_resource_analyzer(aws_client=None, db_manager=None):
    """
    Crée et retourne un analyseur de ressources.
    
    Args:
        aws_client: Client AWS (optionnel)
        db_manager: Gestionnaire de base de données (optionnel)
        
    Returns:
        Un analyseur de ressources initialisé
    """
    return ResourceAnalyzer(aws_client=aws_client, db_manager=db_manager)


if __name__ == "__main__":
    # Exemple d'utilisation
    logging.basicConfig(level=logging.INFO)
    
    # Importer les modules nécessaires
    from datetime import datetime, timedelta
    
    # Import fictif pour l'exemple
    # Dans un vrai contexte, importez les véritables modules
    try:
        from backend.integrations.aws_client import create_aws_client
        from backend.utils.db import create_db_manager
    except ImportError:
        # Utiliser des imports relatifs pour l'exemple
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Essayer à nouveau avec des chemins relatifs
        try:
            from integrations.aws_client import create_aws_client
            from utils.db import create_db_manager
        except ImportError:
            # Créer des mocks pour l'exemple
            def create_aws_client():
                return None
            def create_db_manager():
                return None
    
    # Initialiser les clients
    aws_client = create_aws_client()
    db_manager = create_db_manager(db_url='sqlite:///:memory:')
    
    # Créer l'analyseur de ressources
    analyzer = create_resource_analyzer(aws_client=aws_client, db_manager=db_manager)
    
    # Dans un vrai contexte, analysez les ressources
    # Dans cet exemple, nous affichons simplement un message
    print("Analyseur de ressources initialisé et prêt à l'emploi")
    print("Utilisez analyzer.analyze_resource_utilization() pour analyser une ressource spécifique")
    print("Utilisez analyzer.get_optimization_recommendations() pour obtenir des recommandations")