#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cloud Optimizer MVP
cloud_optimizer.py - Point d'entrée principal pour l'optimisation des ressources cloud
"""

import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
import concurrent.futures

# Import des modules de base
from backend.integrations.aws_client import AwsClient
from backend.core.analyzers.resource_analyzer import ResourceAnalyzer
from backend.core.optimizers.storage_optimizer import StorageOptimizer
from backend.core.optimizers.compute_optimizer import ComputeOptimizer
from backend.core.optimizers.cost_optimizer import CostOptimizer
from backend.core.executors.action_executor import ActionExecutor
from backend.utils.db import OptimizerRecommendation, RecommendationType, ResourceType, session

logger = logging.getLogger(__name__)

class CloudOptimizer:
    """
    Classe principale orchestrant le processus complet d'optimisation des ressources cloud.
    Elle intègre les différents optimiseurs spécialisés et coordonne l'exécution des actions.
    """
    
    def __init__(self, 
                 aws_client: AwsClient = None, 
                 resource_analyzer: ResourceAnalyzer = None, 
                 storage_optimizer: StorageOptimizer = None,
                 compute_optimizer: ComputeOptimizer = None,
                 cost_optimizer: CostOptimizer = None,
                 action_executor: ActionExecutor = None):
        """
        Initialise l'optimiseur cloud avec ses dépendances.
        Si les dépendances ne sont pas fournies, elles sont créées automatiquement.
        
        Args:
            aws_client: Client AWS pour accéder aux services
            resource_analyzer: Analyseur de ressources de base
            storage_optimizer: Optimiseur pour les ressources de stockage
            compute_optimizer: Optimiseur pour les ressources de calcul
            cost_optimizer: Optimiseur pour les coûts et les achats réservés
            action_executor: Exécuteur d'actions pour appliquer les recommandations
        """
        # Initialisation des dépendances ou création automatique
        self.aws_client = aws_client or AwsClient()
        self.resource_analyzer = resource_analyzer or ResourceAnalyzer(self.aws_client)
        self.storage_optimizer = storage_optimizer or StorageOptimizer(self.aws_client, self.resource_analyzer)
        self.compute_optimizer = compute_optimizer or ComputeOptimizer(self.aws_client, self.resource_analyzer)
        self.cost_optimizer = cost_optimizer or CostOptimizer(self.aws_client, self.resource_analyzer)
        self.action_executor = action_executor or ActionExecutor(self.aws_client)
        
    def run_all_optimizations(self, 
                             account_ids: List[str],
                             regions: List[str], 
                             resource_types: Set[ResourceType] = None,
                             parallel: bool = True) -> Dict[str, Any]:
        """
        Exécute l'ensemble des analyses d'optimisation sur les comptes et régions spécifiés.
        
        Args:
            account_ids: Liste des IDs de comptes AWS à analyser
            regions: Liste des régions AWS à analyser
            resource_types: Ensemble des types de ressources à analyser (facultatif)
            parallel: Exécution parallèle des analyses (par défaut: True)
            
        Returns:
            Résumé des recommandations générées
        """
        start_time = datetime.now()
        
        # Si aucun type de ressource n'est spécifié, analyser tous les types
        if not resource_types:
            resource_types = set(ResourceType)
        
        recommendations = []
        
        # Déterminer les optimiseurs à exécuter en fonction des types de ressources
        optimizers_to_run = self._determine_optimizers(resource_types)
        
        if parallel:
            # Exécution parallèle pour chaque compte/région
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                
                for account_id in account_ids:
                    for region in regions:
                        for optimizer in optimizers_to_run:
                            futures.append(
                                executor.submit(
                                    self._run_optimizer, optimizer, account_id, region
                                )
                            )
                
                # Récupérer les résultats
                for future in concurrent.futures.as_completed(futures):
                    try:
                        recommendations.extend(future.result())
                    except Exception as e:
                        logger.error(f"Erreur lors de l'exécution d'un optimiseur: {str(e)}")
        else:
            # Exécution séquentielle
            for account_id in account_ids:
                for region in regions:
                    for optimizer in optimizers_to_run:
                        try:
                            recommendations.extend(
                                self._run_optimizer(optimizer, account_id, region)
                            )
                        except Exception as e:
                            logger.error(f"Erreur lors de l'exécution de l'optimiseur {optimizer.__class__.__name__} pour {account_id}/{region}: {str(e)}")
        
        # Calculer les statistiques
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        summary = self._summarize_recommendations(recommendations, account_ids, regions, duration)
        
        return summary
    
    def _determine_optimizers(self, resource_types: Set[ResourceType]) -> List[Any]:
        """
        Détermine les optimiseurs à exécuter en fonction des types de ressources.
        
        Args:
            resource_types: Ensemble des types de ressources à analyser
            
        Returns:
            Liste des optimiseurs à exécuter
        """
        optimizers = []
        
        # Regrouper les types de ressources par optimiseur
        storage_types = {ResourceType.S3_BUCKET, ResourceType.EBS_VOLUME}
        compute_types = {ResourceType.EC2_INSTANCE, ResourceType.AUTO_SCALING_GROUP, ResourceType.LAMBDA_FUNCTION}
        cost_types = {ResourceType.RESERVED_INSTANCE, ResourceType.SAVINGS_PLAN}
        
        # Ajouter les optimiseurs appropriés
        if any(rt in resource_types for rt in storage_types):
            optimizers.append(self.storage_optimizer)
            
        if any(rt in resource_types for rt in compute_types):
            optimizers.append(self.compute_optimizer)
            
        if any(rt in resource_types for rt in cost_types):
            optimizers.append(self.cost_optimizer)
        
        return optimizers
    
    def _run_optimizer(self, optimizer: Any, account_id: str, region: str) -> List[OptimizerRecommendation]:
        """
        Exécute un optimiseur spécifique pour un compte et une région.
        
        Args:
            optimizer: L'optimiseur à exécuter
            account_id: ID du compte AWS
            region: Région AWS
            
        Returns:
            Liste des recommandations générées
        """
        logger.info(f"Exécution de {optimizer.__class__.__name__} pour {account_id}/{region}")
        return optimizer.generate_recommendations(account_id, region)
    
    def _summarize_recommendations(self, 
                                  recommendations: List[OptimizerRecommendation], 
                                  account_ids: List[str],
                                  regions: List[str],
                                  duration: float) -> Dict[str, Any]:
        """
        Génère un résumé des recommandations.
        
        Args:
            recommendations: Liste de toutes les recommandations générées
            account_ids: Liste des IDs de comptes analysés
            regions: Liste des régions analysées
            duration: Durée d'exécution en secondes
            
        Returns:
            Résumé des recommandations
        """
        # Compter les recommandations par type
        recommendation_counts = {}
        for rec in recommendations:
            rec_type = rec.recommendation_type
            if rec_type not in recommendation_counts:
                recommendation_counts[rec_type] = 0
            recommendation_counts[rec_type] += 1
        
        # Calculer les économies potentielles totales
        total_savings = sum(rec.estimated_savings_monthly for rec in recommendations)
        
        # Créer le résumé
        summary = {
            'total_recommendations': len(recommendations),
            'accounts_analyzed': account_ids,
            'regions_analyzed': regions,
            'execution_time_seconds': duration,
            'total_monthly_savings': total_savings,
            'recommendation_types': recommendation_counts,
            'timestamp': datetime.now().isoformat()
        }
        
        return summary
    
    def execute_recommendations(self, 
                               recommendation_ids: List[int] = None,
                               recommendation_types: List[str] = None,
                               resource_types: List[str] = None,
                               min_savings_percentage: float = None,
                               max_recommendations: int = None,
                               parallel: bool = True) -> Dict[str, Any]:
        """
        Exécute les recommandations d'optimisation avec divers filtres possibles.
        
        Args:
            recommendation_ids: Liste d'IDs spécifiques de recommandations à exécuter
            recommendation_types: Filtrer par types de recommandations
            resource_types: Filtrer par types de ressources
            min_savings_percentage: Pourcentage minimum d'économies
            max_recommendations: Nombre maximum de recommandations à exécuter
            parallel: Exécuter les actions en parallèle
            
        Returns:
            Résumé des actions exécutées
        """
        # Récupérer les recommandations selon les filtres
        recommendations_to_execute = self._get_filtered_recommendations(
            recommendation_ids, recommendation_types, resource_types, min_savings_percentage, max_recommendations
        )
        
        if not recommendations_to_execute:
            return {
                'total': 0,
                'message': "Aucune recommandation ne correspond aux critères spécifiés"
            }
        
        # Exécuter les actions
        if parallel:
            return self.action_executor.execute_bulk_actions([rec.id for rec in recommendations_to_execute])
        else:
            # Exécution séquentielle
            results = {
                'total': len(recommendations_to_execute),
                'succeeded': 0,
                'failed': 0,
                'skipped': 0,
                'details': []
            }
            
            for rec in recommendations_to_execute:
                result = self.action_executor.execute_action(rec.id)
                
                # Compter les résultats par statut
                if result.get('status') == 'SUCCEEDED':
                    results['succeeded'] += 1
                elif result.get('status') == 'FAILED':
                    results['failed'] += 1
                elif result.get('status') == 'SKIPPED':
                    results['skipped'] += 1
                
                # Ajouter le détail du résultat
                results['details'].append({
                    'recommendation_id': rec.id,
                    'status': result.get('status'),
                    'message': result.get('message')
                })
            
            return results
    
    def _get_filtered_recommendations(self,
                                     recommendation_ids: List[int] = None,
                                     recommendation_types: List[str] = None,
                                     resource_types: List[str] = None,
                                     min_savings_percentage: float = None,
                                     max_recommendations: int = None) -> List[OptimizerRecommendation]:
        """
        Récupère les recommandations filtrées selon divers critères.
        
        Args:
            recommendation_ids: Liste d'IDs spécifiques de recommandations
            recommendation_types: Filtrer par types de recommandations
            resource_types: Filtrer par types de ressources
            min_savings_percentage: Pourcentage minimum d'économies
            max_recommendations: Nombre maximum de recommandations à récupérer
            
        Returns:
            Liste des recommandations correspondant aux filtres
        """
        try:
            with session() as db_session:
                query = db_session.query(OptimizerRecommendation).filter(
                    OptimizerRecommendation.is_applied == False
                )
                
                # Appliquer les filtres
                if recommendation_ids:
                    query = query.filter(OptimizerRecommendation.id.in_(recommendation_ids))
                
                if recommendation_types:
                    query = query.filter(OptimizerRecommendation.recommendation_type.in_(recommendation_types))
                
                if resource_types:
                    query = query.filter(OptimizerRecommendation.resource_type.in_(resource_types))
                
                if min_savings_percentage:
                    query = query.filter(OptimizerRecommendation.estimated_savings_percentage >= min_savings_percentage)
                
                # Trier par économies
                query = query.order_by(OptimizerRecommendation.estimated_savings_monthly.desc())
                
                # Limiter le nombre
                if max_recommendations:
                    query = query.limit(max_recommendations)
                
                return query.all()
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des recommandations filtrées: {str(e)}")
            return []
    
    def generate_optimization_report(self, 
                                    account_ids: List[str] = None,
                                    regions: List[str] = None,
                                    days: int = 30) -> Dict[str, Any]:
        """
        Génère un rapport d'optimisation sur une période donnée.
        
        Args:
            account_ids: Liste des IDs de comptes (facultatif)
            regions: Liste des régions (facultatif)
            days: Nombre de jours à inclure dans le rapport
            
        Returns:
            Rapport d'optimisation complet
        """
        start_date = datetime.now() - timedelta(days=days)
        
        try:
            with session() as db_session:
                # Construire la requête de base
                query = db_session.query(OptimizerRecommendation).filter(
                    OptimizerRecommendation.created_at >= start_date
                )
                
                # Appliquer les filtres facultatifs
                if account_ids:
                    query = query.filter(OptimizerRecommendation.account_id.in_(account_ids))
                
                if regions:
                    query = query.filter(OptimizerRecommendation.region.in_(regions))
                
                # Récupérer toutes les recommandations
                recommendations = query.all()
                
                # Générer les statistiques
                total_recommendations = len(recommendations)
                applied_recommendations = sum(1 for rec in recommendations if rec.is_applied)
                potential_savings = sum(rec.estimated_savings_monthly for rec in recommendations)
                realized_savings = sum(rec.estimated_savings_monthly for rec in recommendations if rec.is_applied)
                
                # Regrouper par type de ressource
                resource_type_stats = {}
                for rec in recommendations:
                    rt = rec.resource_type
                    if rt not in resource_type_stats:
                        resource_type_stats[rt] = {
                            'count': 0,
                            'applied': 0,
                            'potential_savings': 0,
                            'realized_savings': 0
                        }
                    
                    stats = resource_type_stats[rt]
                    stats['count'] += 1
                    stats['potential_savings'] += rec.estimated_savings_monthly
                    
                    if rec.is_applied:
                        stats['applied'] += 1
                        stats['realized_savings'] += rec.estimated_savings_monthly
                
                # Regrouper par type de recommandation
                recommendation_type_stats = {}
                for rec in recommendations:
                    rt = rec.recommendation_type
                    if rt not in recommendation_type_stats:
                        recommendation_type_stats[rt] = {
                            'count': 0,
                            'applied': 0,
                            'potential_savings': 0,
                            'realized_savings': 0
                        }
                    
                    stats = recommendation_type_stats[rt]
                    stats['count'] += 1
                    stats['potential_savings'] += rec.estimated_savings_monthly
                    
                    if rec.is_applied:
                        stats['applied'] += 1
                        stats['realized_savings'] += rec.estimated_savings_monthly
                
                # Créer le rapport complet
                report = {
                    'period': {
                        'start_date': start_date.isoformat(),
                        'end_date': datetime.now().isoformat(),
                        'days': days
                    },
                    'summary': {
                        'total_recommendations': total_recommendations,
                        'applied_recommendations': applied_recommendations,
                        'application_rate': (applied_recommendations / total_recommendations * 100) if total_recommendations > 0 else 0,
                        'potential_monthly_savings': potential_savings,
                        'realized_monthly_savings': realized_savings,
                        'savings_realization_rate': (realized_savings / potential_savings * 100) if potential_savings > 0 else 0
                    },
                    'by_resource_type': resource_type_stats,
                    'by_recommendation_type': recommendation_type_stats,
                    'generation_timestamp': datetime.now().isoformat()
                }
                
                return report
                
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport d'optimisation: {str(e)}")
            return {
                'error': str(e),
                'message': "Échec de la génération du rapport d'optimisation"
            }

def main():
    """Point d'entrée principal de l'application"""
    # Exemple d'utilisation du CloudOptimizer
    
    # Initialisation de l'optimiseur cloud
    cloud_optimizer = CloudOptimizer()
    
    # Comptes et régions à analyser
    account_ids = ["123456789012"]  # Exemple
    regions = ["eu-west-1", "us-east-1"]  # Exemple
    
    # Exécuter l'analyse complète
    results = cloud_optimizer.run_all_optimizations(
        account_ids=account_ids,
        regions=regions
    )
    
    print(f"Analyse terminée: {len(results.get('accounts_analyzed', []))} comptes, "
          f"{len(results.get('regions_analyzed', []))} régions")
    print(f"Recommandations générées: {results.get('total_recommendations', 0)}")
    print(f"Économies mensuelles potentielles: {results.get('total_monthly_savings', 0):.2f} $")
    
    # Exécuter automatiquement les recommandations avec plus de 20% d'économies
    action_results = cloud_optimizer.execute_recommendations(
        min_savings_percentage=20.0,
        max_recommendations=10  # Limiter à 10 recommandations pour l'exemple
    )
    
    print(f"Actions exécutées: {action_results.get('total', 0)}")
    print(f"Réussies: {action_results.get('succeeded', 0)}")
    print(f"Échouées: {action_results.get('failed', 0)}")
    print(f"Ignorées: {action_results.get('skipped', 0)}")
    
    # Générer un rapport pour les 30 derniers jours
    report = cloud_optimizer.generate_optimization_report(days=30)
    print(f"Rapport généré pour la période: {report.get('period', {}).get('start_date')} à {report.get('period', {}).get('end_date')}")
    print(f"Taux de réalisation des économies: {report.get('summary', {}).get('savings_realization_rate', 0):.2f}%")

if __name__ == "__main__":
    main()