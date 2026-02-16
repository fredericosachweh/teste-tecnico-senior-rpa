from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


# SQLAlchemy Model
class Film(Base):
    __tablename__ = "films"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    nominations: Mapped[int] = mapped_column(Integer, nullable=False)
    awards: Mapped[int] = mapped_column(Integer, nullable=False)
    best_picture: Mapped[bool] = mapped_column(Boolean, default=False)
    job_id: Mapped[str] = mapped_column(String, nullable=True)


# Pydantic Models
class FilmBase(BaseModel):
    title: str = Field(..., min_length=1, description="Film title")


class OscarWinnerFilm(FilmBase):
    film_id: int = Field(..., description="Film ID")
    year: int = Field(..., ge=1927, description="Film year")
    nominations: int = Field(..., ge=0, description="Number of nominations")
    awards: int = Field(..., ge=0, description="Number of awards")
    best_picture: bool = Field(
        default=False,
        description="Whether the film won the Best Picture award",
    )
