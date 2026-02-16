from app.database import Base
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


# Hockey Team
class HockeyTeam(Base):
    __tablename__ = "hockey_team"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    historic: Mapped[list["HockeyTeamHistoric"]] = relationship(
        "HockeyTeamHistoric", back_populates="team", lazy="joined"
    )


# Hockey Team Historic
class HockeyTeamHistoric(Base):
    __tablename__ = "hockey_team_historic"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("hockey_team.id"))
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, nullable=False)
    losses_ot: Mapped[int] = mapped_column(Integer, nullable=False)
    wins_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    goals_for: Mapped[float] = mapped_column(Float, nullable=False)
    goals_against: Mapped[float] = mapped_column(Float, nullable=False)
    goal_difference: Mapped[float] = mapped_column(Float, nullable=False)
    job_id: Mapped[str] = mapped_column(String, nullable=True)

    team: Mapped["HockeyTeam"] = relationship("HockeyTeam", back_populates="historic")
