#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cloud Optimizer MVP
action_executor.py - Module d'exécution des actions d'optimisation recommandées
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Import des modules de base
from backend.integrations.aws_client import AwsClient
from backend.utils.db import OptimizerRecommendation, RecommendationType, ResourceType, ActionResult, ActionStatus, session

logger = logging.getLogger(__name__)

class ActionExecutor:
    """
    Classe responsable de l'exécution des actions d'optimisation
    recommandées par les différents optimiseurs.
    """
    
    def __init__(self, aws_client: AwsClient):
        """
        Initialise l'exécuteur d'actions.
        
        Args:
            aws_client: Client AWS pour exécuter les actions
        """
        self.aws_client = aws_client
        
    def execute_action(self, recommendation_id: int) -> Dict[str, Any]:
        """
        Exécute une action basée sur une recommandation spécifique.
        
        Args:
            recommendation_id: ID de la recommandation à exécuter
            
        Returns:
            Résultat de l'exécution de l'action
        """
        # Récupérer la recommandation depuis la base de données
        recommendation = self._get_recommendation(recommendation_id)
        
        if not recommendation:
            return {
                'status': ActionStatus.FAILED.value,
                'message': f"Recommandation {recommendation_id} introuvable"
            }
        
        # Vérifier si la recommandation a déjà été appliquée
        if recommendation.is_applied:
            return {
                'status': ActionStatus.SKIPPED.value,
                'message': f"La recommandation {recommendation_id} a déjà été appliquée"
            }
        
        # Exécuter l'action en fonction du type de recommandation
        try:
            # Dispatcher vers la méthode appropriée en fonction du type de recommandation
            if recommendation.recommendation_type == RecommendationType.STORAGE_CLASS_CHANGE.value:
                result = self._execute_storage_class_change(recommendation)
            elif recommendation.recommendation_type == RecommendationType.RESOURCE_CLEANUP.value:
                result = self._execute_resource_cleanup(recommendation)
            elif recommendation.recommendation_type == RecommendationType.RESOURCE_SNAPSHOT.value:
                result = self._execute_resource_snapshot(recommendation)
            elif recommendation.recommendation_type == RecommendationType.VOLUME_TYPE_CHANGE.value:
                result = self._execute_volume_type_change(recommendation)
            else:
                result = {
                    'status': ActionStatus.FAILED.value,
                    'message': f"Type de recommandation non pris en charge: {recommendation.recommendation_type}"
                }
            
            # Enregistrer le résultat de l'action
            self._record_action_result(recommendation, result)
            
            return result
            
        except Exception as e:
            error_message = f"Erreur lors de l'exécution de l'action pour la recommandation {recommendation_id}: {str(e)}"
            logger.error(error_message)
            
            # Enregistrer l'échec
            error_result = {
                'status': ActionStatus.FAILED.value,
                'message': error_message,
                'error': str(e)
            }
            self._record_action_result(recommendation, error_result)
            
            return error_result
    
    def _execute_storage_class_change(self, recommendation: OptimizerRecommendation) -> Dict[str, Any]:
        """
        Exécute un changement de classe de stockage pour un bucket S3.
        
        Args:
            recommendation: La recommandation à appliquer
            
        Returns:
            Résultat de l'exécution
        """
        account_id = recommendation.account_id
        region = recommendation.region
        bucket_name = recommendation.resource_id
        current_storage = recommendation.current_configuration
        target_storage = recommendation.recommended_configuration
        
        logger.info(f"Exécution du changement de classe de stockage de {current_storage} vers {target_storage} pour le bucket {bucket_name}")
        
        try:
            # Créer une configuration de cycle de vie pour migrer les objets
            lifecycle_config = self._create_storage_transition_lifecycle(
                bucket_name, current_storage, target_storage
            )
            
            # Appliquer la configuration de cycle de vie via le client AWS
            self.aws_client.set_s3_lifecycle_configuration(
                account_id=account_id,
                region=region,
                bucket_name=bucket_name,
                lifecycle_configuration=lifecycle_config
            )
            
            return {
                'status': ActionStatus.SUCCEEDED.value,
                'message': f"Configuration de cycle de vie appliquée pour migrer les objets de {current_storage} vers {target_storage}",
                'details': {
                    'lifecycle_configuration': lifecycle_config
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du changement de classe de stockage pour {bucket_name}: {str(e)}")
            raise
    
    def _execute_resource_cleanup(self, recommendation: OptimizerRecommendation) -> Dict[str, Any]:
        """
        Exécute une action de nettoyage de ressource (suppression).
        
        Args:
            recommendation: La recommandation à appliquer
            
        Returns:
            Résultat de l'exécution
        """
        account_id = recommendation.account_id
        region = recommendation.region
        resource_id = recommendation.resource_id
        resource_type = recommendation.resource_type
        
        logger.info(f"Exécution du nettoyage de la ressource {resource_id} de type {resource_type}")
        
        try:
            if resource_type == ResourceType.S3_BUCKET.value:
                # Vérifier si le bucket est vide avant suppression
                is_empty = self.aws_client.check_s3_bucket_empty(
                    account_id=account_id,
                    region=region,
                    bucket_name=resource_id
                )
                
                if not is_empty:
                    return {
                        'status': ActionStatus.SKIPPED.value,
                        'message': f"Le bucket {resource_id} n'est pas vide, suppression annulée",
                        'requires_manual_review': True
                    }
                
                # Supprimer le bucket
                self.aws_client.delete_s3_bucket(
                    account_id=account_id,
                    region=region,
                    bucket_name=resource_id
                )
                
                return {
                    'status': ActionStatus.SUCCEEDED.value,
                    'message': f"Bucket S3 {resource_id} supprimé avec succès"
                }
                
            elif resource_type == ResourceType.EBS_VOLUME.value:
                # Vérifier si le volume est détaché
                volume_info = self.aws_client.get_ebs_volume_info(
                    account_id=account_id,
                    region=region,
                    volume_id=resource_id
                )
                
                if volume_info.get('State') == 'in-use':
                    return {
                        'status': ActionStatus.SKIPPED.value,
                        'message': f"Le volume EBS {resource_id} est toujours attaché, suppression annulée",
                        'requires_manual_review': True
                    }
                
                # Supprimer le volume
                self.aws_client.delete_ebs_volume(
                    account_id=account_id,
                    region=region,
                    volume_id=resource_id
                )
                
                return {
                    'status': ActionStatus.SUCCEEDED.value,
                    'message': f"Volume EBS {resource_id} supprimé avec succès"
                }
            
            else:
                return {
                    'status': ActionStatus.FAILED.value,
                    'message': f"Type de ressource non pris en charge pour le nettoyage: {resource_type}"
                }
                
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage de la ressource {resource_id}: {str(e)}")
            raise
    
    def _execute_resource_snapshot(self, recommendation: OptimizerRecommendation) -> Dict[str, Any]:
        """
        Exécute une action de snapshot de ressource avant suppression.
        
        Args:
            recommendation: La recommandation à appliquer
            
        Returns:
            Résultat de l'exécution
        """
        account_id = recommendation.account_id
        region = recommendation.region
        resource_id = recommendation.resource_id
        resource_type = recommendation.resource_type
        
        logger.info(f"Exécution du snapshot de la ressource {resource_id} de type {resource_type}")
        
        try:
            if resource_type == ResourceType.EBS_VOLUME.value:
                # Créer un snapshot du volume
                snapshot_description = f"Snapshot automatique créé par Cloud Optimizer avant suppression - {datetime.now().isoformat()}"
                
                snapshot_id = self.aws_client.create_ebs_snapshot(
                    account_id=account_id,
                    region=region,
                    volume_id=resource_id,
                    description=snapshot_description
                )
                
                # Attendre que le snapshot soit terminé
                self.aws_client.wait_for_snapshot_completion(
                    account_id=account_id,
                    region=region,
                    snapshot_id=snapshot_id
                )
                
                # Supprimer le volume
                self.aws_client.delete_ebs_volume(
                    account_id=account_id,
                    region=region,
                    volume_id=resource_id
                )
                
                return {
                    'status': ActionStatus.SUCCEEDED.value,
                    'message': f"Snapshot {snapshot_id} créé et volume {resource_id} supprimé avec succès",
                    'details': {
                        'snapshot_id': snapshot_id,
                        'description': snapshot_description
                    }
                }
            
            else:
                return {
                    'status': ActionStatus.FAILED.value,
                    'message': f"Type de ressource non pris en charge pour le snapshot: {resource_type}"
                }
                
        except Exception as e:
            logger.error(f"Erreur lors du snapshot de la ressource {resource_id}: {str(e)}")
            raise
    
    def _execute_volume_type_change(self, recommendation: OptimizerRecommendation) -> Dict[str, Any]:
        """
        Exécute un changement de type de volume EBS.
        
        Args:
            recommendation: La recommandation à appliquer
            
        Returns:
            Résultat de l'exécution
        """
        account_id = recommendation.account_id
        region = recommendation.region
        volume_id = recommendation.resource_id
        current_config = recommendation.current_configuration
        target_config = recommendation.recommended_configuration
        
        logger.info(f"Exécution du changement de type de volume de {current_config} vers {target_config} pour {volume_id}")
        
        try:
            # Extraire le type de volume cible et autres paramètres
            target_type = target_config.split(',')[0].strip()
            
            # Paramètres par défaut pour gp3
            iops = 3000
            throughput = 125
            
            # Configurer les IOPS et le throughput en fonction du type cible
            if 'IOPS' in target_config:
                # Extraire les IOPS de la configuration cible (ex: "gp3, 5000 IOPS")
                iops_part = [part for part in target_config.split(',') if 'IOPS' in part]
                if iops_part:
                    iops = int(iops_part[0].split()[0])
            
            if 'Mo/s' in target_config:
                # Extraire le throughput de la configuration cible (ex: "gp3, 150 Mo/s")
                throughput_part = [part for part in target_config.split(',') if 'Mo/s' in part]
                if throughput_part:
                    throughput = int(throughput_part[0].split()[0])
            
            # Vérifier si le volume est attaché
            volume_info = self.aws_client.get_ebs_volume_info(
                account_id=account_id,
                region=region,
                volume_id=volume_id
            )
            
            # Modifier le type de volume
            self.aws_client.modify_ebs_volume(
                account_id=account_id,
                region=region,
                volume_id=volume_id,
                volume_type=target_type,
                iops=iops if target_type in ['io1', 'io2', 'gp3'] else None,
                throughput=throughput if target_type == 'gp3' else None
            )
            
            return {
                'status': ActionStatus.SUCCEEDED.value,
                'message': f"Type de volume modifié de {current_config} vers {target_config}",
                'details': {
                    'volume_id': volume_id,
                    'new_type': target_type,
                    'iops': iops if target_type in ['io1', 'io2', 'gp3'] else None,
                    'throughput': throughput if target_type == 'gp3' else None
                }
            }
                
        except Exception as e:
            logger.error(f"Erreur lors du changement de type de volume {volume_id}: {str(e)}")
            raise
    
    def _create_storage_transition_lifecycle(
        self, bucket_name: str, source_class: str, target_class: str, prefix: str = None
    ) -> Dict[str, Any]:
        """
        Crée une configuration de cycle de vie pour la transition de classe de stockage.
        
        Args:
            bucket_name: Nom du bucket S3
            source_class: Classe de stockage source
            target_class: Classe de stockage cible
            prefix: Préfixe pour appliquer la règle à un sous-ensemble d'objets
            
        Returns:
            Configuration de cycle de vie
        """
        # Déterminer le délai de transition en fonction de la classe cible
        transition_days = 0  # Transition immédiate par défaut
        
        if target_class == 'Glacier':
            transition_days = 1  # 24h pour Glacier
        elif target_class == 'DeepArchive':
            transition_days = 1  # 24h pour Deep Archive
        
        # Créer la règle de cycle de vie
        lifecycle_rule = {
            'Status': 'Enabled',
            'ID': f'AutoTransitionTo{target_class}-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'Transitions': [
                {
                    'Days': transition_days,
                    'StorageClass': target_class
                }
            ]
        }
        
        # Ajouter le filtre si un préfixe est spécifié
        if prefix:
            lifecycle_rule['Filter'] = {
                'Prefix': prefix
            }
        
        # Si la source est spécifiée, ajouter une condition pour ne cibler que cette classe
        if source_class and source_class != 'Standard':
            if 'Filter' not in lifecycle_rule:
                lifecycle_rule['Filter'] = {}
            
            lifecycle_rule['Filter']['ObjectSizeGreaterThan'] = 0
            # Note: AWS ne permet pas de filtrer directement par classe de stockage
            # On utilise donc une astuce avec ObjectSizeGreaterThan
            
        # Configuration complète du cycle de vie
        lifecycle_config = {
            'Rules': [lifecycle_rule]
        }
        
        return lifecycle_config
    
    def _get_recommendation(self, recommendation_id: int) -> Optional[OptimizerRecommendation]:
        """
        Récupère une recommandation depuis la base de données.
        
        Args:
            recommendation_id: ID de la recommandation
            
        Returns:
            L'objet recommandation ou None si non trouvé
        """
        try:
            with session() as db_session:
                recommendation = db_session.query(OptimizerRecommendation).get(recommendation_id)
                return recommendation
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la recommandation {recommendation_id}: {str(e)}")
            return None
    
    def _record_action_result(self, recommendation: OptimizerRecommendation, result: Dict[str, Any]) -> None:
        """
        Enregistre le résultat d'une action dans la base de données.
        
        Args:
            recommendation: La recommandation concernée
            result: Le résultat de l'action
        """
        try:
            action_result = ActionResult(
                recommendation_id=recommendation.id,
                status=result.get('status'),
                message=result.get('message'),
                execution_time=datetime.now(),
                details=result.get('details', {})
            )
            
            with session() as db_session:
                # Ajouter le résultat de l'action
                db_session.add(action_result)
                
                # Mettre à jour la recommandation si l'action a réussi
                if result.get('status') == ActionStatus.SUCCEEDED.value:
                    recommendation = db_session.query(OptimizerRecommendation).get(recommendation.id)
                    if recommendation:
                        recommendation.is_applied = True
                        recommendation.applied_at = datetime.now()
                
                db_session.commit()
                
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement du résultat de l'action: {str(e)}")
    
    def execute_bulk_actions(self, recommendation_ids: List[int]) -> Dict[str, Any]:
        """
        Exécute plusieurs actions en batch.
        
        Args:
            recommendation_ids: Liste des IDs de recommandations à exécuter
            
        Returns:
            Résumé des résultats d'exécution
        """
        results = {
            'total': len(recommendation_ids),
            'succeeded': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
        
        for recommendation_id in recommendation_ids:
            try:
                result = self.execute_action(recommendation_id)
                
                # Compter les résultats par statut
                status = result.get('status')
                if status == ActionStatus.SUCCEEDED.value:
                    results['succeeded'] += 1
                elif status == ActionStatus.FAILED.value:
                    results['failed'] += 1
                elif status == ActionStatus.SKIPPED.value:
                    results['skipped'] += 1
                
                # Ajouter le détail du résultat
                results['details'].append({
                    'recommendation_id': recommendation_id,
                    'status': status,
                    'message': result.get('message')
                })
                
            except Exception as e:
                logger.error(f"Erreur non gérée lors de l'exécution de l'action {recommendation_id}: {str(e)}")
                results['failed'] += 1
                results['details'].append({
                    'recommendation_id': recommendation_id,
                    'status': ActionStatus.FAILED.value,
                    'message': f"Erreur non gérée: {str(e)}"
                })
        
        return results

def main():
    """Point d'entrée principal (pour tests)"""
    from backend.integrations.aws_client import AwsClient
    
    # Initialiser les dépendances
    aws_client = AwsClient()
    
    # Créer l'exécuteur d'actions
    action_executor = ActionExecutor(aws_client)
    
    # Tester l'exécution d'une action (exemple)
    recommendation_id = 1  # ID exemple
    
    result = action_executor.execute_action(recommendation_id)
    print(f"Résultat de l'exécution: {result}")

if __name__ == "__main__":
    main()