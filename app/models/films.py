from __future__ import annotations

from app.database import Base
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


# Table: films (base film, by title)
class Film(Base):
    __tablename__ = "films"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    oscar_records: Mapped[list[OscarWinnerFilm]] = relationship(
        "OscarWinnerFilm",
        back_populates="film",
        lazy="selectin",
    )


# Table: oscar_winner_films (Oscar data, linked to films via film_id)
class OscarWinnerFilm(Base):
    __tablename__ = "oscar_winner_films"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    film_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("films.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    nominations: Mapped[int] = mapped_column(Integer, nullable=False)
    awards: Mapped[int] = mapped_column(Integer, nullable=False)
    best_picture: Mapped[bool] = mapped_column(Boolean, default=False)
    job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    film: Mapped[Film] = relationship("Film", back_populates="oscar_records")


# Pydantic schemas (validation / API)
class FilmBaseSchema(BaseModel):
    title: str = Field(..., min_length=1, description="Film title")


class OscarWinnerFilmSchema(FilmBaseSchema):
    film_id: int = Field(..., description="Film ID")
    year: int = Field(..., ge=1927, description="Film year")
    nominations: int = Field(..., ge=0, description="Number of nominations")
    awards: int = Field(..., ge=0, description="Number of awards")
    best_picture: bool = Field(
        default=False,
        description="Whether the film won the Best Picture award",
    )
