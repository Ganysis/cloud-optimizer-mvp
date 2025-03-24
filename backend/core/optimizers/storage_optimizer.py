#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cloud Optimizer MVP
storage_optimizer.py - Module d'optimisation des ressources de stockage (S3, EBS)
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

# Import des modules de base
from backend.integrations.aws_client import AwsClient
from backend.core.analyzers.resource_analyzer import ResourceAnalyzer
from backend.utils.db import OptimizerRecommendation, RecommendationType, ResourceType, session

logger = logging.getLogger(__name__)

class StorageOptimizer:
    """
    Classe spécialisée dans l'analyse et l'optimisation des ressources de stockage AWS
    telles que les buckets S3 et les volumes EBS.
    """
    
    def __init__(self, aws_client: AwsClient, resource_analyzer: ResourceAnalyzer):
        """
        Initialise l'optimiseur de stockage.
        
        Args:
            aws_client: Client AWS pour accéder aux services
            resource_analyzer: Analyseur de ressources de base
        """
        self.aws_client = aws_client
        self.resource_analyzer = resource_analyzer
        
    def analyze_s3_buckets(self, account_id: str, region: str) -> List[Dict[str, Any]]:
        """
        Analyse les buckets S3 et identifie les opportunités d'optimisation.
        
        Args:
            account_id: ID du compte AWS
            region: Région AWS à analyser
            
        Returns:
            Liste des buckets S3 avec des métriques d'analyse
        """
        # Récupérer les buckets S3 depuis l'analyseur de ressources
        buckets = self.resource_analyzer.get_resources(
            account_id=account_id,
            region=region,
            resource_type=ResourceType.S3_BUCKET
        )
        
        enriched_buckets = []
        
        for bucket in buckets:
            bucket_name = bucket.get('BucketName', '')
            
            # Récupérer les métriques d'accès et les classes de stockage
            access_metrics = self.get_bucket_access_metrics(bucket_name, account_id, region)
            storage_classes = self.get_bucket_storage_classes(bucket_name, account_id, region)
            
            # Enrichir les données du bucket avec les métriques
            bucket_data = {
                **bucket,
                'AccessMetrics': access_metrics,
                'StorageClasses': storage_classes,
                'OptimizationPotential': self._calculate_s3_optimization_potential(
                    bucket, access_metrics, storage_classes
                )
            }
            
            enriched_buckets.append(bucket_data)
            
        return enriched_buckets
    
    def get_bucket_access_metrics(
        self, bucket_name: str, account_id: str, region: str, days: int = 90
    ) -> Dict[str, Any]:
        """
        Récupère les métriques d'accès pour un bucket S3 sur une période donnée.
        
        Args:
            bucket_name: Nom du bucket S3
            account_id: ID du compte AWS
            region: Région AWS
            days: Nombre de jours d'historique à analyser
            
        Returns:
            Dictionnaire contenant les statistiques d'accès au bucket
        """
        try:
            # Récupérer les métriques CloudWatch via le client AWS
            get_requests = self.aws_client.get_cloudwatch_metrics(
                account_id=account_id,
                region=region,
                namespace='AWS/S3',
                metric_name='GetRequests',
                dimensions=[{'Name': 'BucketName', 'Value': bucket_name}],
                period=86400,  # Agrégation journalière
                days=days
            )
            
            put_requests = self.aws_client.get_cloudwatch_metrics(
                account_id=account_id,
                region=region,
                namespace='AWS/S3',
                metric_name='PutRequests',
                dimensions=[{'Name': 'BucketName', 'Value': bucket_name}],
                period=86400,  # Agrégation journalière
                days=days
            )
            
            # Calculer les statistiques d'accès
            result = {
                'LastAccessDate': None,
                'LastWriteDate': None,
                'ReadFrequency': 'NONE',  # NONE, LOW, MEDIUM, HIGH
                'WriteFrequency': 'NONE',  # NONE, LOW, MEDIUM, HIGH
                'TotalGetRequests': 0,
                'TotalPutRequests': 0,
                'DaysSinceLastAccess': None,
                'DaysSinceLastWrite': None
            }
            
            # Traiter les métriques GET (lecture)
            if get_requests and 'Datapoints' in get_requests and get_requests['Datapoints']:
                datapoints = get_requests['Datapoints']
                result['TotalGetRequests'] = sum(dp.get('Sum', 0) for dp in datapoints)
                
                if result['TotalGetRequests'] > 0:
                    # Trouver la date du dernier accès en lecture
                    latest_get = max(datapoints, key=lambda dp: dp.get('Timestamp', datetime.min))
                    result['LastAccessDate'] = latest_get.get('Timestamp')
                    
                    # Calculer le nombre de jours depuis le dernier accès
                    if result['LastAccessDate']:
                        days_since = (datetime.now() - result['LastAccessDate']).days
                        result['DaysSinceLastAccess'] = days_since
                    
                    # Déterminer la fréquence de lecture
                    avg_daily_gets = result['TotalGetRequests'] / len(datapoints) if datapoints else 0
                    if avg_daily_gets > 1000:
                        result['ReadFrequency'] = 'HIGH'
                    elif avg_daily_gets > 100:
                        result['ReadFrequency'] = 'MEDIUM'
                    elif avg_daily_gets > 0:
                        result['ReadFrequency'] = 'LOW'
            
            # Traiter les métriques PUT (écriture)
            if put_requests and 'Datapoints' in put_requests and put_requests['Datapoints']:
                datapoints = put_requests['Datapoints']
                result['TotalPutRequests'] = sum(dp.get('Sum', 0) for dp in datapoints)
                
                if result['TotalPutRequests'] > 0:
                    # Trouver la date de la dernière écriture
                    latest_put = max(datapoints, key=lambda dp: dp.get('Timestamp', datetime.min))
                    result['LastWriteDate'] = latest_put.get('Timestamp')
                    
                    # Calculer le nombre de jours depuis la dernière écriture
                    if result['LastWriteDate']:
                        days_since = (datetime.now() - result['LastWriteDate']).days
                        result['DaysSinceLastWrite'] = days_since
                    
                    # Déterminer la fréquence d'écriture
                    avg_daily_puts = result['TotalPutRequests'] / len(datapoints) if datapoints else 0
                    if avg_daily_puts > 100:
                        result['WriteFrequency'] = 'HIGH'
                    elif avg_daily_puts > 10:
                        result['WriteFrequency'] = 'MEDIUM'
                    elif avg_daily_puts > 0:
                        result['WriteFrequency'] = 'LOW'
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métriques d'accès pour {bucket_name}: {str(e)}")
            return {
                'LastAccessDate': None,
                'LastWriteDate': None,
                'ReadFrequency': 'UNKNOWN',
                'WriteFrequency': 'UNKNOWN',
                'TotalGetRequests': 0,
                'TotalPutRequests': 0,
                'DaysSinceLastAccess': None,
                'DaysSinceLastWrite': None,
                'Error': str(e)
            }
    
    def get_bucket_storage_classes(
        self, bucket_name: str, account_id: str, region: str
    ) -> Dict[str, Any]:
        """
        Récupère les informations sur les classes de stockage utilisées dans un bucket S3.
        
        Args:
            bucket_name: Nom du bucket S3
            account_id: ID du compte AWS
            region: Région AWS
            
        Returns:
            Dictionnaire contenant les statistiques des classes de stockage
        """
        try:
            # Utiliser le client AWS pour obtenir l'inventaire des objets par classe de stockage
            storage_metrics = self.aws_client.get_s3_storage_metrics(
                account_id=account_id,
                region=region,
                bucket_name=bucket_name
            )
            
            # Initialiser le résultat
            result = {
                'Standard': {'SizeBytes': 0, 'ObjectCount': 0},
                'StandardIA': {'SizeBytes': 0, 'ObjectCount': 0},
                'OneZoneIA': {'SizeBytes': 0, 'ObjectCount': 0},
                'IntelligentTiering': {'SizeBytes': 0, 'ObjectCount': 0},
                'Glacier': {'SizeBytes': 0, 'ObjectCount': 0},
                'DeepArchive': {'SizeBytes': 0, 'ObjectCount': 0},
                'TotalSizeBytes': 0,
                'TotalObjectCount': 0
            }
            
            # Si les métriques sont disponibles, les traiter
            if storage_metrics:
                # Traiter les métriques par classe de stockage
                for storage_class, metrics in storage_metrics.items():
                    if storage_class in result:
                        result[storage_class]['SizeBytes'] = metrics.get('SizeBytes', 0)
                        result[storage_class]['ObjectCount'] = metrics.get('ObjectCount', 0)
                
                # Calculer les totaux
                result['TotalSizeBytes'] = sum(
                    metrics['SizeBytes'] for metrics in [result[sc] for sc in result if sc not in ['TotalSizeBytes', 'TotalObjectCount']]
                )
                result['TotalObjectCount'] = sum(
                    metrics['ObjectCount'] for metrics in [result[sc] for sc in result if sc not in ['TotalSizeBytes', 'TotalObjectCount']]
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des classes de stockage pour {bucket_name}: {str(e)}")
            return {
                'Standard': {'SizeBytes': 0, 'ObjectCount': 0},
                'StandardIA': {'SizeBytes': 0, 'ObjectCount': 0},
                'OneZoneIA': {'SizeBytes': 0, 'ObjectCount': 0},
                'IntelligentTiering': {'SizeBytes': 0, 'ObjectCount': 0},
                'Glacier': {'SizeBytes': 0, 'ObjectCount': 0},
                'DeepArchive': {'SizeBytes': 0, 'ObjectCount': 0},
                'TotalSizeBytes': 0,
                'TotalObjectCount': 0,
                'Error': str(e)
            }
    
    def _calculate_s3_optimization_potential(
        self, bucket: Dict[str, Any], access_metrics: Dict[str, Any], storage_classes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calcule le potentiel d'optimisation d'un bucket S3.
        
        Args:
            bucket: Données du bucket S3
            access_metrics: Métriques d'accès au bucket
            storage_classes: Données sur les classes de stockage utilisées
            
        Returns:
            Dictionnaire contenant le potentiel d'optimisation
        """
        # Initialiser le résultat
        result = {
            'Recommendations': [],
            'TotalCurrentCost': 0,
            'TotalProjectedCost': 0,
            'TotalSavings': 0,
            'SavingsPercentage': 0
        }
        
        # Vérifier si les données sont complètes
        if not storage_classes or not access_metrics:
            return result
        
        # Calculer le coût actuel
        current_cost = self._calculate_s3_current_cost(storage_classes, bucket.get('Region', ''))
        result['TotalCurrentCost'] = current_cost
        
        # Liste des recommandations
        recommendations = []
        total_projected_cost = current_cost
        
        # 1. Vérifier si le bucket contient des données en classe Standard peu accédées
        standard_size = storage_classes.get('Standard', {}).get('SizeBytes', 0)
        standard_objects = storage_classes.get('Standard', {}).get('ObjectCount', 0)
        
        if (standard_size > 0 and access_metrics.get('ReadFrequency') == 'LOW' and 
            (access_metrics.get('DaysSinceLastAccess', 0) or 0) > 30):
            
            # Recommander un changement vers Standard-IA
            standard_cost = self._calculate_s3_storage_cost('Standard', standard_size, bucket.get('Region', ''))
            standard_ia_cost = self._calculate_s3_storage_cost('StandardIA', standard_size, bucket.get('Region', ''))
            savings = standard_cost - standard_ia_cost
            
            # Si l'économie est significative
            if savings > 1.0:  # Plus d'1$ d'économie par mois
                recommendations.append({
                    'Type': RecommendationType.STORAGE_CLASS_CHANGE.value,
                    'Description': "Migrer les objets de Standard vers Standard-IA",
                    'AffectedStorage': "Standard",
                    'RecommendedStorage': "StandardIA",
                    'AffectedSizeGB': standard_size / (1024 * 1024 * 1024),
                    'AffectedObjects': standard_objects,
                    'CurrentCost': standard_cost,
                    'ProjectedCost': standard_ia_cost,
                    'Savings': savings,
                    'SavingsPercentage': (savings / standard_cost * 100) if standard_cost > 0 else 0,
                    'Reasoning': [
                        f"Le bucket a une faible fréquence d'accès (dernier accès il y a {access_metrics.get('DaysSinceLastAccess')} jours)",
                        f"{standard_objects} objets ({standard_size / (1024 * 1024 * 1024):.2f} Go) sont stockés en classe Standard"
                    ]
                })
                
                total_projected_cost = total_projected_cost - savings
        
        # 2. Vérifier les données très peu accédées qui pourraient aller en Glacier
        standard_and_ia_size = (
            storage_classes.get('Standard', {}).get('SizeBytes', 0) + 
            storage_classes.get('StandardIA', {}).get('SizeBytes', 0)
        )
        standard_and_ia_objects = (
            storage_classes.get('Standard', {}).get('ObjectCount', 0) + 
            storage_classes.get('StandardIA', {}).get('ObjectCount', 0)
        )
        
        if (standard_and_ia_size > 0 and access_metrics.get('ReadFrequency') == 'NONE' and 
            (access_metrics.get('DaysSinceLastAccess', 0) or 0) > 90):
            
            # Recommander un changement vers Glacier
            current_cost = self._calculate_s3_storage_cost('Standard', standard_and_ia_size, bucket.get('Region', ''))
            glacier_cost = self._calculate_s3_storage_cost('Glacier', standard_and_ia_size, bucket.get('Region', ''))
            savings = current_cost - glacier_cost
            
            # Si l'économie est significative
            if savings > 5.0:  # Plus de 5$ d'économie par mois
                recommendations.append({
                    'Type': RecommendationType.STORAGE_CLASS_CHANGE.value,
                    'Description': "Archiver les objets rarement accédés vers Glacier",
                    'AffectedStorage': "Standard/StandardIA",
                    'RecommendedStorage': "Glacier",
                    'AffectedSizeGB': standard_and_ia_size / (1024 * 1024 * 1024),
                    'AffectedObjects': standard_and_ia_objects,
                    'CurrentCost': current_cost,
                    'ProjectedCost': glacier_cost,
                    'Savings': savings,
                    'SavingsPercentage': (savings / current_cost * 100) if current_cost > 0 else 0,
                    'Reasoning': [
                        f"Aucun accès récent au bucket (dernier accès il y a {access_metrics.get('DaysSinceLastAccess')} jours)",
                        f"{standard_and_ia_objects} objets ({standard_and_ia_size / (1024 * 1024 * 1024):.2f} Go) pourraient être archivés"
                    ]
                })
                
                total_projected_cost = total_projected_cost - savings
                
        # 3. Vérifier s'il y a des objets qui n'ont pas été accédés depuis très longtemps (potentiel suppression)
        if ((access_metrics.get('DaysSinceLastAccess', 0) or 0) > 365 and 
            (access_metrics.get('DaysSinceLastWrite', 0) or 0) > 365):
            
            total_size = storage_classes.get('TotalSizeBytes', 0)
            total_objects = storage_classes.get('TotalObjectCount', 0)
            
            # Coût actuel de tous les objets
            current_total_cost = result['TotalCurrentCost']
            
            recommendations.append({
                'Type': RecommendationType.RESOURCE_CLEANUP.value,
                'Description': "Évaluer la suppression des données non utilisées",
                'AffectedStorage': "Tous",
                'RecommendedStorage': "N/A",
                'AffectedSizeGB': total_size / (1024 * 1024 * 1024),
                'AffectedObjects': total_objects,
                'CurrentCost': current_total_cost,
                'ProjectedCost': 0,
                'Savings': current_total_cost,
                'SavingsPercentage': 100,
                'Reasoning': [
                    f"Aucun accès ni modification depuis plus d'un an (dernier accès il y a {access_metrics.get('DaysSinceLastAccess')} jours)",
                    f"Le bucket contient {total_objects} objets ({total_size / (1024 * 1024 * 1024):.2f} Go)"
                ]
            })
            
            # Ce n'est qu'une recommandation, donc nous ne l'incluons pas dans l'économie totale projetée
            
        # Mettre à jour le résultat avec les recommandations
        result['Recommendations'] = recommendations
        result['TotalProjectedCost'] = total_projected_cost
        result['TotalSavings'] = result['TotalCurrentCost'] - total_projected_cost
        
        if result['TotalCurrentCost'] > 0:
            result['SavingsPercentage'] = (result['TotalSavings'] / result['TotalCurrentCost'] * 100)
        
        return result
        
    def _calculate_s3_current_cost(self, storage_classes: Dict[str, Any], region: str) -> float:
        """
        Calcule le coût actuel du stockage S3 en fonction des classes utilisées.
        
        Args:
            storage_classes: Données sur les classes de stockage utilisées
            region: Région AWS
            
        Returns:
            Coût mensuel estimé en dollars
        """
        total_cost = 0
        
        # Calculer le coût pour chaque classe de stockage
        for storage_class in ['Standard', 'StandardIA', 'OneZoneIA', 'IntelligentTiering', 'Glacier', 'DeepArchive']:
            size_bytes = storage_classes.get(storage_class, {}).get('SizeBytes', 0)
            if size_bytes > 0:
                cost = self._calculate_s3_storage_cost(storage_class, size_bytes, region)
                total_cost += cost
                
        return total_cost
    
    def _calculate_s3_storage_cost(self, storage_class: str, size_bytes: int, region: str) -> float:
        """
        Calcule le coût du stockage S3 pour une classe et une taille données.
        
        Args:
            storage_class: Classe de stockage S3
            size_bytes: Taille en octets
            region: Région AWS
            
        Returns:
            Coût mensuel estimé en dollars
        """
        # Convertir en Go pour le calcul des coûts
        size_gb = size_bytes / (1024 * 1024 * 1024)
        
        # Prix approximatifs par Go par mois (USD) - à mettre à jour avec des prix réels
        pricing = {
            'Standard': {
                'us-east-1': 0.023,
                'eu-west-1': 0.024,
                'ap-northeast-1': 0.025
            },
            'StandardIA': {
                'us-east-1': 0.0125,
                'eu-west-1': 0.0135,
                'ap-northeast-1': 0.014
            },
            'OneZoneIA': {
                'us-east-1': 0.01,
                'eu-west-1': 0.011,
                'ap-northeast-1': 0.012
            },
            'IntelligentTiering': {
                'us-east-1': 0.023,  # Prix de base, hors frais de surveillance
                'eu-west-1': 0.024,
                'ap-northeast-1': 0.025
            },
            'Glacier': {
                'us-east-1': 0.004,
                'eu-west-1': 0.0045,
                'ap-northeast-1': 0.005
            },
            'DeepArchive': {
                'us-east-1': 0.00099,
                'eu-west-1': 0.0011,
                'ap-northeast-1': 0.0012
            }
        }
        
        # Prix par défaut si la région n'est pas spécifiée
        default_region = 'us-east-1'
        
        # Obtenir le prix pour la classe et la région spécifiées
        cost_per_gb = pricing.get(storage_class, {}).get(
            region, pricing.get(storage_class, {}).get(default_region, 0)
        )
        
        # Calculer le coût total
        return cost_per_gb * size_gb
    
    def analyze_ebs_volumes(self, account_id: str, region: str) -> List[Dict[str, Any]]:
        """
        Analyse les volumes EBS et identifie les opportunités d'optimisation.
        
        Args:
            account_id: ID du compte AWS
            region: Région AWS à analyser
            
        Returns:
            Liste des volumes EBS avec des métriques d'analyse
        """
        # Récupérer les volumes EBS depuis l'analyseur de ressources
        volumes = self.resource_analyzer.get_resources(
            account_id=account_id,
            region=region,
            resource_type=ResourceType.EBS_VOLUME
        )
        
        enriched_volumes = []
        
        for volume in volumes:
            volume_id = volume.get('VolumeId', '')
            
            # Récupérer les métriques d'utilisation
            utilization_metrics = self.get_volume_utilization_metrics(volume_id, account_id, region)
            
            # Enrichir les données du volume avec les métriques
            volume_data = {
                **volume,
                'UtilizationMetrics': utilization_metrics,
                'OptimizationPotential': self._calculate_ebs_optimization_potential(
                    volume, utilization_metrics
                )
            }
            
            enriched_volumes.append(volume_data)
            
        return enriched_volumes
    
    def get_volume_utilization_metrics(
        self, volume_id: str, account_id: str, region: str, days: int = 30
    ) -> Dict[str, Any]:
        """
        Récupère les métriques d'utilisation pour un volume EBS sur une période donnée.
        
        Args:
            volume_id: ID du volume EBS
            account_id: ID du compte AWS
            region: Région AWS
            days: Nombre de jours d'historique à analyser
            
        Returns:
            Dictionnaire contenant les statistiques d'utilisation du volume
        """
        try:
            # Récupérer les métriques CloudWatch via le client AWS
            volume_read_ops = self.aws_client.get_cloudwatch_metrics(
                account_id=account_id,
                region=region,
                namespace='AWS/EBS',
                metric_name='VolumeReadOps',
                dimensions=[{'Name': 'VolumeId', 'Value': volume_id}],
                period=3600,  # Agrégation horaire
                days=days
            )
            
            volume_write_ops = self.aws_client.get_cloudwatch_metrics(
                account_id=account_id,
                region=region,
                namespace='AWS/EBS',
                metric_name='VolumeWriteOps',
                dimensions=[{'Name': 'VolumeId', 'Value': volume_id}],
                period=3600,  # Agrégation horaire
                days=days
            )
            
            # Calculer les statistiques d'utilisation
            result = {
                'ReadOps': {
                    'Average': 0,
                    'Maximum': 0,
                    'P95': 0,
                    'TotalOps': 0
                },
                'WriteOps': {
                    'Average': 0,
                    'Maximum': 0,
                    'P95': 0,
                    'TotalOps': 0
                },
                'UtilizationLevel': 'UNKNOWN',  # NONE, LOW, MEDIUM, HIGH, UNKNOWN
                'LastActivityDate': None,
                'DaysSinceLastActivity': None
            }
            
            # Traiter les métriques de lecture
            if volume_read_ops and 'Datapoints' in volume_read_ops and volume_read_ops['Datapoints']:
                datapoints = volume_read_ops['Datapoints']
                values = [dp.get('Sum', 0) for dp in datapoints]
                
                result['ReadOps']['TotalOps'] = sum(values)
                result['ReadOps']['Average'] = sum(values) / len(values) if values else 0
                result['ReadOps']['Maximum'] = max(values) if values else 0
                result['ReadOps']['P95'] = self._calculate_percentile(values, 95) if values else 0
                
                # Trouver la date de la dernière activité de lecture
                if any(values):
                    latest_activity = max(
                        (dp for dp in datapoints if dp.get('Sum', 0) > 0),
                        key=lambda dp: dp.get('Timestamp', datetime.min),
                        default=None
                    )
                    if latest_activity:
                        last_activity_date = latest_activity.get('Timestamp')
                        if not result['LastActivityDate'] or last_activity_date > result['LastActivityDate']:
                            result['LastActivityDate'] = last_activity_date
            
            # Traiter les métriques d'écriture
            if volume_write_ops and 'Datapoints' in volume_write_ops and volume_write_ops['Datapoints']:
                datapoints = volume_write_ops['Datapoints']
                values = [dp.get('Sum', 0) for dp in datapoints]
                
                result['WriteOps']['TotalOps'] = sum(values)
                result['WriteOps']['Average'] = sum(values) / len(values) if values else 0
                result['WriteOps']['Maximum'] = max(values) if values else 0
                result['WriteOps']['P95'] = self._calculate_percentile(values, 95) if values else 0
                
                # Trouver la date de la dernière activité d'écriture
                if any(values):
                    latest_activity = max(
                        (dp for dp in datapoints if dp.get('Sum', 0) > 0),
                        key=lambda dp: dp.get('Timestamp', datetime.min),
                        default=None
                    )
                    if latest_activity:
                        last_activity_date = latest_activity.get('Timestamp')
                        if not result['LastActivityDate'] or last_activity_date > result['LastActivityDate']:
                            result['LastActivityDate'] = last_activity_date
            
            # Calculer les jours depuis la dernière activité
            if result['LastActivityDate']:
                days_since = (datetime.now() - result['LastActivityDate']).days
                result['DaysSinceLastActivity'] = days_since
            
            # Déterminer le niveau d'utilisation global
            total_ops_daily = (result['ReadOps']['Average'] + result['WriteOps']['Average']) * 24
            
            if total_ops_daily > 10000:
                result['UtilizationLevel'] = 'HIGH'
            elif total_ops_daily > 1000:
                result['UtilizationLevel'] = 'MEDIUM'
            elif total_ops_daily > 0:
                result['UtilizationLevel'] = 'LOW'
            else:
                result['UtilizationLevel'] = 'NONE'
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métriques d'utilisation pour {volume_id}: {str(e)}")
            return {
                'ReadOps': {'Average': 0, 'Maximum': 0, 'P95': 0, 'TotalOps': 0},
                'WriteOps': {'Average': 0, 'Maximum': 0, 'P95': 0, 'TotalOps': 0},
                'UtilizationLevel': 'UNKNOWN',
                'LastActivityDate': None,
                'DaysSinceLastActivity': None,
                'Error': str(e)
            }
    
    def _calculate_ebs_optimization_potential(
        self, volume: Dict[str, Any], utilization_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calcule le potentiel d'optimisation d'un volume EBS.
        
        Args:
            volume: Données du volume EBS
            utilization_metrics: Métriques d'utilisation du volume
            
        Returns:
            Dictionnaire contenant le potentiel d'optimisation
        """
        # Initialiser le résultat
        result = {
            'Recommendations': [],
            'CurrentCost': 0,
            'ProjectedCost': 0,
            'Savings': 0,
            'SavingsPercentage': 0
        }
        
        # Extraire les propriétés du volume
        volume_type = volume.get('VolumeType', '')
        volume_size = volume.get('Size', 0)  # Taille en Go
        iops = volume.get('Iops', 0)
        throughput = volume.get('Throughput', 0)
        attached = volume.get('State', '') == 'in-use'
        region = volume.get('Region', '')
        
        # Calculer le coût actuel
        current_cost = self._calculate_ebs_cost(
            volume_type, volume_size, iops, throughput, region
        )
        result['CurrentCost'] = current_cost
        
        # Liste des recommandations
        recommendations = []
        projected_cost = current_cost
        
        # 1. Vérifier si le volume est non attaché (candidat pour suppression)
        if not attached:
            recommendations.append({
                'Type': RecommendationType.RESOURCE_CLEANUP.value,
                'Description': "Supprimer le volume EBS non attaché",
                'CurrentConfiguration': f"{volume_type}, {volume_size} Go",
                'RecommendedConfiguration': "Suppression",
                'CurrentCost': current_cost,
                'ProjectedCost': 0,
                'Savings': current_cost,
                'SavingsPercentage': 100,
                'Confidence': 'HIGH',
                'Reasoning': [
                    "Le volume n'est pas attaché à une instance",
                    f"Coût mensuel de {current_cost:.2f}$ pour un stockage inutilisé"
                ]
            })
            
            projected_cost = 0
        
        # 2. Vérifier si le volume est sous-utilisé (candidat pour type moins cher ou taille réduite)
        elif utilization_metrics.get('UtilizationLevel') in ['NONE', 'LOW']:
            # Cas 1: Volume provisioned IOPS (io1/io2) sous-utilisé -> gp3/gp2
            if volume_type in ['io1', 'io2']:
                # Déterminer le type recommandé (gp3 pour la plupart des cas récents)
                recommended_type = 'gp3'
                
                # Calculer le coût avec le nouveau type
                recommended_cost = self._calculate_ebs_cost(
                    recommended_type, volume_size, 3000, 125, region  # Valeurs par défaut pour gp3
                )
                
                savings = current_cost - recommended_cost
                
                # Si l'économie est significative
                if savings > 1.0:  # Plus d'1$ d'économie par mois
                    recommendations.append({
                        'Type': RecommendationType.VOLUME_TYPE_CHANGE.value,
                        'Description': f"Changer le type de volume de {volume_type} à {recommended_type}",
                        'CurrentConfiguration': f"{volume_type}, {volume_size} Go, {iops} IOPS",
                        'RecommendedConfiguration': f"{recommended_type}, {volume_size} Go",
                        'CurrentCost': current_cost,
                        'ProjectedCost': recommended_cost,
                        'Savings': savings,
                        'SavingsPercentage': (savings / current_cost * 100) if current_cost > 0 else 0,
                        'Confidence': 'MEDIUM',
                        'Reasoning': [
                            f"Faible utilisation du volume ({utilization_metrics.get('UtilizationLevel')})",
                            f"Les IOPS provisionnés ({iops}) sont sous-utilisés",
                            f"gp3 offre jusqu'à 3000 IOPS et 125 Mo/s de débit de base"
                        ]
                    })
                    
                    projected_cost = recommended_cost
            
            # Cas 2: Volume gp2 de grande taille -> gp3
            elif volume_type == 'gp2' and volume_size >= 334:  # À partir de 334 Go, gp3 est généralement moins cher
                recommended_type = 'gp3'
                
                # Calculer le coût avec le nouveau type
                recommended_cost = self._calculate_ebs_cost(
                    recommended_type, volume_size, 3000, 125, region  # Valeurs par défaut pour gp3
                )
                
                savings = current_cost - recommended_cost
                
                # Si l'économie est significative
                if savings > 1.0:  # Plus d'1$ d'économie par mois
                    recommendations.append({
                        'Type': RecommendationType.VOLUME_TYPE_CHANGE.value,
                        'Description': f"Changer le type de volume de {volume_type} à {recommended_type}",
                        'CurrentConfiguration': f"{volume_type}, {volume_size} Go",
                        'RecommendedConfiguration': f"{recommended_type}, {volume_size} Go",
                        'CurrentCost': current_cost,
                        'ProjectedCost': recommended_cost,
                        'Savings': savings,
                        'SavingsPercentage': (savings / current_cost * 100) if current_cost > 0 else 0,
                        'Confidence': 'HIGH',
                        'Reasoning': [
                            f"Volume gp2 de grande taille ({volume_size} Go)",
                            "gp3 offre un meilleur rapport coût/performance pour les volumes de grande taille",
                            f"Économie estimée de {savings:.2f}$ par mois"
                        ]
                    })
                    
                    projected_cost = recommended_cost
        
        # 3. Vérifier si un snapshot peut être créé et le volume supprimé (inactif depuis longtemps)
        days_since_activity = utilization_metrics.get('DaysSinceLastActivity')
        if days_since_activity and days_since_activity > 90:  # Inactif depuis 3 mois
            # Calcul du coût de stockage des snapshots (environ 0,05$ par Go par mois)
            snapshot_cost = volume_size * 0.05
            savings = current_cost - snapshot_cost
            
            if savings > 1.0:  # Plus d'1$ d'économie par mois
                recommendations.append({
                    'Type': RecommendationType.RESOURCE_SNAPSHOT.value,
                    'Description': "Créer un snapshot et supprimer le volume inactif",
                    'CurrentConfiguration': f"{volume_type}, {volume_size} Go",
                    'RecommendedConfiguration': f"Snapshot, {volume_size} Go",
                    'CurrentCost': current_cost,
                    'ProjectedCost': snapshot_cost,
                    'Savings': savings,
                    'SavingsPercentage': (savings / current_cost * 100) if current_cost > 0 else 0,
                    'Confidence': 'MEDIUM',
                    'Reasoning': [
                        f"Volume inactif depuis {days_since_activity} jours",
                        "Créer un snapshot préserve les données tout en réduisant les coûts",
                        f"Économie estimée de {savings:.2f}$ par mois"
                    ]
                })
                
                # Ne pas mettre à jour projected_cost si on a déjà une recommandation de changement de type
                if projected_cost == current_cost:
                    projected_cost = snapshot_cost
        
        # Mettre à jour le résultat avec les recommandations
        result['Recommendations'] = recommendations
        result['ProjectedCost'] = projected_cost
        result['Savings'] = current_cost - projected_cost
        
        if current_cost > 0:
            result['SavingsPercentage'] = (result['Savings'] / current_cost * 100)
        
        return result
    
    def _calculate_ebs_cost(
        self, volume_type: str, size_gb: int, iops: int = 0, throughput: int = 0, region: str = 'us-east-1'
    ) -> float:
        """
        Calcule le coût mensuel d'un volume EBS.
        
        Args:
            volume_type: Type de volume EBS (gp2, gp3, io1, io2, st1, sc1, standard)
            size_gb: Taille du volume en Go
            iops: IOPS provisionnés (pour io1, io2, gp3)
            throughput: Débit provisionné en Mo/s (pour gp3)
            region: Région AWS
            
        Returns:
            Coût mensuel estimé en dollars
        """
        # Prix approximatifs par Go par mois (USD) - à mettre à jour avec des prix réels
        storage_pricing = {
            'gp2': {
                'us-east-1': 0.10,
                'eu-west-1': 0.11,
                'ap-northeast-1': 0.12
            },
            'gp3': {
                'us-east-1': 0.08,
                'eu-west-1': 0.088,
                'ap-northeast-1': 0.096
            },
            'io1': {
                'us-east-1': 0.125,
                'eu-west-1': 0.138,
                'ap-northeast-1': 0.15
            },
            'io2': {
                'us-east-1': 0.125,
                'eu-west-1': 0.138,
                'ap-northeast-1': 0.15
            },
            'st1': {
                'us-east-1': 0.045,
                'eu-west-1': 0.05,
                'ap-northeast-1': 0.054
            },
            'sc1': {
                'us-east-1': 0.025,
                'eu-west-1': 0.028,
                'ap-northeast-1': 0.03
            },
            'standard': {
                'us-east-1': 0.05,
                'eu-west-1': 0.055,
                'ap-northeast-1': 0.06
            }
        }
        
        # Prix des IOPS et du throughput (USD) - à mettre à jour avec des prix réels
        iops_pricing = {
            'io1': {
                'us-east-1': 0.065,  # Par IOPS par mois
                'eu-west-1': 0.072,
                'ap-northeast-1': 0.078
            },
            'io2': {
                'us-east-1': 0.065,  # Par IOPS par mois
                'eu-west-1': 0.072,
                'ap-northeast-1': 0.078
            },
            'gp3': {
                'us-east-1': 0.005,  # Par IOPS par mois au-delà de 3000
                'eu-west-1': 0.0055,
                'ap-northeast-1': 0.006
            }
        }
        
        throughput_pricing = {
            'gp3': {
                'us-east-1': 0.04,  # Par Mo/s par mois au-delà de 125
                'eu-west-1': 0.044,
                'ap-northeast-1': 0.048
            }
        }
        
        # Région par défaut si non spécifiée
        default_region = 'us-east-1'
        
        # Calculer le coût du stockage
        storage_cost_per_gb = storage_pricing.get(volume_type, {}).get(
            region, storage_pricing.get(volume_type, {}).get(default_region, 0)
        )
        storage_cost = storage_cost_per_gb * size_gb
        
        # Calculer le coût des IOPS (si applicable)
        iops_cost = 0
        if volume_type in ['io1', 'io2'] and iops > 0:
            iops_cost_per_iops = iops_pricing.get(volume_type, {}).get(
                region, iops_pricing.get(volume_type, {}).get(default_region, 0)
            )
            iops_cost = iops_cost_per_iops * iops
        elif volume_type == 'gp3' and iops > 3000:
            iops_cost_per_iops = iops_pricing.get('gp3', {}).get(
                region, iops_pricing.get('gp3', {}).get(default_region, 0)
            )
            iops_cost = iops_cost_per_iops * (iops - 3000)  # Seuls les IOPS au-delà de 3000 sont facturés
        
        # Calculer le coût du throughput (si applicable)
        throughput_cost = 0
        if volume_type == 'gp3' and throughput > 125:
            throughput_cost_per_mbs = throughput_pricing.get('gp3', {}).get(
                region, throughput_pricing.get('gp3', {}).get(default_region, 0)
            )
            throughput_cost = throughput_cost_per_mbs * (throughput - 125)  # Seul le débit au-delà de 125 Mo/s est facturé
        
        # Calculer le coût total
        total_cost = storage_cost + iops_cost + throughput_cost
        
        return total_cost
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """
        Calcule le percentile d'une liste de valeurs.
        
        Args:
            values: Liste de valeurs numériques
            percentile: Percentile à calculer (ex: 95 pour P95)
            
        Returns:
            Valeur du percentile
        """
        if not values:
            return 0
            
        sorted_values = sorted(values)
        idx = int(len(sorted_values) * percentile / 100)
        return sorted_values[idx]
    
    def generate_recommendations(self, account_id: str, region: str) -> List[OptimizerRecommendation]:
        """
        Génère des recommandations d'optimisation pour les buckets S3 et volumes EBS.
        
        Args:
            account_id: ID du compte AWS
            region: Région AWS
            
        Returns:
            Liste des recommandations d'optimisation
        """
        recommendations = []
        
        # Analyser les buckets S3
        s3_buckets = self.analyze_s3_buckets(account_id, region)
        
        # Générer des recommandations pour S3
        for bucket in s3_buckets:
            optimization = bucket.get('OptimizationPotential', {})
            bucket_recommendations = optimization.get('Recommendations', [])
            
            for rec in bucket_recommendations:
                recommendation = OptimizerRecommendation(
                    account_id=account_id,
                    region=region,
                    resource_id=bucket.get('BucketName', ''),
                    resource_type=ResourceType.S3_BUCKET.value,
                    recommendation_type=rec.get('Type', ''),
                    current_configuration=rec.get('AffectedStorage', ''),
                    recommended_configuration=rec.get('RecommendedStorage', ''),
                    estimated_savings_monthly=rec.get('Savings', 0),
                    estimated_savings_percentage=rec.get('SavingsPercentage', 0),
                    confidence_level='MEDIUM',
                    reasons=rec.get('Reasoning', []),
                    is_applied=False
                )
                
                recommendations.append(recommendation)
        
        # Analyser les volumes EBS
        ebs_volumes = self.analyze_ebs_volumes(account_id, region)
        
        # Générer des recommandations pour EBS
        for volume in ebs_volumes:
            optimization = volume.get('OptimizationPotential', {})
            volume_recommendations = optimization.get('Recommendations', [])
            
            for rec in volume_recommendations:
                recommendation = OptimizerRecommendation(
                    account_id=account_id,
                    region=region,
                    resource_id=volume.get('VolumeId', ''),
                    resource_type=ResourceType.EBS_VOLUME.value,
                    recommendation_type=rec.get('Type', ''),
                    current_configuration=rec.get('CurrentConfiguration', ''),
                    recommended_configuration=rec.get('RecommendedConfiguration', ''),
                    estimated_savings_monthly=rec.get('Savings', 0),
                    estimated_savings_percentage=rec.get('SavingsPercentage', 0),
                    confidence_level=rec.get('Confidence', 'MEDIUM'),
                    reasons=rec.get('Reasoning', []),
                    is_applied=False
                )
                
                recommendations.append(recommendation)
        
        # Enregistrer les recommandations dans la base de données
        if recommendations:
            try:
                with session() as db_session:
                    for recommendation in recommendations:
                        db_session.add(recommendation)
                    db_session.commit()
            except Exception as e:
                logger.error(f"Erreur lors de l'enregistrement des recommandations: {str(e)}")
        
        return recommendations

def main():
    """Point d'entrée principal (pour tests)"""
    from backend.integrations.aws_client import AwsClient
    from backend.core.analyzers.resource_analyzer import ResourceAnalyzer
    
    # Initialiser les dépendances
    aws_client = AwsClient()
    resource_analyzer = ResourceAnalyzer(aws_client)
    
    # Créer l'optimiseur de stockage
    storage_optimizer = StorageOptimizer(aws_client, resource_analyzer)
    
    # Tester l'analyse des buckets et volumes
    account_id = "123456789012"  # Exemple
    region = "eu-west-1"  # Exemple
    
    recommendations = storage_optimizer.generate_recommendations(account_id, region)
    print(f"Généré {len(recommendations)} recommandations")

if __name__ == "__main__":
    main()