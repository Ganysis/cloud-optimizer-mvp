#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cloud Optimizer MVP
compute_optimizer.py - Module d'optimisation des ressources de calcul (EC2, Lambda)
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

# Import des modules de base
from backend.integrations.aws_client import AwsClient
from backend.core.analyzers.resource_analyzer import ResourceAnalyzer
from backend.utils.db import OptimizerRecommendation, RecommendationType, ResourceType, session

logger = logging.getLogger(__name__)

class ComputeOptimizer:
    """
    Classe spécialisée dans l'analyse et l'optimisation des ressources de calcul AWS
    telles que les instances EC2 et les fonctions Lambda.
    """
    
    def __init__(self, aws_client: AwsClient, resource_analyzer: ResourceAnalyzer):
        """
        Initialise l'optimiseur de calcul.
        
        Args:
            aws_client: Client AWS pour accéder aux services
            resource_analyzer: Analyseur de ressources de base
        """
        self.aws_client = aws_client
        self.resource_analyzer = resource_analyzer
        
    def analyze_ec2_instances(self, account_id: str, region: str) -> List[Dict[str, Any]]:
        """
        Analyse les instances EC2 et identifie les opportunités d'optimisation.
        
        Args:
            account_id: ID du compte AWS
            region: Région AWS à analyser
            
        Returns:
            Liste des instances EC2 avec des métriques d'analyse
        """
        # Récupérer les instances EC2 depuis l'analyseur de ressources
        instances = self.resource_analyzer.get_resources(
            account_id=account_id,
            region=region,
            resource_type=ResourceType.EC2_INSTANCE
        )
        
        enriched_instances = []
        
        for instance in instances:
            instance_id = instance['ResourceId']
            
            # Récupérer les métriques CloudWatch pour l'instance
            cpu_utilization = self.get_instance_cpu_utilization(instance_id, account_id, region)
            memory_utilization = self.get_instance_memory_utilization(instance_id, account_id, region)
            
            # Enrichir les données d'instance avec les métriques
            instance_data = {
                **instance,
                'CpuUtilization': cpu_utilization,
                'MemoryUtilization': memory_utilization,
                'OptimizationPotential': self._calculate_optimization_potential(
                    instance, cpu_utilization, memory_utilization
                )
            }
            
            enriched_instances.append(instance_data)
            
        return enriched_instances
    
    def get_instance_cpu_utilization(
        self, instance_id: str, account_id: str, region: str, days: int = 14
    ) -> Dict[str, Any]:
        """
        Récupère l'utilisation CPU d'une instance EC2 sur une période donnée.
        
        Args:
            instance_id: ID de l'instance EC2
            account_id: ID du compte AWS
            region: Région AWS
            days: Nombre de jours d'historique à analyser
            
        Returns:
            Dictionnaire contenant les statistiques d'utilisation CPU
        """
        try:
            # Récupérer les métriques CloudWatch via le client AWS
            metrics = self.aws_client.get_cloudwatch_metrics(
                account_id=account_id,
                region=region,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                period=3600,  # Agrégation horaire
                days=days
            )
            
            # Calculer les statistiques d'utilisation
            if metrics and 'Datapoints' in metrics:
                datapoints = metrics['Datapoints']
                if not datapoints:
                    return {'Average': 0, 'Maximum': 0, 'Minimum': 0, 'P95': 0}
                
                values = [dp['Average'] for dp in datapoints]
                
                return {
                    'Average': sum(values) / len(values) if values else 0,
                    'Maximum': max(values) if values else 0,
                    'Minimum': min(values) if values else 0,
                    'P95': self._calculate_percentile(values, 95) if values else 0
                }
                
            return {'Average': 0, 'Maximum': 0, 'Minimum': 0, 'P95': 0}
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métriques CPU pour {instance_id}: {str(e)}")
            return {'Average': 0, 'Maximum': 0, 'Minimum': 0, 'P95': 0, 'Error': str(e)}
    
    def get_instance_memory_utilization(
        self, instance_id: str, account_id: str, region: str, days: int = 14
    ) -> Dict[str, Any]:
        """
        Récupère l'utilisation mémoire d'une instance EC2 sur une période donnée.
        Note: Nécessite CloudWatch Agent pour être configuré sur l'instance.
        
        Args:
            instance_id: ID de l'instance EC2
            account_id: ID du compte AWS
            region: Région AWS
            days: Nombre de jours d'historique à analyser
            
        Returns:
            Dictionnaire contenant les statistiques d'utilisation mémoire
        """
        try:
            # Vérifier si les métriques mémoire sont disponibles via CloudWatch Agent
            metrics = self.aws_client.get_cloudwatch_metrics(
                account_id=account_id,
                region=region,
                namespace='CWAgent',
                metric_name='mem_used_percent',
                dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                period=3600,
                days=days
            )
            
            # Traiter les métriques si disponibles
            if metrics and 'Datapoints' in metrics and metrics['Datapoints']:
                datapoints = metrics['Datapoints']
                values = [dp['Average'] for dp in datapoints]
                
                return {
                    'Average': sum(values) / len(values) if values else 0,
                    'Maximum': max(values) if values else 0,
                    'Minimum': min(values) if values else 0,
                    'P95': self._calculate_percentile(values, 95) if values else 0
                }
            
            # Si pas de métriques mémoire disponibles via CloudWatch Agent
            logger.warning(f"Pas de métriques mémoire disponibles pour {instance_id}")
            return {'Average': None, 'Maximum': None, 'Minimum': None, 'P95': None}
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métriques mémoire pour {instance_id}: {str(e)}")
            return {'Average': None, 'Maximum': None, 'Minimum': None, 'P95': None, 'Error': str(e)}
    
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
    
    def _calculate_optimization_potential(
        self, instance: Dict[str, Any], cpu_metrics: Dict[str, Any], memory_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calcule le potentiel d'optimisation d'une instance EC2.
        
        Args:
            instance: Données de l'instance EC2
            cpu_metrics: Métriques d'utilisation CPU
            memory_metrics: Métriques d'utilisation mémoire
            
        Returns:
            Dictionnaire contenant le potentiel d'optimisation
        """
        # Valeurs par défaut
        result = {
            'Recommendation': None,
            'RecommendationType': None,
            'CurrentCost': 0,
            'ProjectedCost': 0,
            'Savings': 0,
            'SavingsPercentage': 0,
            'Confidence': 'MEDIUM',
            'Reason': []
        }
        
        # Extraire les détails de l'instance pour l'analyse
        instance_type = instance.get('InstanceType', '')
        current_cost = self._get_instance_cost(instance_type, instance.get('Region', ''))
        result['CurrentCost'] = current_cost
        
        # Vérifier si l'instance est sous-utilisée
        is_underutilized = self._is_instance_underutilized(cpu_metrics, memory_metrics)
        
        if is_underutilized:
            # Déterminer le type d'instance recommandé
            recommended_type, confidence = self._get_recommended_instance_type(
                instance_type, cpu_metrics, memory_metrics
            )
            
            if recommended_type and recommended_type != instance_type:
                projected_cost = self._get_instance_cost(recommended_type, instance.get('Region', ''))
                savings = current_cost - projected_cost
                
                result.update({
                    'Recommendation': recommended_type,
                    'RecommendationType': RecommendationType.RIGHTSIZING.value,
                    'ProjectedCost': projected_cost,
                    'Savings': savings,
                    'SavingsPercentage': (savings / current_cost * 100) if current_cost > 0 else 0,
                    'Confidence': confidence,
                    'Reason': self._generate_recommendation_reasons(instance, cpu_metrics, memory_metrics)
                })
        
        return result
    
    def _is_instance_underutilized(
        self, cpu_metrics: Dict[str, Any], memory_metrics: Dict[str, Any]
    ) -> bool:
        """
        Détermine si une instance est sous-utilisée en fonction des métriques.
        
        Args:
            cpu_metrics: Métriques d'utilisation CPU
            memory_metrics: Métriques d'utilisation mémoire
            
        Returns:
            True si l'instance est sous-utilisée, False sinon
        """
        # Vérifier l'utilisation CPU
        if cpu_metrics and 'P95' in cpu_metrics:
            # Si 95% du temps, l'utilisation CPU est inférieure à 40%
            if cpu_metrics['P95'] < 40:
                return True
                
        # Vérifier l'utilisation mémoire si disponible
        if memory_metrics and memory_metrics.get('P95') is not None:
            if memory_metrics['P95'] < 40:
                return True
                
        return False
    
    def _get_recommended_instance_type(
        self, current_type: str, cpu_metrics: Dict[str, Any], memory_metrics: Dict[str, Any]
    ) -> Tuple[Optional[str], str]:
        """
        Détermine le type d'instance recommandé en fonction des métriques d'utilisation.
        
        Args:
            current_type: Type d'instance actuel
            cpu_metrics: Métriques d'utilisation CPU
            memory_metrics: Métriques d'utilisation mémoire
            
        Returns:
            Tuple contenant le type d'instance recommandé et le niveau de confiance
        """
        # Mapping simplifié des types d'instances EC2 (à compléter avec une base de données plus complète)
        instance_family = current_type.split('.')[0]
        
        # Simplification: pour le moment, on se base principalement sur l'utilisation CPU
        if cpu_metrics and 'P95' in cpu_metrics:
            p95_cpu = cpu_metrics['P95']
            
            # Logique de redimensionnement simplifiée
            if p95_cpu < 20:
                # Très sous-utilisé, recommander deux tailles en dessous
                return self._get_smaller_instance(current_type, 2), 'HIGH'
            elif p95_cpu < 40:
                # Sous-utilisé, recommander une taille en dessous
                return self._get_smaller_instance(current_type, 1), 'MEDIUM'
                
        return None, 'LOW'
    
    def _get_smaller_instance(self, current_type: str, steps: int = 1) -> Optional[str]:
        """
        Obtient un type d'instance plus petit que le type actuel.
        
        Args:
            current_type: Type d'instance actuel
            steps: Nombre de niveaux à réduire
            
        Returns:
            Type d'instance recommandé
        """
        # Mapping (simplifié) des tailles d'instances par famille
        size_rankings = {
            't3': ['nano', 'micro', 'small', 'medium', 'large', 'xlarge', '2xlarge'],
            'm5': ['large', 'xlarge', '2xlarge', '4xlarge', '8xlarge', '12xlarge', '16xlarge', '24xlarge'],
            'c5': ['large', 'xlarge', '2xlarge', '4xlarge', '9xlarge', '18xlarge', '24xlarge'],
            'r5': ['large', 'xlarge', '2xlarge', '4xlarge', '8xlarge', '12xlarge', '24xlarge'],
            # Ajouter d'autres familles selon les besoins
        }
        
        parts = current_type.split('.')
        if len(parts) != 2:
            return None
            
        family, size = parts
        
        # Vérifier si la famille est dans notre mapping
        if family not in size_rankings:
            return None
            
        sizes = size_rankings[family]
        if size not in sizes:
            return None
            
        current_index = sizes.index(size)
        
        # Calculer le nouvel index
        new_index = max(0, current_index - steps)
        
        # Si nous sommes déjà au niveau le plus bas
        if new_index == current_index:
            return None
            
        return f"{family}.{sizes[new_index]}"
    
    def _get_instance_cost(self, instance_type: str, region: str) -> float:
        """
        Obtient le coût mensuel estimé d'un type d'instance dans une région donnée.
        
        Args:
            instance_type: Type d'instance EC2
            region: Région AWS
            
        Returns:
            Coût mensuel estimé
        """
        # Dans un système réel, cette méthode interrogerait une API de pricing
        # ou une base de données de prix. Pour le MVP, nous utilisons des valeurs simplifiées.
        
        # Prix mensuel simplifié (à remplacer par une vraie source de prix)
        pricing_map = {
            't3.nano': 3.80,
            't3.micro': 7.59,
            't3.small': 15.18,
            't3.medium': 30.37,
            't3.large': 60.74,
            't3.xlarge': 121.47,
            't3.2xlarge': 242.95,
            'm5.large': 69.35,
            'm5.xlarge': 138.70,
            'm5.2xlarge': 277.40,
            # Ajouter d'autres types selon les besoins
        }
        
        # Appliquer un multiplicateur régional simplifié
        region_multipliers = {
            'us-east-1': 1.0,    # Région de référence
            'eu-west-1': 1.1,    # 10% plus cher
            'ap-northeast-1': 1.2, # 20% plus cher
            # Ajouter d'autres régions selon les besoins
        }
        
        base_cost = pricing_map.get(instance_type, 0)
        multiplier = region_multipliers.get(region, 1.0)
        
        return base_cost * multiplier
    
    def _generate_recommendation_reasons(
        self, instance: Dict[str, Any], cpu_metrics: Dict[str, Any], memory_metrics: Dict[str, Any]
    ) -> List[str]:
        """
        Génère des explications pour la recommandation d'optimisation.
        
        Args:
            instance: Données de l'instance EC2
            cpu_metrics: Métriques d'utilisation CPU
            memory_metrics: Métriques d'utilisation mémoire
            
        Returns:
            Liste des raisons justifiant la recommandation
        """
        reasons = []
        
        if cpu_metrics and 'Average' in cpu_metrics:
            avg_cpu = cpu_metrics['Average']
            if avg_cpu < 20:
                reasons.append(f"L'utilisation CPU moyenne est très basse ({avg_cpu:.1f}%)")
            elif avg_cpu < 40:
                reasons.append(f"L'utilisation CPU moyenne est basse ({avg_cpu:.1f}%)")
                
        if cpu_metrics and 'P95' in cpu_metrics:
            p95_cpu = cpu_metrics['P95']
            if p95_cpu < 40:
                reasons.append(f"95% du temps, l'utilisation CPU est inférieure à {p95_cpu:.1f}%")
                
        if memory_metrics and memory_metrics.get('Average') is not None:
            avg_mem = memory_metrics['Average']
            if avg_mem < 30:
                reasons.append(f"L'utilisation mémoire moyenne est basse ({avg_mem:.1f}%)")
                
        # Ajouter d'autres raisons pertinentes selon les cas
                
        return reasons
    
    def generate_recommendations(self, account_id: str, region: str) -> List[OptimizerRecommendation]:
        """
        Génère des recommandations d'optimisation pour les instances EC2.
        
        Args:
            account_id: ID du compte AWS
            region: Région AWS
            
        Returns:
            Liste des recommandations d'optimisation
        """
        recommendations = []
        
        # Analyser les instances EC2
        analyzed_instances = self.analyze_ec2_instances(account_id, region)
        
        # Générer des recommandations
        for instance in analyzed_instances:
            optimization = instance.get('OptimizationPotential', {})
            
            # Si une recommandation a été trouvée
            if optimization.get('Recommendation'):
                # Créer une recommandation dans la base de données
                recommendation = OptimizerRecommendation(
                    account_id=account_id,
                    region=region,
                    resource_id=instance.get('ResourceId', ''),
                    resource_type=ResourceType.EC2_INSTANCE.value,
                    recommendation_type=optimization.get('RecommendationType', ''),
                    current_configuration=instance.get('InstanceType', ''),
                    recommended_configuration=optimization.get('Recommendation', ''),
                    estimated_savings_monthly=optimization.get('Savings', 0),
                    estimated_savings_percentage=optimization.get('SavingsPercentage', 0),
                    confidence_level=optimization.get('Confidence', 'MEDIUM'),
                    reasons=optimization.get('Reason', []),
                    is_applied=False
                )
                
                # Ajouter à la liste des recommandations
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
    
    def analyze_lambda_functions(self, account_id: str, region: str) -> List[Dict[str, Any]]:
        """
        Analyse les fonctions Lambda et identifie les opportunités d'optimisation.
        
        Args:
            account_id: ID du compte AWS
            region: Région AWS à analyser
            
        Returns:
            Liste des fonctions Lambda avec des métriques d'analyse
        """
        # Récupérer les fonctions Lambda depuis l'analyseur de ressources
        lambda_functions = self.resource_analyzer.get_resources(
            account_id=account_id,
            region=region,
            resource_type=ResourceType.LAMBDA_FUNCTION
        )
        
        enriched_functions = []
        
        for function in lambda_functions:
            function_name = function.get('FunctionName', '')
            
            # Récupérer les métriques CloudWatch pour la fonction
            memory_metrics = self.get_lambda_memory_utilization(function_name, account_id, region)
            duration_metrics = self.get_lambda_duration(function_name, account_id, region)
            
            # Enrichir les données de fonction avec les métriques
            function_data = {
                **function,
                'MemoryUtilization': memory_metrics,
                'Duration': duration_metrics,
                'OptimizationPotential': self._calculate_lambda_optimization_potential(
                    function, memory_metrics, duration_metrics
                )
            }
            
            enriched_functions.append(function_data)
            
        return enriched_functions
    
    def get_lambda_memory_utilization(
        self, function_name: str, account_id: str, region: str, days: int = 14
    ) -> Dict[str, Any]:
        """
        Récupère l'utilisation mémoire d'une fonction Lambda sur une période donnée.
        
        Args:
            function_name: Nom de la fonction Lambda
            account_id: ID du compte AWS
            region: Région AWS
            days: Nombre de jours d'historique à analyser
            
        Returns:
            Dictionnaire contenant les statistiques d'utilisation mémoire
        """
        # Similaire à la méthode pour les instances EC2, mais adaptée aux Lambda
        # TODO: Implémenter cette méthode
        return {'Average': 0, 'Maximum': 0, 'P95': 0}
    
    def get_lambda_duration(
        self, function_name: str, account_id: str, region: str, days: int = 14
    ) -> Dict[str, Any]:
        """
        Récupère la durée d'exécution d'une fonction Lambda sur une période donnée.
        
        Args:
            function_name: Nom de la fonction Lambda
            account_id: ID du compte AWS
            region: Région AWS
            days: Nombre de jours d'historique à analyser
            
        Returns:
            Dictionnaire contenant les statistiques de durée d'exécution
        """
        # TODO: Implémenter cette méthode
        return {'Average': 0, 'Maximum': 0, 'P95': 0}
    
    def _calculate_lambda_optimization_potential(
        self, function: Dict[str, Any], memory_metrics: Dict[str, Any], duration_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calcule le potentiel d'optimisation d'une fonction Lambda.
        
        Args:
            function: Données de la fonction Lambda
            memory_metrics: Métriques d'utilisation mémoire
            duration_metrics: Métriques de durée d'exécution
            
        Returns:
            Dictionnaire contenant le potentiel d'optimisation
        """
        # TODO: Implémenter cette méthode
        return {
            'Recommendation': None,
            'RecommendationType': None,
            'CurrentCost': 0,
            'ProjectedCost': 0,
            'Savings': 0,
            'SavingsPercentage': 0,
            'Confidence': 'LOW',
            'Reason': []
        }

def main():
    """Point d'entrée principal (pour tests)"""
    from backend.integrations.aws_client import AwsClient
    from backend.core.analyzers.resource_analyzer import ResourceAnalyzer
    
    # Initialiser les dépendances
    aws_client = AwsClient()
    resource_analyzer = ResourceAnalyzer(aws_client)
    
    # Créer l'optimiseur de calcul
    compute_optimizer = ComputeOptimizer(aws_client, resource_analyzer)
    
    # Tester l'analyse des instances
    account_id = "123456789012"  # Exemple
    region = "eu-west-1"  # Exemple
    
    recommendations = compute_optimizer.generate_recommendations(account_id, region)
    print(f"Généré {len(recommendations)} recommandations")

if __name__ == "__main__":
    main()