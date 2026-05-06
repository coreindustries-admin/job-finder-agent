"""
Resend today's job digest without re-scraping or re-scoring.

Fetches today's scored jobs from Supabase (including job_url_direct)
and sends the email digest.
"""

import json
import logging
import sys
from datetime import date

import config
import supabase_utils
from send_digest import send_digest

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def fetch_todays_scored_jobs(min_score: int = None) -> list:
    """Fetch today's scored jobs from Supabase with all digest fields."""
    threshold = (min_score or config.SCORING_THRESHOLD) * 10  # DB stores score*10

    today = date.today().isoformat()  # YYYY-MM-DD

    logging.info(f"Fetching scored jobs from today ({today}) with resume_score >= {threshold}...")

    try:
        response = (
            supabase_utils.supabase.table(config.SUPABASE_TABLE_NAME)
            .select(
                "job_id, job_title, company, location, job_type, salary_min, salary_max, "
                "salary_interval, is_remote, level, job_url_direct, resume_score, "
                "score_tldr, score_pros, score_cons"
            )
            .eq("is_active", True)
            .not_.is_("resume_score", None)
            .gte("resume_score", threshold)
            .gte("scraped_at", today)
            .order("resume_score", desc=True)
            .execute()
        )

        if not response.data:
            logging.info("No scored jobs found for today.")
            return []

        logging.info(f"Found {len(response.data)} scored jobs from today.")
        return response.data

    except Exception as e:
        logging.error(f"Error fetching today's jobs: {e}")
        return []


def map_db_job_to_digest(job: dict) -> dict:
    """Map DB row fields to the format send_digest expects."""
    raw_score = job.get("resume_score") or 0
    score = raw_score // 10  # DB stores score*10, digest expects 1-10

    tldr = job.get("score_tldr") or job.get("score_reason") or ""

    pros = job.get("score_pros", [])
    cons = job.get("score_cons", [])
    if isinstance(pros, str):
        try:
            pros = json.loads(pros)
        except Exception:
            pros = []
    if isinstance(cons, str):
        try:
            cons = json.loads(cons)
        except Exception:
            cons = []

    return {
        **job,
        "score": score,
        "tldr": tldr,
        "reason": tldr,
        "pros": pros,
        "cons": cons,
    }


def main():
    logging.info("=== RESEND DIGEST ===")

    raw_jobs = fetch_todays_scored_jobs()
    if not raw_jobs:
        logging.info("Nothing to send.")
        sys.exit(0)

    digest_jobs = [map_db_job_to_digest(j) for j in raw_jobs]
    logging.info(f"Sending digest with {len(digest_jobs)} jobs...")

    success = send_digest(digest_jobs)
    if success:
        logging.info("Digest resent successfully.")
    else:
        logging.error("Failed to send digest.")
        sys.exit(1)


if __name__ == "__main__":
    main()
