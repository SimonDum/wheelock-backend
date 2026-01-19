"""
Exemple d'endpoint API pour l'upload d'images vers MinIO
et l'insertion de l'URL dans la base de données
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import ParkingSpot
from app.core.storage import storage_service

router = APIRouter(prefix="/images", tags=["Images"])


@router.post("/upload/parking-spot/{spot_id}")
async def upload_parking_spot_image(
    spot_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    # current_admin = Depends(get_current_admin)  # Décommentez pour protéger la route
):
    """
    Upload une image pour un parking spot et met à jour l'URL dans la base de données
    
    Args:
        spot_id: L'ID du parking spot
        file: Le fichier image à uploader
        db: Session de base de données
        
    Returns:
        Les informations du parking spot avec l'URL de l'image mise à jour
    """
    
    # 1. Vérifier que le parking spot existe
    result = await db.execute(
        select(ParkingSpot).where(ParkingSpot.id == spot_id)
    )
    parking_spot = result.scalar_one_or_none()
    
    if not parking_spot:
        raise HTTPException(
            status_code=404,
            detail=f"Parking spot avec l'ID {spot_id} introuvable"
        )
    
    # 2. Supprimer l'ancienne image si elle existe
    if parking_spot.image_url:
        deletion_success = storage_service.delete_image(parking_spot.image_url)
        if not deletion_success:
            # Log l'erreur mais continue quand même
            print(f"Attention: Impossible de supprimer l'ancienne image: {parking_spot.image_url}")
    
    # 3. Upload la nouvelle image vers MinIO
    try:
        image_url = await storage_service.upload_image(
            file=file,
            folder="parking-spots"  # Dossier spécifique pour les images de parking
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
    parking_spot.image_url = image_url
    await db.commit()
    await db.refresh(parking_spot)
    
    return {
        "message": "Image uploadée avec succès",
        "parking_spot_id": parking_spot.id,
        "parking_spot_name": parking_spot.name,
        "image_url": parking_spot.image_url
    }


@router.delete("/parking-spot/{spot_id}")
async def delete_parking_spot_image(
    spot_id: int,
    db: AsyncSession = Depends(get_db),
    # current_admin = Depends(get_current_admin)  # Décommentez pour protéger la route
):
    """
    Supprime l'image d'un parking spot
    
    Args:
        spot_id: L'ID du parking spot
        db: Session de base de données
        
    Returns:
        Message de confirmation
    """
    
    # 1. Récupérer le parking spot
    result = await db.execute(
        select(ParkingSpot).where(ParkingSpot.id == spot_id)
    )
    parking_spot = result.scalar_one_or_none()
    
    if not parking_spot:
        raise HTTPException(
            status_code=404,
            detail=f"Parking spot avec l'ID {spot_id} introuvable"
        )
    
    if not parking_spot.image_url:
        raise HTTPException(
            status_code=404,
            detail="Ce parking spot n'a pas d'image associée"
        )
    
    # 2. Supprimer l'image de MinIO
    deletion_success = storage_service.delete_image(parking_spot.image_url)
    
    if not deletion_success:
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la suppression de l'image du stockage"
        )
    
    # 3. Mettre à jour la base de données
    parking_spot.image_url = None
    await db.commit()
    
    return {
        "message": "Image supprimée avec succès",
        "parking_spot_id": parking_spot.id
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
