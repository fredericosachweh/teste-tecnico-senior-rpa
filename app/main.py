import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession, joinedload

from app.database import Base, engine, get_session
from app.models.films import Film, OscarWinnerFilm
from app.models.hockey_teams import HockeyTeamHistoric
from app.models.jobs import Job, JobStatus, JobType
from app.queue import publish_job

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="RPA Crawler API",
    description="API para coleta assíncrona de dados via web scraping",
    version="1.0.0",
)


# Pydantic schemas
class JobCreate(BaseModel):
    job_type: str


class JobResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    results_count: int = 0

    class Config:
        from_attributes = True


class HockeyTeamResponse(BaseModel):
    id: int
    name: str
    year: int
    wins: int
    losses: int
    losses_ot: int
    wins_percentage: float
    goals_for: float
    goals_against: float
    goal_difference: float

    class Config:
        from_attributes = True


class FilmResponse(BaseModel):
    id: int
    title: str
    year: int
    nominations: int
    awards: int
    best_picture: bool

    class Config:
        from_attributes = True


# Root endpoints
@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "RPA Crawler API",
        "version": "1.0.0",
        "endpoints": {
            "crawl": ["/crawl/hockey", "/crawl/oscar", "/crawl/all"],
            "jobs": ["/jobs", "/jobs/{job_id}", "/jobs/{job_id}/results"],
            "results": ["/results/hockey", "/results/oscar"],
        },
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# Crawl endpoints (async job creation)
@app.post("/crawl/hockey", response_model=JobResponse)
def crawl_hockey(db: DBSession = Depends(get_session)):
    """Agenda coleta do Hockey (retorna job_id)"""
    job_id = str(uuid.uuid4())

    # Create job in database
    job = Job(job_id=job_id, job_type=JobType.HOCKEY, status=JobStatus.PENDING)
    db.add(job)
    db.commit()
    db.refresh(job)

    # Publish to queue
    publish_job({"job_id": job_id, "job_type": "hockey"})

    return JobResponse(
        job_id=job.job_id,
        job_type=job.job_type.value,
        status=job.status.value,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        results_count=job.results_count,
    )


@app.post("/crawl/oscar", response_model=JobResponse)
def crawl_oscar(db: DBSession = Depends(get_session)):
    """Agenda coleta do Oscar (retorna job_id)"""
    job_id = str(uuid.uuid4())

    # Create job in database
    job = Job(job_id=job_id, job_type=JobType.OSCAR, status=JobStatus.PENDING)
    db.add(job)
    db.commit()
    db.refresh(job)

    # Publish to queue
    publish_job({"job_id": job_id, "job_type": "oscar"})

    return JobResponse(
        job_id=job.job_id,
        job_type=job.job_type.value,
        status=job.status.value,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        results_count=job.results_count,
    )


@app.post("/crawl/all")
def crawl_all(db: DBSession = Depends(get_session)):
    """Agenda ambas as coletas (retorna job_ids)"""
    jobs = []

    # Hockey job
    hockey_job_id = str(uuid.uuid4())
    hockey_job = Job(
        job_id=hockey_job_id, job_type=JobType.HOCKEY, status=JobStatus.PENDING
    )
    db.add(hockey_job)
    publish_job({"job_id": hockey_job_id, "job_type": "hockey"})
    jobs.append({"job_id": hockey_job_id, "job_type": "hockey", "status": "pending"})

    # Oscar job
    oscar_job_id = str(uuid.uuid4())
    oscar_job = Job(
        job_id=oscar_job_id, job_type=JobType.OSCAR, status=JobStatus.PENDING
    )
    db.add(oscar_job)
    publish_job({"job_id": oscar_job_id, "job_type": "oscar"})
    jobs.append({"job_id": oscar_job_id, "job_type": "oscar", "status": "pending"})

    db.commit()

    return {"jobs": jobs}


# Job management endpoints
@app.get("/jobs", response_model=List[JobResponse])
def list_jobs(db: DBSession = Depends(get_session)):
    """Lista todos os jobs"""
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    return [
        JobResponse(
            job_id=job.job_id,
            job_type=job.job_type.value,
            status=job.status.value,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            results_count=job.results_count,
        )
        for job in jobs
    ]


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: DBSession = Depends(get_session)):
    """Status e detalhes de um job"""
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        job_id=job.job_id,
        job_type=job.job_type.value,
        status=job.status.value,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        results_count=job.results_count,
    )


@app.get("/jobs/{job_id}/results")
def get_job_results(job_id: str, db: DBSession = Depends(get_session)):
    """Resultados de um job específico"""
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.COMPLETED:
        return {
            "job_id": job_id,
            "status": job.status.value,
            "message": "Job not completed yet",
            "results": [],
        }

    # Get results based on job type
    if job.job_type == JobType.HOCKEY:
        results = (
            db.query(HockeyTeamHistoric)
            .filter(HockeyTeamHistoric.job_id == job_id)
            .all()
        )
        return {
            "job_id": job_id,
            "status": job.status.value,
            "job_type": job.job_type.value,
            "results_count": len(results),
            "results": [
                HockeyTeamResponse(
                    id=r.id,
                    name=r.team.name,
                    year=r.year,
                    wins=r.wins,
                    losses=r.losses,
                    losses_ot=r.losses_ot,
                    wins_percentage=r.wins_percentage,
                    goals_for=r.goals_for,
                    goals_against=r.goals_against,
                    goal_difference=r.goal_difference,
                )
                for r in results
            ],
        }
    else:  # OSCAR
        results = (
            db.query(OscarWinnerFilm)
            .options(joinedload(OscarWinnerFilm.film))
            .filter(OscarWinnerFilm.job_id == job_id)
            .all()
        )
        return {
            "job_id": job_id,
            "status": job.status.value,
            "job_type": job.job_type.value,
            "results_count": len(results),
            "results": [
                FilmResponse(
                    id=r.id,
                    title=r.film.title,
                    year=r.year,
                    nominations=r.nominations,
                    awards=r.awards,
                    best_picture=r.best_picture,
                )
                for r in results
            ],
        }


# Results endpoints
@app.get("/results/hockey")
def get_all_hockey_results(limit: int = 100, db: DBSession = Depends(get_session)):
    """Todos os dados coletados de Hockey"""
    results = db.query(HockeyTeamHistoric).limit(limit).all()
    return {
        "total": len(results),
        "limit": limit,
        "results": [
            HockeyTeamResponse(
                id=r.id,
                name=r.team.name,
                year=r.year,
                wins=r.wins,
                losses=r.losses,
                losses_ot=r.losses_ot,
                wins_percentage=r.wins_percentage,
                goals_for=r.goals_for,
                goals_against=r.goals_against,
                goal_difference=r.goal_difference,
            )
            for r in results
        ],
    }


@app.get("/results/oscar")
def get_all_oscar_results(limit: int = 100, db: DBSession = Depends(get_session)):
    """Todos os dados coletados de Oscar"""
    results = (
        db.query(OscarWinnerFilm)
        .options(joinedload(OscarWinnerFilm.film))
        .limit(limit)
        .all()
    )
    return {
        "total": len(results),
        "limit": limit,
        "results": [
            FilmResponse(
                id=r.id,
                title=r.film.title,
                year=r.year,
                nominations=r.nominations,
                awards=r.awards,
                best_picture=r.best_picture,
            )
            for r in results
        ],
    }
