import pytest
from pydantic import ValidationError

from app.models.films import (
    FilmBaseSchema,
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
