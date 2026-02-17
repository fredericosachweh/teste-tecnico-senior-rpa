import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.films import (
    Film,
    FilmBaseSchema,
    OscarWinnerFilm,
    OscarWinnerFilmSchema,
)


class TestFilmBaseSchema:
    def test_valid_title(self):
        model = FilmBaseSchema(title="The Godfather")
        assert model.title == "The Godfather"

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            FilmBaseSchema(title="")
        err = exc_info.value
        assert "title" in str(err).lower() or len(err.errors()) > 0

    def test_missing_title_raises(self):
        with pytest.raises(ValidationError):
            FilmBaseSchema()


class TestOscarWinnerFilmSchema:
    def test_valid_film(self):
        film = OscarWinnerFilmSchema(
            film_id=1,
            title="The Godfather",
            year=1972,
            nominations=10,
            awards=3,
            best_picture=True,
        )
        assert film.film_id == 1
        assert film.title == "The Godfather"
        assert film.year == 1972
        assert film.nominations == 10
        assert film.awards == 3
        assert film.best_picture is True

    def test_best_picture_default_false(self):
        film = OscarWinnerFilmSchema(
            film_id=1,
            title="Some Film",
            year=2000,
            nominations=1,
            awards=0,
        )
        assert film.best_picture is False

    def test_year_before_1927_raises(self):
        with pytest.raises(ValidationError):
            OscarWinnerFilmSchema(
                film_id=1,
                title="Old Film",
                year=1926,
                nominations=0,
                awards=0,
            )

    def test_year_1927_valid(self):
        film = OscarWinnerFilmSchema(
            film_id=1,
            title="Wings",
            year=1927,
            nominations=2,
            awards=2,
        )
        assert film.year == 1927

    def test_negative_nominations_raises(self):
        with pytest.raises(ValidationError):
            OscarWinnerFilmSchema(
                film_id=1,
                title="Film",
                year=2000,
                nominations=-1,
                awards=0,
            )

    def test_negative_awards_raises(self):
        with pytest.raises(ValidationError):
            OscarWinnerFilmSchema(
                film_id=1,
                title="Film",
                year=2000,
                nominations=5,
                awards=-1,
            )

    def test_zero_nominations_and_awards_valid(self):
        film = OscarWinnerFilmSchema(
            film_id=1,
            title="Film",
            year=2000,
            nominations=0,
            awards=0,
        )
        assert film.nominations == 0
        assert film.awards == 0

    def test_inherits_title_from_film_base_schema(self):
        """OscarWinnerFilmSchema has title from FilmBaseSchema."""
        film = OscarWinnerFilmSchema(
            film_id=1,
            title="Inherited",
            year=1999,
            nominations=1,
            awards=1,
        )
        assert film.title == "Inherited"

    def test_film_id_zero_valid(self):
        """film_id can be any non-negative int (no ge=0 in schema, but typical)."""
        film = OscarWinnerFilmSchema(
            film_id=0,
            title="X",
            year=1928,
            nominations=0,
            awards=0,
        )
        assert film.film_id == 0


class TestFilmModel:
    """Tests for Film SQLAlchemy model (table films)."""

    @pytest.fixture
    def engine(self):
        return create_engine("sqlite:///:memory:", echo=False)

    @pytest.fixture
    def session(self, engine):
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        with session_factory() as session:
            yield session
        Base.metadata.drop_all(engine)

    def test_film_create_and_attributes(self, session):
        """Film has id, title, oscar_records."""
        film = Film(title="The Godfather")
        session.add(film)
        session.commit()
        session.refresh(film)
        assert film.id is not None
        assert film.title == "The Godfather"
        assert film.oscar_records == []

    def test_film_oscar_records_relationship(self, session):
        """Film.oscar_records back-populates from OscarWinnerFilm."""
        film = Film(title="Argo")
        session.add(film)
        session.commit()
        session.refresh(film)
        oscar = OscarWinnerFilm(
            film_id=film.id,
            year=2012,
            nominations=7,
            awards=3,
            best_picture=True,
        )
        session.add(oscar)
        session.commit()
        session.refresh(film)
        assert len(film.oscar_records) == 1
        assert film.oscar_records[0].year == 2012
        assert film.oscar_records[0].best_picture is True


class TestOscarWinnerFilmModel:
    """Tests for OscarWinnerFilm SQLAlchemy model (table oscar_winner_films)."""

    @pytest.fixture
    def engine(self):
        return create_engine("sqlite:///:memory:", echo=False)

    @pytest.fixture
    def session(self, engine):
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        with session_factory() as session:
            yield session
        Base.metadata.drop_all(engine)

    def test_oscar_winner_film_create_and_attributes(self, session):
        """OscarWinnerFilm has all columns including optional job_id, best_picture."""
        film = Film(title="Lincoln")
        session.add(film)
        session.commit()
        session.refresh(film)
        oscar = OscarWinnerFilm(
            film_id=film.id,
            year=2012,
            nominations=12,
            awards=2,
            best_picture=False,
            job_id="job-123",
        )
        session.add(oscar)
        session.commit()
        session.refresh(oscar)
        assert oscar.id is not None
        assert oscar.film_id == film.id
        assert oscar.year == 2012
        assert oscar.nominations == 12
        assert oscar.awards == 2
        assert oscar.best_picture is False
        assert oscar.job_id == "job-123"

    def test_oscar_winner_film_film_relationship(self, session):
        """OscarWinnerFilm.film back-populates from Film."""
        film = Film(title="Wings")
        session.add(film)
        session.commit()
        session.refresh(film)
        oscar = OscarWinnerFilm(
            film_id=film.id,
            year=1927,
            nominations=2,
            awards=2,
            best_picture=False,
        )
        session.add(oscar)
        session.commit()
        session.refresh(oscar)
        assert oscar.film is not None
        assert oscar.film.title == "Wings"
        assert oscar.film.id == film.id

    def test_oscar_winner_film_best_picture_default(self, session):
        """best_picture defaults to False when not set."""
        film = Film(title="X")
        session.add(film)
        session.commit()
        session.refresh(film)
        oscar = OscarWinnerFilm(
            film_id=film.id,
            year=1930,
            nominations=0,
            awards=0,
        )
        session.add(oscar)
        session.commit()
        session.refresh(oscar)
        assert oscar.best_picture is False
        assert oscar.job_id is None
