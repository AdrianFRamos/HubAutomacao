from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pathlib import Path
import uuid
import shutil
from typing import List
from app.api.deps import get_current_user

router = APIRouter(prefix="/uploads", tags=["uploads"])

UPLOAD_DIR = Path("/home/ubuntu/projeto_final/backend/uploads")
DASHBOARD_DIR = UPLOAD_DIR / "dashboards"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def validate_image(file: UploadFile) -> None:
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensão não permitida. Use: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="O arquivo deve ser uma imagem"
        )

@router.post("/dashboard-image")
async def upload_dashboard_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    try:
        validate_image(file)
        
        file_ext = Path(file.filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = DASHBOARD_DIR / unique_filename
        
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        relative_path = f"uploads/dashboards/{unique_filename}"
        
        return {
            "filename": unique_filename,
            "path": relative_path,
            "url": f"/uploads/dashboards/{unique_filename}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao fazer upload: {str(e)}")

@router.post("/dashboard-images")
async def upload_multiple_dashboard_images(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Máximo de 5 imagens por vez")
    
    uploaded_files = []
    
    for file in files:
        try:
            validate_image(file)
            
            file_ext = Path(file.filename).suffix.lower()
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = DASHBOARD_DIR / unique_filename
            
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            uploaded_files.append({
                "original_name": file.filename,
                "filename": unique_filename,
                "path": f"uploads/dashboards/{unique_filename}",
                "url": f"/uploads/dashboards/{unique_filename}"
            })
        
        except HTTPException as e:
            for uploaded in uploaded_files:
                try:
                    (DASHBOARD_DIR / uploaded["filename"]).unlink()
                except:
                    pass
            raise e
    
    return {"files": uploaded_files}
