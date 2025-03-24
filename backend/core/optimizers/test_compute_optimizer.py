#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module compute_optimizer.py
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from backend.core.optimizers.compute_optimizer import ComputeOptimizer
from backend.utils.db import OptimizerRecommendation, RecommendationType, ResourceType

class TestComputeOptimizer(unittest.TestCase):
    """Tests pour la classe ComputeOptimizer"""
    
    def setUp(self):
        """Initialiser les mocks et l'optimiseur pour les tests"""
        self.aws_client = MagicMock()
        self.resource_analyzer = MagicMock()
        self.compute_optimizer = ComputeOptimizer(self.aws_client, self.resource_analyzer)
        
        # Configurer les mocks de base
        self.account_id = "123456789012"
        self.region = "eu-west-1"
        
    def test_calculate_percentile(self):
        """Tester le calcul de percentile"""
        # Test avec une liste simple
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        self.assertEqual(self.compute_optimizer._calculate_percentile(values, 50), 5)
        self.assertEqual(self.compute_optimizer._calculate_percentile(values, 90), 9)
        
        # Test avec une liste vide
        self.assertEqual(self.compute_optimizer._calculate_percentile([], 95), 0)
        
    def test_is_instance_underutilized(self):
        """Tester la détection des instances sous-utilisées"""
        # Instance sous-utilisée (CPU < 40%)
        cpu_metrics = {'Average': 15, 'Maximum': 35, 'P95': 30}
        memory_metrics = {'Average': 25, 'Maximum': 45, 'P95': 40}
        self.assertTrue(self.compute_optimizer._is_instance_underutilized(cpu_metrics, memory_metrics))
        
        # Instance correctement utilisée
        cpu_metrics = {'Average': 45, 'Maximum': 65, 'P95': 60}
        memory_metrics = {'Average': 55, 'Maximum': 75, 'P95': 70}
        self.assertFalse(self.compute_optimizer._is_instance_underutilized(cpu_metrics, memory_metrics))
        
        # Pas de données mémoire disponibles, mais CPU sous-utilisé
        cpu_metrics = {'Average': 15, 'Maximum': 35, 'P95': 30}
        memory_metrics = {'Average': None, 'Maximum': None, 'P95': None}
        self.assertTrue(self.compute_optimizer._is_instance_underutilized(cpu_metrics, memory_metrics))
        
    def test_get_smaller_instance(self):
        """Tester la logique de redimensionnement des instances"""
        # Test t3 family
        self.assertEqual(self.compute_optimizer._get_smaller_instance('t3.medium', 1), 't3.small')
        self.assertEqual(self.compute_optimizer._get_smaller_instance('t3.2xlarge', 2), 't3.large')
        
        # Test m5 family
        self.assertEqual(self.compute_optimizer._get_smaller_instance('m5.4xlarge', 1), 'm5.2xlarge')
        
        # Test cas limite (taille minimale)
        self.assertEqual(self.compute_optimizer._get_smaller_instance('t3.nano', 1), None)
        
        # Test famille inconnue
        self.assertEqual(self.compute_optimizer._get_smaller_instance('xyz.large', 1), None)
        
    def test_get_instance_cost(self):
        """Tester le calcul des coûts d'instance"""
        # Test quelques instances dans différentes régions
        self.assertGreater(self.compute_optimizer._get_instance_cost('t3.medium', 'us-east-1'), 0)
        self.assertGreater(self.compute_optimizer._get_instance_cost('m5.large', 'eu-west-1'), 0)
        
        # Vérifier que le prix est plus élevé dans les régions plus chères
        us_price = self.compute_optimizer._get_instance_cost('t3.large', 'us-east-1')
        eu_price = self.compute_optimizer._get_instance_cost('t3.large', 'eu-west-1')
        self.assertGreater(eu_price, us_price)
        
    def test_generate_recommendation_reasons(self):
        """Tester la génération des raisons pour les recommandations"""
        # Instance avec faible utilisation CPU
        instance = {'InstanceId': 'i-12345', 'InstanceType': 't3.xlarge'}
        cpu_metrics = {'Average': 15, 'Maximum': 35, 'P95': 25}
        memory_metrics = {'Average': 20, 'Maximum': 40, 'P95': 30}
        
        reasons = self.compute_optimizer._generate_recommendation_reasons(instance, cpu_metrics, memory_metrics)
        
        # Vérifier que des raisons pertinentes sont générées
        self.assertGreater(len(reasons), 0)
        self.assertTrue(any("CPU moyenne" in reason for reason in reasons))
        
    def test_get_recommended_instance_type(self):
        """Tester la logique de recommandation de type d'instance"""
        # Test cas sous-utilisé (recommande une taille plus petite)
        cpu_metrics = {'Average': 15, 'Maximum': 35, 'P95': 25}
        memory_metrics = {'Average': 20, 'Maximum': 40, 'P95': 30}
        recommended_type, confidence = self.compute_optimizer._get_recommended_instance_type(
            't3.xlarge', cpu_metrics, memory_metrics
        )
        
        self.assertEqual(recommended_type, 't3.large')
        self.assertEqual(confidence, 'MEDIUM')
        
        # Test cas très sous-utilisé (recommande deux tailles plus petites)
        cpu_metrics = {'Average': 8, 'Maximum': 15, 'P95': 12}
        recommended_type, confidence = self.compute_optimizer._get_recommended_instance_type(
            't3.xlarge', cpu_metrics, memory_metrics
        )
        
        self.assertEqual(recommended_type, 't3.medium')
        self.assertEqual(confidence, 'HIGH')
        
    @patch('backend.utils.db.session')
    def test_generate_recommendations(self, mock_session):
        """Tester la génération complète de recommandations"""
        # Configurer le mock pour analyze_ec2_instances
        mock_instances = [
            {
                'ResourceId': 'i-12345',
                'InstanceType': 't3.xlarge',
                'Region': 'eu-west-1',
                'OptimizationPotential': {
                    'Recommendation': 't3.large',
                    'RecommendationType': RecommendationType.RIGHTSIZING.value,
                    'Savings': 60.73,
                    'SavingsPercentage': 50,
                    'Confidence': 'MEDIUM',
                    'Reason': ['CPU utilisation basse']
                }
            }
        ]
        
        # Mocker la méthode analyze_ec2_instances
        self.compute_optimizer.analyze_ec2_instances = MagicMock(return_value=mock_instances)
        
        # Mocker le contexte de session DB
        mock_session_instance = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        
        # Appeler la méthode à tester
        recommendations = self.compute_optimizer.generate_recommendations(self.account_id, self.region)
        
        # Vérifier les résultats
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0].resource_id, 'i-12345')
        self.assertEqual(recommendations[0].recommended_configuration, 't3.large')
        
        # Vérifier que les recommandations sont sauvegardées en DB
        mock_session_instance.add.assert_called()
        mock_session_instance.commit.assert_called_once()
        
    def test_analyze_ec2_instances(self):
        """Tester l'analyse complète des instances EC2"""
        # Configurer les mocks
        mock_instances = [
            {
                'ResourceId': 'i-12345',
                'InstanceType': 't3.xlarge',
                'Region': 'eu-west-1'
            }
        ]
        
        self.resource_analyzer.get_resources.return_value = mock_instances
        
        # Mocker get_instance_cpu_utilization et get_instance_memory_utilization
        self.compute_optimizer.get_instance_cpu_utilization = MagicMock(
            return_value={'Average': 15, 'Maximum': 35, 'P95': 25}
        )
        self.compute_optimizer.get_instance_memory_utilization = MagicMock(
            return_value={'Average': 20, 'Maximum': 40, 'P95': 30}
        )
        
        # Appeler la méthode à tester
        result = self.compute_optimizer.analyze_ec2_instances(self.account_id, self.region)
        
        # Vérifier les résultats
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['ResourceId'], 'i-12345')
        self.assertIn('OptimizationPotential', result[0])
        
        # Vérifier que les méthodes mockées ont été appelées
        self.resource_analyzer.get_resources.assert_called_once()
        self.compute_optimizer.get_instance_cpu_utilization.assert_called_once()
        self.compute_optimizer.get_instance_memory_utilization.assert_called_once()

if __name__ == '__main__':
    unittest.main()