"""
Job Finder System — Main Orchestration Script.

Runs the full pipeline:
1. Scrape job boards for new listings
2. Save new jobs to Supabase
3. Score unscored jobs against the agent profile
4. Send email digest of top matches

Designed to run twice daily via Claude Code Routines (or n8n fallback).
"""

import logging
import os
import time

import config
import cost_tracker
import supabase_utils
from scraper import scrape_all_queries
from score_jobs import score_unscored_jobs
from send_digest import send_digest

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def run_pipeline():
    """Execute the full job finder pipeline."""
    cost_tracker.reset()
    start_time = time.time()
    logging.info("=" * 60)
    logging.info("JOB FINDER PIPELINE — Starting")
    logging.info("=" * 60)

    skip_scrape = os.environ.get("SKIP_SCRAPE", "").lower() in ("1", "true", "yes")

    # Step 1: Scrape new jobs
    if skip_scrape:
        logging.info("\n--- STEP 1: SKIPPED (SKIP_SCRAPE=1) ---")
        new_jobs = []
    else:
        logging.info("\n--- STEP 1: Scraping job boards ---")
        new_jobs = scrape_all_queries()

    # Step 2: Save new jobs to Supabase
    if new_jobs:
        logging.info(f"\n--- STEP 2: Saving {len(new_jobs)} new jobs to Supabase ---")
        supabase_utils.save_jobs_to_supabase(new_jobs)
    else:
        logging.info("\n--- STEP 2: No new jobs to save ---")

    # Step 3: Score unscored jobs
    logging.info("\n--- STEP 3: Scoring unscored jobs ---")
    scored_jobs = score_unscored_jobs()

    # Step 4: Send email digest
    logging.info("\n--- STEP 4: Sending email digest ---")
    if scored_jobs:
        send_digest(scored_jobs)
    else:
        logging.info("No scored jobs to send in digest.")

    # Summary
    elapsed = time.time() - start_time
    logging.info("\n" + "=" * 60)
    logging.info("JOB FINDER PIPELINE — Complete")
    logging.info(f"  New jobs scraped: {len(new_jobs)}")
    logging.info(f"  Jobs scored: {len(scored_jobs)}")
    logging.info(f"  Total time: {elapsed:.1f}s")
    logging.info(f"\n{cost_tracker.tracker.summary()}")
    logging.info("=" * 60)


if __name__ == "__main__":
    # Validate required config
    missing = []
    if not config.ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not config.SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not config.SUPABASE_SERVICE_ROLE_KEY:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")

    if missing:
        logging.error(f"Missing required environment variables: {', '.join(missing)}")
        logging.error("Set these in .env or your environment before running.")
    else:
        run_pipeline()
