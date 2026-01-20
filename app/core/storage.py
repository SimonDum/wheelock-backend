"""
Service de stockage d'images avec MinIO (compatible S3)
"""
import logging
from typing import Optional
from datetime import datetime
from io import BytesIO
import uuid

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from fastapi import UploadFile, HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """
    Service pour gérer le stockage de fichiers dans MinIO/S3
    """
    
    def __init__(self):
        """
        Initialise le client S3 avec les configurations MinIO
        """
        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=settings.MINIO_ENDPOINT,
                aws_access_key_id=settings.MINIO_ACCESS_KEY,
                aws_secret_access_key=settings.MINIO_SECRET_KEY,
                use_ssl=settings.MINIO_USE_SSL,
                verify=False  # Pour le développement local
            )
            self.bucket_name = settings.MINIO_BUCKET_NAME
            logger.info(f"Client S3 initialisé avec succès pour le bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client S3: {str(e)}")
            raise

    def _verify_bucket_exists(self) -> bool:
        """
        Vérifie que le bucket existe
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error(f"Le bucket {self.bucket_name} n'existe pas")
                return False
            else:
                logger.error(f"Erreur lors de la vérification du bucket: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la vérification du bucket: {str(e)}")
            return False

    def _generate_unique_filename(self, original_filename: str) -> str:
        """
        Génère un nom de fichier unique pour éviter les collisions
        
        Args:
            original_filename: Le nom de fichier original
            
        Returns:
            Un nom de fichier unique avec horodatage et UUID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        extension = original_filename.split('.')[-1] if '.' in original_filename else ''
        
        if extension:
            return f"{timestamp}_{unique_id}.{extension}"
        return f"{timestamp}_{unique_id}"

    async def upload_image(
        self, 
        file: UploadFile, 
        folder: str = "images"
    ) -> str:
        """
        Upload un fichier image vers MinIO et retourne l'URL publique
        
        Args:
            file: Le fichier à uploader (FastAPI UploadFile)
            folder: Le dossier dans le bucket (optionnel)
            
        Returns:
            L'URL publique du fichier uploadé
            
        Raises:
            HTTPException: Si l'upload échoue
        """
        # Vérification que le bucket existe
        if not self._verify_bucket_exists():
            raise HTTPException(
                status_code=500,
                detail=f"Le bucket de stockage {self.bucket_name} n'est pas accessible"
            )

        # Validation du type de fichier (images uniquement)
        allowed_content_types = [
            "image/jpeg", 
            "image/jpg", 
            "image/png", 
            "image/gif", 
            "image/webp"
        ]
        
        if file.content_type not in allowed_content_types:
            raise HTTPException(
                status_code=400,
                detail=f"Type de fichier non autorisé. Types acceptés: {', '.join(allowed_content_types)}"
            )

        # Génération du nom de fichier unique
        unique_filename = self._generate_unique_filename(file.filename)
        object_key = f"{folder}/{unique_filename}"

        try:
            # Lecture du contenu du fichier
            file_content = await file.read()
            
            # Upload vers MinIO
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=BytesIO(file_content),
                ContentType=file.content_type,
                Metadata={
                    'original-filename': file.filename,
                    'upload-date': datetime.now().isoformat()
                }
            )
            
            # Construction de l'URL publique
            public_url = f"{settings.MINIO_PUBLIC_ENDPOINT}/{self.bucket_name}/{object_key}"
            
            logger.info(f"Fichier uploadé avec succès: {object_key}")
            return public_url

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Erreur S3 lors de l'upload: {error_code} - {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Erreur lors de l'upload du fichier: {error_code}"
            )
        except BotoCoreError as e:
            logger.error(f"Erreur BotoCore lors de l'upload: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Erreur de connexion au service de stockage"
            )
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'upload: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Erreur inattendue lors de l'upload: {str(e)}"
            )
        finally:
            # Fermeture du fichier
            await file.close()

    def delete_image(self, image_url: str) -> bool:
        """
        Supprime une image du stockage MinIO
        
        Args:
            image_url: L'URL complète de l'image à supprimer
            
        Returns:
            True si la suppression a réussi, False sinon
        """
        try:
            # Extraction de l'object_key depuis l'URL
            # Format: http://localhost:9000/images-public/images/20260119_abc123.jpg
            parts = image_url.split(f"/{self.bucket_name}/")
            if len(parts) != 2:
                logger.error(f"Format d'URL invalide: {image_url}")
                return False
            
            object_key = parts[1]
            
            # Suppression de l'objet
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            logger.info(f"Fichier supprimé avec succès: {object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Erreur lors de la suppression du fichier: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la suppression: {str(e)}")
            return False

    def get_presigned_url(self, object_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Génère une URL pré-signée pour un accès temporaire sécurisé
        (Utile pour les buckets privés)
        
        Args:
            object_key: La clé de l'objet dans le bucket
            expiration: Durée de validité de l'URL en secondes (défaut: 1h)
            
        Returns:
            L'URL pré-signée ou None en cas d'erreur
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Erreur lors de la génération de l'URL pré-signée: {str(e)}")
            return None


# Instance unique du service de stockage
storage_service = StorageService()
