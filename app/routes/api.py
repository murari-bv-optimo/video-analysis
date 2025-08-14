import os
import time
import uuid
from typing import List
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from ..room_analyzer import RoomAnalyzer
from ..models import UploadResponse, AnalysisResult
import shutil

router = APIRouter()

# In-memory storage for processing status
processing_status = {}

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    allowed_extensions = os.getenv('ALLOWED_EXTENSIONS', 'jpg,jpeg,png,bmp,tiff').split(',')
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_uploaded_files(files: List[UploadFile], house_id: str) -> List[str]:
    """Save uploaded files and return their paths"""
    upload_dir = os.getenv('UPLOAD_DIR', 'uploads')
    house_dir = os.path.join(upload_dir, house_id)
    os.makedirs(house_dir, exist_ok=True)
    
    saved_paths = []
    for index, file in enumerate(files):
        if file.filename and allowed_file(file.filename):
            base_name, ext = os.path.splitext(file.filename)
            # Ensure unique filenames to prevent overwriting
            unique_name = f"{base_name}_{index:03d}{ext.lower()}"
            file_path = os.path.join(house_dir, unique_name)
            # If somehow exists, add a uuid suffix
            counter = 1
            while os.path.exists(file_path):
                unique_name = f"{base_name}_{index:03d}_{counter}{ext.lower()}"
                file_path = os.path.join(house_dir, unique_name)
                counter += 1
            # Ensure file stream is at the start before copying
            try:
                file.file.seek(0)
            except Exception:
                pass
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_paths.append(file_path)
    
    return saved_paths

async def process_images_background(house_id: str, image_paths: List[str]):
    """Background task to process images"""
    try:
        processing_status[house_id] = {"status": "processing", "progress": 0}
        
        analyzer = RoomAnalyzer()
        start_time = time.time()
        
        result = await analyzer.analyze_images(image_paths, house_id)
        
        processing_time = time.time() - start_time
        result["processing_time"] = processing_time
        
        processing_status[house_id] = {
            "status": "completed",
            "progress": 100,
            "result": result
        }
        
        # Clean up uploaded files
        upload_dir = os.path.join(os.getenv('UPLOAD_DIR', 'uploads'), house_id)
        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir)
            
    except Exception as e:
        processing_status[house_id] = {
            "status": "failed",
            "error": str(e),
            "progress": 0
        }

@router.post("/upload", response_model=UploadResponse)
async def upload_images(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    """Upload images for analysis"""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    # Validate files
    max_size = int(os.getenv('MAX_FILE_SIZE', '10485760'))  # 10MB
    valid_files = []
    
    for file in files:
        if not file.filename:
            continue
            
        if not allowed_file(file.filename):
            raise HTTPException(
                status_code=400, 
                detail=f"File type not allowed: {file.filename}"
            )
            
        # Check file size
        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {file.filename}"
            )
        
        # Reset file pointer
        await file.seek(0)
        valid_files.append(file)
    
    if not valid_files:
        raise HTTPException(status_code=400, detail="No valid files found")
    
    # Generate house ID and save files
    house_id = str(uuid.uuid4())
    image_paths = save_uploaded_files(valid_files, house_id)
    
    # Start background processing
    background_tasks.add_task(process_images_background, house_id, image_paths)
    
    return UploadResponse(
        message="Images uploaded successfully. Processing started.",
        house_id=house_id,
        total_images=len(image_paths),
        processing_status="started"
    )

@router.get("/status/{house_id}")
async def get_processing_status(house_id: str):
    """Get processing status for a house analysis"""
    if house_id not in processing_status:
        raise HTTPException(status_code=404, detail="House ID not found")
    
    return processing_status[house_id]

@router.get("/result/{house_id}", response_model=AnalysisResult)
async def get_analysis_result(house_id: str):
    """Get analysis result for a completed house analysis"""
    if house_id not in processing_status:
        raise HTTPException(status_code=404, detail="House ID not found")
    
    status_info = processing_status[house_id]
    
    if status_info["status"] != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Analysis not completed. Status: {status_info['status']}"
        )
    
    result = status_info["result"]
    
    return AnalysisResult(
        house_id=result["house_id"],
        status=result["status"],
        total_rooms=result["total_rooms"],
        processing_time=result["processing_time"],
        output_file=result["output_file"],
        report=result["report"]
    )

@router.get("/download/{house_id}")
async def download_report(house_id: str):
    """Download JSON report file"""
    if house_id not in processing_status:
        raise HTTPException(status_code=404, detail="House ID not found")
    
    status_info = processing_status[house_id]
    if status_info["status"] != "completed":
        raise HTTPException(status_code=400, detail="Analysis not completed")
    
    output_file = status_info["result"]["output_file"]
    if not os.path.exists(output_file):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    return FileResponse(
        output_file,
        media_type='application/json',
        filename=f"house_analysis_{house_id[:8]}.json"
    )
