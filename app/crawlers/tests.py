from unittest.mock import MagicMock, patch

import pytest
from selenium.common.exceptions import StaleElementReferenceException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.hockey_teams import HockeyTeam, HockeyTeamHistoric

from .crawler import HockeyHistoricScraper

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
