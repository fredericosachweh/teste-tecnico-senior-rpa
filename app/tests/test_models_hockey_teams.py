import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models.hockey_teams import HockeyTeam, HockeyTeamHistoric


@pytest.fixture
def engine():
    return create_engine("sqlite:///:memory:", echo=False)


@pytest.fixture
def session(engine):
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        yield session
    Base.metadata.drop_all(engine)


class TestHockeyTeam:
    def test_create_team(self, session: Session):
        team = HockeyTeam(name="Bruins")
        session.add(team)
        session.commit()
        session.refresh(team)
        assert team.id is not None
        assert team.name == "Bruins"
        assert team.historic == []

    def test_team_has_historic_relationship(self, session: Session):
        team = HockeyTeam(name="Rangers")
        session.add(team)
        session.commit()
        session.refresh(team)
        record = HockeyTeamHistoric(
            team_id=team.id,
            year=2023,
            wins=50,
            losses=20,
            losses_ot=12,
            wins_percentage=0.650,
            goals_for=280.0,
            goals_against=220.0,
            goal_difference=60.0,
        )
        session.add(record)
        session.commit()
        session.refresh(team)
        assert len(team.historic) == 1
        assert team.historic[0].year == 2023
        assert team.historic[0].wins == 50


class TestHockeyTeamHistoric:
    def test_create_historic(self, session: Session):
        team = HockeyTeam(name="Canadiens")
        session.add(team)
        session.commit()
        session.refresh(team)
        historic = HockeyTeamHistoric(
            team_id=team.id,
            year=2024,
            wins=45,
            losses=25,
            losses_ot=10,
            wins_percentage=0.563,
            goals_for=260.0,
            goals_against=240.0,
            goal_difference=20.0,
        )
        session.add(historic)
        session.commit()
        session.refresh(historic)
        assert historic.id is not None
        assert historic.team_id == team.id
        assert historic.year == 2024
        assert historic.wins == 45
        assert historic.losses == 25
        assert historic.losses_ot == 10
        assert historic.wins_percentage == 0.563
        assert historic.goals_for == 260.0
        assert historic.goals_against == 240.0
        assert historic.goal_difference == 20.0

    def test_historic_back_populates_team(self, session: Session):
        team = HockeyTeam(name="Maple Leafs")
        session.add(team)
        session.commit()
        session.refresh(team)
        historic = HockeyTeamHistoric(
            team_id=team.id,
            year=2023,
            wins=46,
            losses=22,
            losses_ot=14,
            wins_percentage=0.634,
            goals_for=270.0,
            goals_against=230.0,
            goal_difference=40.0,
        )
        session.add(historic)
        session.commit()
        session.refresh(historic)
        assert historic.team is not None
        assert historic.team.name == "Maple Leafs"
        assert historic.team.id == team.id
