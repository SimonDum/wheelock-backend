"""
Exemple d'endpoint API pour l'upload d'images vers MinIO
et l'insertion de l'URL dans la base de données
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import DocksGroup
from app.core.storage import storage_service

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/upload/docks-group/{group_id}")
async def upload_docks_group_image(
    group_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    # current_admin = Depends(get_current_admin)  # Décommentez pour protéger la route
):
    """
    Upload une image pour un groupe de docks et met à jour l'URL dans la base de données
    
    Args:
        group_id: L'ID du groupe de docks
        file: Le fichier image à uploader
        db: Session de base de données
        
    Returns:
        Les informations du groupe avec l'URL de l'image mise à jour
    """
    
    # 1. Vérifier que le groupe existe
    result = await db.execute(
        select(DocksGroup).where(DocksGroup.id == group_id)
    )
    docks_group = result.scalar_one_or_none()
    
    if not docks_group:
        raise HTTPException(
            status_code=404,
            detail=f"Groupe de docks avec l'ID {group_id} introuvable"
        )
    
    # 2. Supprimer l'ancienne image si elle existe
    if docks_group.image_url:
        deletion_success = storage_service.delete_image(docks_group.image_url)
        if not deletion_success:
            # Log l'erreur mais continue quand même
            print(f"Attention: Impossible de supprimer l'ancienne image: {docks_group.image_url}")
    
    # 3. Upload la nouvelle image vers MinIO
    try:
        image_url = await storage_service.upload_image(
            file=file,
            folder="docks-groups"  # Dossier spécifique pour les images de groupes
        )
    except HTTPException as e:
        # Re-raise l'exception HTTP du service de stockage
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'upload de l'image: {str(e)}"
        )
    
    # 4. Mettre à jour l'URL de l'image dans la base de données
    docks_group.image_url = image_url
    await db.commit()
    await db.refresh(docks_group)
    
    return {
        "message": "Image uploadée avec succès",
        "docks_group_id": docks_group.id,
        "docks_group_name": docks_group.name,
        "image_url": docks_group.image_url
    }


@router.delete("/docks-group/{group_id}")
async def delete_docks_group_image(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    # current_admin = Depends(get_current_admin)  # Décommentez pour protéger la route
):
    """
    Supprime l'image d'un groupe de docks
    
    Args:
        group_id: L'ID du groupe de docks
        db: Session de base de données
        
    Returns:
        Message de confirmation
    """
    
    # 1. Récupérer le groupe de docks
    result = await db.execute(
        select(DocksGroup).where(DocksGroup.id == group_id)
    )
    docks_group = result.scalar_one_or_none()
    
    if not docks_group:
        raise HTTPException(
            status_code=404,
            detail=f"Groupe de docks avec l'ID {group_id} introuvable"
        )
    
    if not docks_group.image_url:
        raise HTTPException(
            status_code=404,
            detail="Ce groupe de docks n'a pas d'image associée"
        )
    
    # 2. Supprimer l'image de MinIO
    deletion_success = storage_service.delete_image(docks_group.image_url)
    
    if not deletion_success:
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la suppression de l'image du stockage"
        )
    
    # 3. Mettre à jour la base de données
    docks_group.image_url = None
    await db.commit()
    
    return {
        "message": "Image supprimée avec succès",
        "docks_group_id": docks_group.id
    }


@router.post("/upload/simple")
async def upload_simple_image(
    file: UploadFile = File(...),
    # current_admin = Depends(get_current_admin)  # Décommentez pour protéger la route
):
    """
    Upload simple d'une image (sans association à un modèle)
    Utile pour tester le service de stockage
    
    Returns:
        L'URL publique de l'image uploadée
    """
    try:
        image_url = await storage_service.upload_image(file=file)
        return {
            "message": "Image uploadée avec succès",
            "image_url": image_url,
            "filename": file.filename
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'upload: {str(e)}"
        )
