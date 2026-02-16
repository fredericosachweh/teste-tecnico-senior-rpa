import pytest
from pydantic import ValidationError

from app.models.films import FilmBase, OscarWinnerFilm


class TestFilmBase:
    def test_valid_title(self):
        model = FilmBase(title="The Godfather")
        assert model.title == "The Godfather"

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            FilmBase(title="")
        assert "title" in str(exc_info.value).lower() or len(exc_info.value.errors()) > 0

    def test_missing_title_raises(self):
        with pytest.raises(ValidationError):
            FilmBase()


class TestOscarWinnerFilm:
    def test_valid_film(self):
        film = OscarWinnerFilm(
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
        film = OscarWinnerFilm(
            film_id=1,
            title="Some Film",
            year=2000,
            nominations=1,
            awards=0,
        )
        assert film.best_picture is False

    def test_year_before_1927_raises(self):
        with pytest.raises(ValidationError):
            OscarWinnerFilm(
                film_id=1,
                title="Old Film",
                year=1926,
                nominations=0,
                awards=0,
            )

    def test_year_1927_valid(self):
        film = OscarWinnerFilm(
            film_id=1,
            title="Wings",
            year=1927,
            nominations=2,
            awards=2,
        )
        assert film.year == 1927

    def test_negative_nominations_raises(self):
        with pytest.raises(ValidationError):
            OscarWinnerFilm(
                film_id=1,
                title="Film",
                year=2000,
                nominations=-1,
                awards=0,
            )

    def test_negative_awards_raises(self):
        with pytest.raises(ValidationError):
            OscarWinnerFilm(
                film_id=1,
                title="Film",
                year=2000,
                nominations=5,
                awards=-1,
            )

    def test_zero_nominations_and_awards_valid(self):
        film = OscarWinnerFilm(
            film_id=1,
            title="Film",
            year=2000,
            nominations=0,
            awards=0,
        )
        assert film.nominations == 0
        assert film.awards == 0
