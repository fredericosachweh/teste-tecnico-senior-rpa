#!/usr/bin/env python
"""
Worker para processar jobs de crawling da fila RabbitMQ
"""

import json
import sys
import traceback
from datetime import datetime

from app.config import SCRAPER_URLS
from app.crawlers.crawler import HockeyHistoricScraper, OscarScraper
from app.database import Session
from app.models.jobs import Job, JobStatus
from app.queue import consume_jobs


def process_job(job_id: str, job_type: str):
    """
    Process a single crawl job.

    Args:
        job_id: Unique job identifier
        job_type: Type of job ('hockey' or 'oscar')
    """
    print(f" [→] Processing job {job_id} ({job_type})")

    with Session() as session:
        # Get job from database
        job = session.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            print(f" [!] Job {job_id} not found in database")
            return

        # Update status to running
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        session.commit()

        try:
            if job_type == "hockey":
                # Run Hockey scraper
                url = SCRAPER_URLS["hockey"]["url"]
                with HockeyHistoricScraper(headless=True) as scraper:
                    data = scraper.get_all_historic_data(url, job_id=job_id)
                    results_count = len(data)

            elif job_type == "oscar":
                # Run Oscar scraper (uses AJAX API directly, no Selenium needed)
                scraper = OscarScraper()
                data = scraper.get_all_oscar_data()
                scraper.save_to_database(data, job_id=job_id)
                results_count = len(data)

            else:
                raise ValueError(f"Unknown job type: {job_type}")

            # Update job status to completed
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.results_count = results_count
            session.commit()

            print(f" [✓] Job {job_id} completed successfully ({results_count} results)")

        except Exception as e:
            # Update job status to failed
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error_message = error_msg
            session.commit()

            print(f" [✗] Job {job_id} failed: {error_msg}")


def callback(ch, method, properties, body):
    """
    RabbitMQ callback function.

    Args:
        ch: Channel
        method: Method
        properties: Properties
        body: Message body (JSON)
    """
    try:
        # Parse message
        message = json.loads(body)
        job_id = message.get("job_id")
        job_type = message.get("job_type")

        if not job_id or not job_type:
            print(f" [!] Invalid message: {message}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Process job
        process_job(job_id, job_type)

        # Acknowledge message
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f" [!] Error processing message: {e}")
        traceback.print_exc()
        # Reject message (will be requeued)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    """Main worker loop"""
    print(" [*] Starting crawler worker...")
    print(" [*] Connecting to RabbitMQ...")

    try:
        consume_jobs(callback)
    except KeyboardInterrupt:
        print("\n [*] Worker stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n [!] Worker error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
