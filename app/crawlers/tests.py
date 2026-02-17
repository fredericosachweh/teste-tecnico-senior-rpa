from unittest.mock import MagicMock, patch

import pytest
from selenium.common.exceptions import StaleElementReferenceException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.hockey_teams import HockeyTeam, HockeyTeamHistoric

from .crawler import HockeyHistoricScraper, OscarScraper

HOCKEY_HEADER = [
    "Team Name",
    "Year",
    "Wins",
    "Losses",
    "OT Losses",
    "Win %",
    "Goals For (GF)",
    "Goals Against (GA)",
    "+ / -",
]


def _make_cell(text: str) -> MagicMock:
    cell = MagicMock()
    cell.text = text
    return cell


def _make_row(cell_texts: list[str]):
    row = MagicMock()
    cells = [_make_cell(t) for t in cell_texts]
    row.find_elements.return_value = cells
    return row


def _make_page_data(rows: list[list[str]]):
    """Build a mock page_data WebElement. First row is header (skipped)."""
    table = MagicMock()
    mock_rows = [_make_row(cell_texts) for cell_texts in rows]
    table.find_elements.return_value = mock_rows

    page_data = MagicMock()
    page_data.find_element.return_value = table
    return page_data


@pytest.fixture
def scraper():
    return HockeyHistoricScraper(headless=True)


def test_empty_table_returns_empty_list(scraper):
    page_data = _make_page_data([HOCKEY_HEADER])
    result = scraper.parse_page_data(page_data)
    assert result == []


def test_single_row_parsed_correctly(scraper):
    page_data = _make_page_data(
        [
            HOCKEY_HEADER,
            ["Bruins", "2024", "50", "20", "12", ".650", "280", "220", "60"],
        ]
    )
    result = scraper.parse_page_data(page_data)

    assert len(result) == 1
    assert result[0] == {
        "name": "Bruins",
        "year": "2024",
        "wins": "50",
        "losses": "20",
        "losses_ot": "12",
        "wins_percentage": ".650",
        "goals_for": "280",
        "goals_against": "220",
        "goal_difference": "60",
    }


def test_multiple_rows_parsed(scraper):
    page_data = _make_page_data(
        [
            HOCKEY_HEADER,
            ["Bruins", "2024", "50", "20", "12", ".650", "280", "220", "60"],
            ["Rangers", "2024", "48", "22", "12", ".610", "270", "230", "40"],
        ]
    )
    result = scraper.parse_page_data(page_data)

    assert len(result) == 2
    assert result[0]["name"] == "Bruins"
    assert result[1]["name"] == "Rangers"


def test_strips_whitespace(scraper):
    page_data = _make_page_data(
        [
            HOCKEY_HEADER,
            ["  Bruins  ", " 2024 ", "50", "20", "12", ".650", "280", "220", "60"],
        ]
    )
    result = scraper.parse_page_data(page_data)

    assert result[0]["name"] == "Bruins"
    assert result[0]["year"] == "2024"


def test_row_with_fewer_than_nine_cells_skipped(scraper):
    page_data = _make_page_data(
        [
            HOCKEY_HEADER,
            ["Bruins", "2024", "50"],  # only 3 cells
            ["Rangers", "2024", "48", "22", "12", ".610", "270", "230", "40"],
        ]
    )
    result = scraper.parse_page_data(page_data)

    assert len(result) == 1
    assert result[0]["name"] == "Rangers"


def test_stale_element_exception_skips_row(scraper):
    page_data = _make_page_data(
        [
            HOCKEY_HEADER,
            ["Bruins", "2024", "50", "20", "12", ".650", "280", "220", "60"],
            ["Rangers", "2024", "48", "22", "12", ".610", "270", "230", "40"],
        ]
    )

    # Make second data row (index 2) stale
    rows = page_data.find_element.return_value.find_elements.return_value
    rows[2].find_elements.side_effect = StaleElementReferenceException("stale")

    result = scraper.parse_page_data(page_data)

    assert len(result) == 1
    assert result[0]["name"] == "Bruins"


def test_save_to_database(scraper):
    """Save parsed data to an in-memory SQLite database and verify it was persisted."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    page_data = _make_page_data(
        [
            HOCKEY_HEADER,
            ["Bruins", "2024", "50", "20", "12", ".650", "280", "220", "60"],
            ["Rangers", "2024", "48", "22", "12", ".610", "270", "230", "40"],
        ]
    )

    records = scraper.parse_page_data(page_data)
    assert len(records) == 2

    with patch("app.crawlers.crawler.Session", session_factory):
        scraper.save_to_database(records)

    with session_factory() as session:
        teams = session.query(HockeyTeam).order_by(HockeyTeam.name).all()
        assert len(teams) == 2
        assert teams[0].name == "Bruins"
        assert teams[1].name == "Rangers"

        historics = (
            session.query(HockeyTeamHistoric).order_by(HockeyTeamHistoric.team_id).all()
        )
        assert len(historics) == 2
        assert historics[0].year == 2024 and historics[0].wins == 50
        assert historics[1].year == 2024 and historics[1].wins == 48


# --- OscarScraper tests ---


@pytest.fixture
def oscar_scraper():
    return OscarScraper(headless=True)


def test_oscar_fetch_year_data(oscar_scraper):
    """_fetch_year_data returns list of film dicts from mocked AJAX JSON."""
    mock_json = [
        {
            "title": "Argo",
            "year": 2012,
            "nominations": 7,
            "awards": 3,
            "best_picture": True,
        },
        {
            "title": "Lincoln",
            "year": 2012,
            "nominations": 12,
            "awards": 2,
            "best_picture": False,
        },
    ]
    with patch("urllib.request.urlopen") as mock_open:
        mock_resp = MagicMock()
        mock_resp.read.return_value = __import__("json").dumps(mock_json).encode()
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = lambda *a: None
        mock_open.return_value = mock_resp
        result = oscar_scraper._fetch_year_data(2012)
    assert len(result) == 2
    assert result[0]["title"] == "Argo"
    assert result[0]["year"] == 2012
    assert result[0]["nominations"] == 7
    assert result[0]["awards"] == 3
    assert result[0]["best_picture"] is True
    assert result[1]["title"] == "Lincoln"
    assert result[1]["best_picture"] is False


def test_oscar_fetch_year_data_skips_empty_title(oscar_scraper):
    """_fetch_year_data skips films with empty title."""
    mock_json = [
        {"title": "  ", "year": 2012, "nominations": 0, "awards": 0},
        {"title": "Argo", "year": 2012, "nominations": 7, "awards": 3},
    ]
    with patch("urllib.request.urlopen") as mock_open:
        mock_resp = MagicMock()
        mock_resp.read.return_value = __import__("json").dumps(mock_json).encode()
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = lambda *a: None
        mock_open.return_value = mock_resp
        result = oscar_scraper._fetch_year_data(2012)
    assert len(result) == 1
    assert result[0]["title"] == "Argo"


def test_oscar_save_to_database(oscar_scraper):
    """save_to_database creates Film and OscarWinnerFilm rows (film_id link)."""
    from app.models.films import Film, OscarWinnerFilm

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    data = [
        {
            "title": "Argo",
            "year": 2012,
            "nominations": 7,
            "awards": 3,
            "best_picture": True,
        },
        {
            "title": "Lincoln",
            "year": 2012,
            "nominations": 12,
            "awards": 2,
            "best_picture": False,
        },
    ]

    with patch("app.crawlers.crawler.Session", session_factory):
        oscar_scraper.save_to_database(data, job_id="job-1")

    with session_factory() as session:
        films = session.query(Film).order_by(Film.title).all()
        assert len(films) == 2
        assert films[0].title == "Argo"
        assert films[1].title == "Lincoln"

        oscars = session.query(OscarWinnerFilm).order_by(OscarWinnerFilm.film_id).all()
        assert len(oscars) == 2
        assert oscars[0].film_id == films[0].id
        assert oscars[0].year == 2012
        assert oscars[0].nominations == 7
        assert oscars[0].awards == 3
        assert oscars[0].best_picture is True
        assert oscars[0].job_id == "job-1"
        assert oscars[1].film_id == films[1].id
        assert oscars[1].nominations == 12
        assert oscars[1].best_picture is False


def test_oscar_save_to_database_reuses_film_by_title(oscar_scraper):
    """Same title creates one Film and two OscarWinnerFilm rows."""
    from app.models.films import Film, OscarWinnerFilm

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    data = [
        {
            "title": "Argo",
            "year": 2012,
            "nominations": 7,
            "awards": 3,
            "best_picture": True,
        },
        {
            "title": "Argo",
            "year": 2013,
            "nominations": 1,
            "awards": 0,
            "best_picture": False,
        },
    ]

    with patch("app.crawlers.crawler.Session", session_factory):
        oscar_scraper.save_to_database(data, job_id="job-1")

    with session_factory() as session:
        films = session.query(Film).all()
        assert len(films) == 1
        assert films[0].title == "Argo"

        oscars = session.query(OscarWinnerFilm).order_by(OscarWinnerFilm.year).all()
        assert len(oscars) == 2
        assert oscars[0].film_id == films[0].id
        assert oscars[0].year == 2012
        assert oscars[1].film_id == films[0].id
        assert oscars[1].year == 2013
