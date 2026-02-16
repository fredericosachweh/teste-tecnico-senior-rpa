import os

from dotenv import load_dotenv

load_dotenv()


def env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


# App
ENV = env("ENV", "development")
DEBUG = env("DEBUG", "false").lower() in ("true", "1", "yes")

# Database
DATABASE_URL = env("DATABASE_URL", "postgresql://user:password@localhost:5432/rpa")

# RabbitMQ
RABBITMQ_URL = env("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

# Selenium
HEADLESS = env("HEADLESS", "false").lower() in ("true", "1", "yes")

# Scraper URLs
SCRAPER_URLS = {
    "hockey": {
        "url": "https://www.scrapethissite.com/pages/forms/",
        "table_id": "hockey",
        "pagination_selector": ".pagination",
        "page_param": "page_num",
    },
    "oscar": {
        "url": "https://www.scrapethissite.com/pages/ajax-javascript/",
    },
}
