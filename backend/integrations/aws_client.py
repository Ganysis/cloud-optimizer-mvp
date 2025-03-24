#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cloud Optimizer MVP
aws_client.py - Client AWS pour les intégrations
"""

import os
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class AWSClient:
    """Client unifié pour accéder aux services AWS"""
    
    def __init__(self, profile_name=None, region=None):
        """
        Initialise le client AWS.
        
        Args:
            profile_name: Nom du profil AWS à utiliser (optionnel)
            region: Région AWS à utiliser (défaut: us-east-1)
        """
        self.profile_name = profile_name
        self.region = region or 'us-east-1'
        self.session = None
        self.clients = {}
        
        self._initialize_session()
    
    def _initialize_session(self):
        """Initialise la session AWS."""
        try:
            if self.profile_name:
                self.session = boto3.Session(profile_name=self.profile_name, region_name=self.region)
            else:
                self.session = boto3.Session(region_name=self.region)
            
            logger.info(f"Session AWS initialisée pour la région {self.region}")
        except ClientError as e:
            logger.error(f"Erreur lors de l'initialisation de la session AWS: {e}")
            raise
    
    def get_client(self, service_name):
        """
        Obtient un client pour un service AWS spécifique.
        
        Args:
            service_name: Nom du service AWS (ec2, s3, rds, etc.)
            
        Returns:
            Un client boto3 pour le service demandé
        """
        if service_name not in self.clients:
            self.clients[service_name] = self.session.client(service_name)
        
        return self.clients[service_name]
    
    def get_resource(self, service_name):
        """
        Obtient une ressource pour un service AWS spécifique.
        
        Args:
            service_name: Nom du service AWS (ec2, s3, rds, etc.)
            
        Returns:
            Une ressource boto3 pour le service demandé
        """
        return self.session.resource(service_name)
    
    # MÉTHODES UTILITAIRES POUR EC2
    
    def get_ec2_instances(self, filters=None):
        """
        Récupère la liste des instances EC2.
        
        Args:
            filters: Filtres à appliquer (optionnel)
            
        Returns:
            Liste des instances EC2
        """
        ec2_resource = self.get_resource('ec2')
        instances = ec2_resource.instances.all() if not filters else ec2_resource.instances.filter(Filters=filters)
        
        return list(instances)
    
    def get_instance_details(self, instance_id):
        """
        Récupère les détails d'une instance EC2.
        
        Args:
            instance_id: ID de l'instance EC2
            
        Returns:
            Détails de l'instance EC2
        """
        ec2_resource = self.get_resource('ec2')
        instance = ec2_resource.Instance(instance_id)
        
        return instance
    
    # MÉTHODES UTILITAIRES POUR S3
    
    def list_buckets(self):
        """
        Liste tous les buckets S3.
        
        Returns:
            Liste des buckets S3
        """
        s3_client = self.get_client('s3')
        response = s3_client.list_buckets()
        
        return response.get('Buckets', [])
    
    def get_bucket_size(self, bucket_name):
        """
        Calcule la taille totale d'un bucket S3.
        
        Args:
            bucket_name: Nom du bucket S3
            
        Returns:
            Taille du bucket en octets
        """
        s3_resource = self.get_resource('s3')
        bucket = s3_resource.Bucket(bucket_name)
        
        total_size = 0
        for obj in bucket.objects.all():
            total_size += obj.size
        
        return total_size
    
    # MÉTHODES UTILITAIRES POUR RDS
    
    def list_rds_instances(self):
        """
        Liste toutes les instances RDS.
        
        Returns:
            Liste des instances RDS
        """
        rds_client = self.get_client('rds')
        response = rds_client.describe_db_instances()
        
        return response.get('DBInstances', [])
    
    # MÉTHODES UTILITAIRES POUR CLOUDWATCH (MÉTRIQUES)
    
    def get_metric_data(self, namespace, metric_name, dimensions, start_time, end_time, period=300, stat='Average'):
        """
        Récupère les données métriques depuis CloudWatch.
        
        Args:
            namespace: Espace de nom de la métrique (AWS/EC2, AWS/RDS, etc.)
            metric_name: Nom de la métrique
            dimensions: Dimensions de la métrique
            start_time: Heure de début
            end_time: Heure de fin
            period: Période en secondes (défaut: 300s)
            stat: Statistique à utiliser (défaut: Average)
            
        Returns:
            Données métriques
        """
        cloudwatch = self.get_client('cloudwatch')
        
        response = cloudwatch.get_metric_data(
            MetricDataQueries=[
                {
                    'Id': 'metric1',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': namespace,
                            'MetricName': metric_name,
                            'Dimensions': dimensions
                        },
                        'Period': period,
                        'Stat': stat
                    },
                    'ReturnData': True
                }
            ],
            StartTime=start_time,
            EndTime=end_time
        )
        
        return response['MetricDataResults'][0] if response['MetricDataResults'] else None


# Fonction utilitaire pour créer facilement un client AWS
def create_aws_client(profile_name=None, region=None):
    """
    Crée et retourne un client AWS.
    
    Args:
        profile_name: Nom du profil AWS (optionnel)
        region: Région AWS (optionnel)
        
    Returns:
        Une instance de AWSClient
    """
    return AWSClient(profile_name=profile_name, region=region)


if __name__ == "__main__":
    # Exemple d'utilisation
    logging.basicConfig(level=logging.INFO)
    
    # Créer un client AWS
    aws_client = create_aws_client()
    
    # Lister les instances EC2
    try:
        instances = aws_client.get_ec2_instances()
        print(f"Instances EC2 trouvées: {len(instances)}")
        
        for i, instance in enumerate(instances[:5], 1):  # Limiter à 5 instances pour l'exemple
            print(f"Instance {i}: {instance.id} - État: {instance.state['Name']}")
    except Exception as e:
        print(f"Erreur lors de la récupération des instances EC2: {e}")