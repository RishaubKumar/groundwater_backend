"""
Citizen science and manual data submission endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.citizen_science import CitizenSubmission, CommunityObservation, SubmissionFeedback, ObservationResponse
from app.schemas.citizen_science import (
    CitizenSubmissionCreate, CitizenSubmissionResponse, 
    CommunityObservationCreate, CommunityObservationResponse,
    SubmissionFeedbackCreate, ObservationResponseCreate
)

router = APIRouter()


@router.post("/submissions", response_model=CitizenSubmissionResponse)
async def create_citizen_submission(
    submission_data: CitizenSubmissionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a citizen science data submission."""
    submission = CitizenSubmission(
        user_id=current_user.id,
        **submission_data.dict()
    )
    
    db.add(submission)
    db.commit()
    db.refresh(submission)
    
    return submission


@router.get("/submissions", response_model=List[CitizenSubmissionResponse])
async def get_citizen_submissions(
    submission_type: Optional[str] = Query(None, description="Filter by submission type"),
    station_id: Optional[str] = Query(None, description="Filter by station ID"),
    verified_only: bool = Query(False, description="Show only verified submissions"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get citizen science submissions."""
    query = db.query(CitizenSubmission)
    
    # Users can only see their own submissions unless they're admin
    if not current_user.is_superuser:
        query = query.filter(CitizenSubmission.user_id == current_user.id)
    
    if submission_type:
        query = query.filter(CitizenSubmission.submission_type == submission_type)
    
    if station_id:
        query = query.filter(CitizenSubmission.station_id == station_id)
    
    if verified_only:
        query = query.filter(CitizenSubmission.is_verified == True)
    
    submissions = query.order_by(CitizenSubmission.created_at.desc()).offset(skip).limit(limit).all()
    return submissions


@router.get("/submissions/{submission_id}", response_model=CitizenSubmissionResponse)
async def get_citizen_submission(
    submission_id: int = Path(..., description="Submission ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific citizen science submission."""
    submission = db.query(CitizenSubmission).filter(CitizenSubmission.id == submission_id).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Users can only see their own submissions unless they're admin
    if not current_user.is_superuser and submission.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return submission


@router.post("/submissions/{submission_id}/verify")
async def verify_submission(
    submission_id: int = Path(..., description="Submission ID"),
    verification_notes: Optional[str] = Query(None, description="Verification notes"),
    quality_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Quality score"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Verify a citizen science submission (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    submission = db.query(CitizenSubmission).filter(CitizenSubmission.id == submission_id).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    submission.is_verified = True
    submission.verified_by = current_user.username
    submission.verified_at = datetime.now()
    
    if verification_notes:
        submission.verification_notes = verification_notes
    
    if quality_score is not None:
        submission.quality_score = quality_score
    
    db.commit()
    
    return {"message": "Submission verified successfully"}


@router.post("/submissions/{submission_id}/feedback", response_model=SubmissionFeedback)
async def add_submission_feedback(
    submission_id: int = Path(..., description="Submission ID"),
    feedback_data: SubmissionFeedbackCreate = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add feedback to a citizen science submission."""
    # Verify submission exists
    submission = db.query(CitizenSubmission).filter(CitizenSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    feedback = SubmissionFeedback(
        submission_id=submission_id,
        feedback_by=current_user.username,
        **feedback_data.dict()
    )
    
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    
    return feedback


@router.post("/observations", response_model=CommunityObservationResponse)
async def create_community_observation(
    observation_data: CommunityObservationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a community observation."""
    observation = CommunityObservation(
        user_id=current_user.id,
        **observation_data.dict()
    )
    
    db.add(observation)
    db.commit()
    db.refresh(observation)
    
    return observation


@router.get("/observations", response_model=List[CommunityObservationResponse])
async def get_community_observations(
    observation_type: Optional[str] = Query(None, description="Filter by observation type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get community observations."""
    query = db.query(CommunityObservation)
    
    if observation_type:
        query = query.filter(CommunityObservation.observation_type == observation_type)
    
    if severity:
        query = query.filter(CommunityObservation.severity == severity)
    
    if status:
        query = query.filter(CommunityObservation.status == status)
    
    observations = query.order_by(CommunityObservation.created_at.desc()).offset(skip).limit(limit).all()
    return observations


@router.get("/observations/{observation_id}", response_model=CommunityObservationResponse)
async def get_community_observation(
    observation_id: int = Path(..., description="Observation ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific community observation."""
    observation = db.query(CommunityObservation).filter(CommunityObservation.id == observation_id).first()
    
    if not observation:
        raise HTTPException(status_code=404, detail="Observation not found")
    
    return observation


@router.post("/observations/{observation_id}/verify")
async def verify_observation(
    observation_id: int = Path(..., description="Observation ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Verify a community observation (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    observation = db.query(CommunityObservation).filter(CommunityObservation.id == observation_id).first()
    
    if not observation:
        raise HTTPException(status_code=404, detail="Observation not found")
    
    observation.is_verified = True
    observation.verified_by = current_user.username
    observation.verified_at = datetime.now()
    observation.status = "verified"
    
    db.commit()
    
    return {"message": "Observation verified successfully"}


@router.post("/observations/{observation_id}/respond", response_model=ObservationResponse)
async def respond_to_observation(
    observation_id: int = Path(..., description="Observation ID"),
    response_data: ObservationResponseCreate = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Respond to a community observation."""
    # Verify observation exists
    observation = db.query(CommunityObservation).filter(CommunityObservation.id == observation_id).first()
    if not observation:
        raise HTTPException(status_code=404, detail="Observation not found")
    
    response = ObservationResponse(
        observation_id=observation_id,
        responded_by=current_user.username,
        is_official=current_user.is_superuser,
        **response_data.dict()
    )
    
    db.add(response)
    db.commit()
    db.refresh(response)
    
    return response


@router.post("/submissions/{submission_id}/upload-photo")
async def upload_submission_photo(
    submission_id: int = Path(..., description="Submission ID"),
    photo: UploadFile = File(..., description="Photo file"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload photo for a citizen science submission."""
    # Verify submission exists and belongs to user
    submission = db.query(CitizenSubmission).filter(
        CitizenSubmission.id == submission_id,
        CitizenSubmission.user_id == current_user.id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Validate file type
    if not photo.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # In a real implementation, you would save the file to cloud storage
    # For now, we'll just store the filename
    photo_url = f"uploads/submissions/{submission_id}/{photo.filename}"
    
    # Update submission with photo URL
    if not submission.photos:
        submission.photos = []
    
    submission.photos.append(photo_url)
    db.commit()
    
    return {"message": "Photo uploaded successfully", "photo_url": photo_url}


@router.get("/stats")
async def get_citizen_science_stats(
    days: int = Query(30, ge=1, le=365, description="Period in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get citizen science statistics."""
    start_date = datetime.now() - timedelta(days=days)
    
    # Submission statistics
    total_submissions = db.query(CitizenSubmission).filter(
        CitizenSubmission.created_at >= start_date
    ).count()
    
    verified_submissions = db.query(CitizenSubmission).filter(
        CitizenSubmission.created_at >= start_date,
        CitizenSubmission.is_verified == True
    ).count()
    
    # Observation statistics
    total_observations = db.query(CommunityObservation).filter(
        CommunityObservation.created_at >= start_date
    ).count()
    
    verified_observations = db.query(CommunityObservation).filter(
        CommunityObservation.created_at >= start_date,
        CommunityObservation.is_verified == True
    ).count()
    
    # Submissions by type
    submission_types = db.query(CitizenSubmission.submission_type).filter(
        CitizenSubmission.created_at >= start_date
    ).distinct().all()
    
    submission_type_stats = {}
    for submission_type, in submission_types:
        count = db.query(CitizenSubmission).filter(
            CitizenSubmission.created_at >= start_date,
            CitizenSubmission.submission_type == submission_type
        ).count()
        submission_type_stats[submission_type] = count
    
    # Observations by type
    observation_types = db.query(CommunityObservation.observation_type).filter(
        CommunityObservation.created_at >= start_date
    ).distinct().all()
    
    observation_type_stats = {}
    for observation_type, in observation_types:
        count = db.query(CommunityObservation).filter(
            CommunityObservation.created_at >= start_date,
            CommunityObservation.observation_type == observation_type
        ).count()
        observation_type_stats[observation_type] = count
    
    return {
        "period_days": days,
        "submissions": {
            "total": total_submissions,
            "verified": verified_submissions,
            "verification_rate": verified_submissions / total_submissions if total_submissions > 0 else 0,
            "by_type": submission_type_stats
        },
        "observations": {
            "total": total_observations,
            "verified": verified_observations,
            "verification_rate": verified_observations / total_observations if total_observations > 0 else 0,
            "by_type": observation_type_stats
        }
    }
