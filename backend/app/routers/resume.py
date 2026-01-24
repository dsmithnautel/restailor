"""Resume compilation endpoints."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from app.models import CompileRequest, CompileResponse, ParsedJD
from app.services.scoring import score_units_against_jd
from app.services.optimizer import optimize_selection
from app.services.renderer import render_resume
from app.db.mongodb import get_database

router = APIRouter()


@router.post("/compile", response_model=CompileResponse)
async def compile_resume(request: CompileRequest):
    """
    Compile a tailored resume from master resume + job description.
    
    Pipeline:
    1. Fetch all atomic units for master_version_id
    2. Get or parse job description
    3. Score each unit against JD using Gemini LLM
    4. Optimize selection under constraints
    5. Generate PDF via RenderCV
    6. Return results with full provenance
    """
    db = await get_database()
    
    # 1. Fetch atomic units
    units_cursor = db.atomic_units.find({"version": request.master_version_id})
    units = []
    async for doc in units_cursor:
        units.append(doc)
    
    if not units:
        raise HTTPException(
            status_code=404,
            detail=f"No atomic units found for master version {request.master_version_id}"
        )
    
    # 2. Get job description
    if request.jd_id:
        jd_doc = await db.parsed_jds.find_one({"jd_id": request.jd_id})
        if not jd_doc:
            raise HTTPException(status_code=404, detail=f"JD {request.jd_id} not found")
        parsed_jd = ParsedJD(**jd_doc)
    elif request.jd_text:
        # Parse on the fly
        from app.services.jd_parser import parse_job_description
        parsed_jd = await parse_job_description(text=request.jd_text)
    else:
        raise HTTPException(
            status_code=400,
            detail="Either jd_id or jd_text must be provided"
        )
    
    # 3. Score units using LLM
    scored_units = await score_units_against_jd(units, parsed_jd)
    
    # 4. Optimize selection
    selected_units, coverage = optimize_selection(
        scored_units,
        parsed_jd,
        request.constraints
    )
    
    # 5. Generate compile ID and provenance
    import uuid
    from datetime import datetime
    compile_id = f"cmp_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"
    
    provenance = []
    for i, unit in enumerate(selected_units):
        from app.models import Provenance
        provenance.append(Provenance(
            compile_id=compile_id,
            output_line_id=f"resume.{unit.section}.{i}",
            atomic_unit_id=unit.unit_id,
            matched_requirements=unit.matched_requirements,
            llm_score=unit.llm_score,
            llm_reasoning=unit.reasoning
        ))
    
    # 6. Render PDF (async, may take a moment)
    pdf_url = None
    try:
        pdf_path = await render_resume(compile_id, selected_units, request.master_version_id)
        pdf_url = f"/resume/{compile_id}/pdf"
    except Exception as e:
        # PDF generation failed, but we can still return the data
        pass
    
    # Store compile result
    result = CompileResponse(
        compile_id=compile_id,
        selected_units=selected_units,
        coverage=coverage,
        provenance=provenance,
        pdf_url=pdf_url
    )
    
    await db.compiles.insert_one(result.model_dump())
    
    return result


@router.get("/{compile_id}")
async def get_compile_result(compile_id: str):
    """Get a compilation result by ID."""
    db = await get_database()
    
    doc = await db.compiles.find_one({"compile_id": compile_id})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Compile {compile_id} not found")
    
    return CompileResponse(**doc)


@router.get("/{compile_id}/pdf")
async def get_compile_pdf(compile_id: str):
    """Download the compiled PDF."""
    import os
    from app.config import get_settings
    
    # Look for the PDF file
    pdf_path = f"output/{compile_id}/resume.pdf"
    
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found. Try recompiling.")
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"resume_{compile_id}.pdf"
    )


@router.get("/{compile_id}/provenance")
async def get_provenance(compile_id: str):
    """Get the provenance JSON for a compilation."""
    db = await get_database()
    
    doc = await db.compiles.find_one({"compile_id": compile_id})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Compile {compile_id} not found")
    
    return JSONResponse(content={"provenance": doc.get("provenance", [])})


@router.get("/{compile_id}/narrate")
async def narrate_resume(compile_id: str):
    """
    Generate voice narration of the compiled resume (stretch goal).
    
    Requires ELEVENLABS_API_KEY to be configured.
    """
    from fastapi.responses import StreamingResponse
    from app.services.voice import generate_resume_narration, format_resume_for_narration
    
    db = await get_database()
    doc = await db.compiles.find_one({"compile_id": compile_id})
    
    if not doc:
        raise HTTPException(status_code=404, detail=f"Compile {compile_id} not found")
    
    # Format resume for narration
    selected_units = doc.get("selected_units", [])
    narration_text = format_resume_for_narration(selected_units)
    
    # Generate audio
    audio_bytes = await generate_resume_narration(narration_text)
    
    if audio_bytes is None:
        raise HTTPException(
            status_code=503,
            detail="Voice narration not available. ElevenLabs API key not configured."
        )
    
    return StreamingResponse(
        iter([audio_bytes]),
        media_type="audio/mpeg",
        headers={"Content-Disposition": f"attachment; filename=resume_{compile_id}.mp3"}
    )
