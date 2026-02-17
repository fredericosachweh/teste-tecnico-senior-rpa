import json
import os
import re
import time
import urllib.request
from typing import Dict, List, Optional
from urllib.parse import urljoin

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC  # noqa: N812
from selenium.webdriver.support.ui import WebDriverWait

from app.config import SCRAPER_URLS
from app.database import Session
from app.models.hockey_teams import HockeyTeam, HockeyTeamHistoric


class Scraper:
    """Base class for all Selenium-based scrapers"""

    def __init__(self, headless: bool = True, timeout: int = 12):
        self.headless = headless
        self.timeout = timeout
        self.driver: Optional[webdriver.Chrome] = None

    def __enter__(self):
        self._init_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _init_driver(self) -> None:
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")

        # Modern anti-detection (very often needed in 2025+)
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Use system chromedriver if available (Docker), otherwise try webdriver-manager
        chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
        chrome_bin = os.environ.get("CHROME_BIN")

        if chrome_bin:
            options.binary_location = chrome_bin

        if chromedriver_path and os.path.isfile(chromedriver_path):
            service = Service(chromedriver_path)
        else:
            try:
                from webdriver_manager.chrome import ChromeDriverManager

                service = Service(ChromeDriverManager().install())
            except ImportError:
                service = Service()  # fallback to PATH

        self.driver = webdriver.Chrome(service=service, options=options)

        # Better webdriver hiding (executed on every new document)
        # fmt: off
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'languages',
                    { get: () => ['en-US', 'en'] });
                Object.defineProperty(navigator, 'plugins',
                    { get: () => [1, 2, 3, 4, 5] });
            """},
        )
        # fmt: on

    def close(self) -> None:
        if self.driver is not None:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None


class HockeyHistoricScraper(Scraper):
    """Scrapes hockey teams historic / results table with pagination (?page_num=…)"""

    TABLE_ID = SCRAPER_URLS["hockey"]["table_id"]
    PAGINATION_SELECTOR = SCRAPER_URLS["hockey"]["pagination_selector"]
    PAGE_PARAM = SCRAPER_URLS["hockey"]["page_param"]

    def parse_page_data(self, page_data: WebElement) -> List[Dict[str, str]]:
        table = page_data.find_element(By.TAG_NAME, "table")
        rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # skip header

        data = []
        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 9:
                    continue

                entry = {
                    "name": cells[0].text.strip(),
                    "year": cells[1].text.strip(),
                    "wins": cells[2].text.strip(),
                    "losses": cells[3].text.strip(),
                    "losses_ot": cells[4].text.strip(),
                    "wins_percentage": cells[5].text.strip(),
                    "goals_for": cells[6].text.strip(),
                    "goals_against": cells[7].text.strip(),
                    "goal_difference": cells[8].text.strip(),
                }
                data.append(entry)
            except StaleElementReferenceException:
                continue  # row disappeared → skip

        return data

    def _extract_page_data(self) -> WebElement:
        try:
            page_data = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.ID, self.TABLE_ID))
            )
            return page_data

        except Exception as e:
            print(f"Failed to extract page data: {type(e).__name__}: {e}")
            return []

    def _get_pagination_urls(self, base_url: str) -> List[str]:
        """Collect all unique page URLs from pagination block"""
        urls = set()

        try:
            pagination = self.driver.find_element(
                By.CSS_SELECTOR, self.PAGINATION_SELECTOR
            )
            links = pagination.find_elements(By.TAG_NAME, "a")

            for link in links:
                try:
                    href = link.get_attribute("href")
                    if not href:
                        continue
                    page_number = re.search(r"page_num=(\d+)", href).group(1)
                    full_url = urljoin(base_url, "?page_num=" + page_number)
                    urls.add(full_url)
                except Exception:
                    continue

            def page_num_key(url: str) -> int:
                return int(re.search(rf"{self.PAGE_PARAM}=(\d+)", url).group(1))

            return sorted(list(urls), key=page_num_key)

        except (NoSuchElementException, StaleElementReferenceException):
            return []

    def get_all_historic_data(
        self,
        base_url: str,
        save_per_page: bool = False,
        job_id: str = None,
    ) -> List[Dict[str, str]]:
        """
        Main entry point — collects data from all pages
        """
        if not self.driver:
            raise RuntimeError("Driver not initialized. Use 'with' statement.")

        all_data: List[Dict[str, str]] = []
        visited: set[str] = set()

        try:
            # ── First page ───────────────────────────────────────
            self.driver.get(base_url)
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.ID, self.TABLE_ID))
            )

            current_url = self.driver.current_url
            visited.add(current_url)

            page_data = self._extract_page_data()
            if not page_data:
                print("No records on page 1 → stopping")
                return []

            parsed_data = self.parse_page_data(page_data)
            all_data.extend(parsed_data)
            print(f"Page 1: {len(parsed_data)} records")

            # ── Collect & sort pagination links ──────────────────
            page_urls = self._get_pagination_urls(base_url)

            # ── Crawl remaining pages ────────────────────────────
            for idx, url in enumerate(page_urls, start=2):
                if url in visited:
                    continue

                self.driver.get(url)
                try:
                    WebDriverWait(self.driver, self.timeout).until(
                        EC.presence_of_element_located((By.ID, self.TABLE_ID))
                    )
                except TimeoutException:
                    print(f"Timeout on page {idx} → stopping")
                    break

                page_data = self._extract_page_data()
                parsed_data = self.parse_page_data(page_data)
                if not parsed_data:
                    print(f"No records on page {idx} → stopping")
                    break
                if save_per_page:
                    self.save_to_database(parsed_data, job_id)
                all_data.extend(parsed_data)
                visited.add(self.driver.current_url)
                print(f"Page {idx}: {len(parsed_data)} records")

            print(f"Total collected: {len(all_data)} records")
            if not save_per_page:
                self.save_to_database(all_data, job_id)
            return all_data

        except TimeoutException as e:
            raise TimeoutException(f"Timeout waiting for #{self.TABLE_ID} table") from e
        except Exception as e:
            raise RuntimeError(f"Scraping failed: {type(e).__name__}: {e}") from e

    def save_to_database(self, data: List[Dict[str, str]], job_id: str = None) -> None:
        """Save data to database"""

        def to_int(val, default=0):
            try:
                return int(val)
            except (ValueError, TypeError):
                return default

        def to_float(val, default=0.0):
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        with Session() as session:
            for row in data:
                team = (
                    session.query(HockeyTeam)
                    .filter(HockeyTeam.name == row["name"])
                    .one_or_none()
                )
                if not team:
                    team = HockeyTeam(name=row["name"])
                    session.add(team)
                    session.commit()
                    session.refresh(team)

                historic = HockeyTeamHistoric(
                    team_id=team.id,
                    year=to_int(row["year"]),
                    wins=to_int(row["wins"]),
                    losses=to_int(row["losses"]),
                    losses_ot=to_int(row["losses_ot"]),
                    wins_percentage=to_float(row["wins_percentage"]),
                    goals_for=to_float(row["goals_for"]),
                    goals_against=to_float(row["goals_against"]),
                    goal_difference=to_float(row["goal_difference"]),
                    job_id=job_id,
                )
                session.add(historic)
            session.commit()


class OscarScraper(Scraper):
    """
    Scrapes Oscar winning films data loaded via AJAX/JavaScript.

    The target page loads data via AJAX endpoint:
    GET /pages/ajax-javascript/?ajax=true&year=YYYY

    Strategy: directly call the AJAX API for each year (2010-2015)
    which returns clean JSON — more reliable than DOM interaction.
    """

    BASE_URL = SCRAPER_URLS["oscar"]["url"]

    def get_years(self) -> List[int]:
        try:
            req = urllib.request.Request(
                self.BASE_URL, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8")
                years = re.findall(r'class="year-link" id="(\d+)"', html)
                return sorted(set([int(year) for year in years]))
        except Exception as e:
            print(f"Error getting years: {type(e).__name__}: {e}")
            return []

    def _fetch_year_data(self, year: int) -> List[Dict[str, any]]:
        """Fetch film data for a specific year via the AJAX endpoint."""
        url = f"{self.BASE_URL}?ajax=true&year={year}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                films = json.loads(raw)

            data = []
            for film in films:
                entry = {
                    "title": film.get("title", "").strip(),
                    "year": int(film.get("year", year)),
                    "nominations": int(film.get("nominations", 0)),
                    "awards": int(film.get("awards", 0)),
                    "best_picture": bool(film.get("best_picture", False)),
                }
                if entry["title"]:
                    data.append(entry)
            return data

        except Exception as e:
            print(f"Error fetching year {year}: {type(e).__name__}: {e}")
            return []

    def get_all_oscar_data(self, base_url: str = None) -> List[Dict[str, any]]:
        """
        Main entry point — collects Oscar data from all years via AJAX API
        """
        all_data: List[Dict[str, any]] = []

        years = self.get_years()  # 2010 through 2015

        for year in years:
            films = self._fetch_year_data(year)
            all_data.extend(films)
            print(f"Year {year}: {len(films)} films")
            time.sleep(0.3)  # polite delay

        print(f"Total collected: {len(all_data)} films")
        return all_data

    def save_to_database(self, data: List[Dict[str, any]], job_id: str = None) -> None:
        """Save Oscar data: create Film by title, then OscarWinnerFilm with film_id."""
        from app.models.films import Film, OscarWinnerFilm

        with Session() as session:
            for row in data:
                film = (
                    session.query(Film).filter(Film.title == row["title"]).one_or_none()
                )
                if not film:
                    film = Film(title=row["title"])
                    session.add(film)
                    session.flush()
                oscar = OscarWinnerFilm(
                    film_id=film.id,
                    year=row["year"],
                    nominations=row["nominations"],
                    awards=row["awards"],
                    best_picture=row.get("best_picture", False),
                    job_id=job_id,
                )
                session.add(oscar)
            session.commit()
