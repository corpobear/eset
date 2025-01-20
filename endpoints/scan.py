from fastapi import APIRouter, UploadFile, File
from utils.ecls import ecls_manager
import asyncio
    
router = APIRouter()


@router.post("/scanFile")
async def scan_file(file: UploadFile = File(...)):
    file_data = file.file.read()
    result = await ecls_manager.submit_scan(file_data)
    return {"result": result}

@router.post("/scanMultipleFiles")
async def scan_multiple_files(files: list[UploadFile] = File(...)):
    tasks = [ecls_manager.submit_scan(await file.read()) for file in files]
    results = await asyncio.gather(*tasks)
    return {"results": results}