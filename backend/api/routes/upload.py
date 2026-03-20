"""
SkillPathForge AI — Upload Route
----------------------------------
POST /api/v1/upload

Handles resume and JD file uploads.
Validates file then parses to clean text.

This route is THIN — all logic in nlp/parser.py.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from api.schemas import UploadResponse, ErrorResponse
from nlp.parser import parse_file, validate_file
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload resume or JD file",
    description="Accepts PDF or DOCX file and returns parsed text with sections",
)
async def upload_file(
    file: UploadFile = File(
        ...,
        description="Resume or JD file (PDF or DOCX)"
    ),
) -> JSONResponse:
    """
    Upload and parse a resume or job description file.

    Steps:
      1. Read file bytes
      2. Validate size + extension
      3. Parse to clean text
      4. Return text + sections

    Args:
        file: uploaded file from multipart form

    Returns:
        UploadResponse with parsed text and sections
    """
    logger.info(f"Upload received: {file.filename}")

    try:
        # Read file bytes
        file_bytes = await file.read()

        # Validate file
        validation = validate_file(
            file_bytes=file_bytes,
            filename=file.filename,
            max_size_mb=5.0,
        )

        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail=validation["message"],
            )

        # Parse file to text
        parsed = parse_file(
            file_bytes=file_bytes,
            filename=file.filename,
        )

        logger.info(
            f"Parsed {file.filename}: "
            f"{parsed.metadata.get('word_count', 0)} words, "
            f"{len(parsed.sections)} sections"
        )

        return JSONResponse(
            status_code=200,
            content={
                "success":   True,
                "file_type": parsed.file_type,
                "raw_text":  parsed.raw_text,
                "sections":  parsed.sections,
                "metadata":  parsed.metadata,
                "message":   (
                    f"Successfully parsed {file.filename}"
                ),
            },
        )

    except HTTPException:
        raise

    except ValueError as e:
        logger.error(f"Parse error: {e}")
        raise HTTPException(
            status_code=422,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}",
        )