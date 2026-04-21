"""
Job scraper using JobSpy library.

Scrapes Indeed, LinkedIn, Glassdoor, and Google Jobs for part-time/contract
roles matching the agent profile's target roles.
"""

import logging
import hashlib
from typing import Optional

from jobspy import scrape_jobs

import config
import supabase_utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def _make_dedup_key(title: str, company: str) -> str:
    """Create a normalized deduplication key from title + company."""
    normalized = f"{(title or '').strip().lower()}|{(company or '').strip().lower()}"
    return hashlib.md5(normalized.encode()).hexdigest()


def scrape_jobs_for_query(
    search_term: str,
    results_wanted: int = None,
) -> list:
    """
    Run a single JobSpy search and return normalized job dicts.

    Args:
        search_term: The job title/keywords to search
        results_wanted: Max results per site (defaults to config value)

    Returns:
        List of job dicts ready for Supabase insertion
    """
    results_wanted = results_wanted or config.JOBSPY_RESULTS_WANTED

    logging.info(f"Scraping jobs for: '{search_term}'")

    import pandas as pd
    all_frames = []

    for job_type in config.JOBSPY_JOB_TYPES:
        try:
            df = scrape_jobs(
                site_name=config.JOBSPY_SITES,
                search_term=search_term,
                location=config.JOBSPY_LOCATION,
                distance=config.JOBSPY_DISTANCE,
                is_remote=config.JOBSPY_IS_REMOTE,
                job_type=job_type,
                results_wanted=results_wanted,
                hours_old=config.JOBSPY_HOURS_OLD,
                country_indeed="USA",
            )
            if df is not None and not df.empty:
                all_frames.append(df)
        except Exception as e:
            logging.error(f"JobSpy scrape failed for '{search_term}' (type={job_type}): {e}")

    if not all_frames:
        logging.info(f"No results for '{search_term}'")
        return []

    jobs_df = pd.concat(all_frames, ignore_index=True).drop_duplicates(subset=["job_url"], keep="first")

    if jobs_df.empty:
        logging.info(f"No results for '{search_term}'")
        return []

    logging.info(f"Got {len(jobs_df)} raw results for '{search_term}'")

    # Normalize DataFrame rows to job dicts matching our schema
    jobs = []
    for _, row in jobs_df.iterrows():
        job_url = str(row.get("job_url", "")) if row.get("job_url") else None
        title = str(row.get("title", "")) if row.get("title") else None
        company = str(row.get("company", "")) if row.get("company") else None
        description = str(row.get("description", "")) if row.get("description") else None

        if not title or not description:
            continue

        # Use job_url as the unique ID (or hash it if too long)
        job_id = job_url if job_url else _make_dedup_key(title, company)

        # Truncate job_id if it's a very long URL
        if len(job_id) > 500:
            job_id = hashlib.md5(job_id.encode()).hexdigest()

        location = str(row.get("location", "")) if row.get("location") else None
        site = str(row.get("site", "")) if row.get("site") else None

        # Extract salary info
        min_amount = row.get("min_amount") if row.get("min_amount") and str(row.get("min_amount")) != "nan" else None
        max_amount = row.get("max_amount") if row.get("max_amount") and str(row.get("max_amount")) != "nan" else None
        interval = str(row.get("interval", "")) if row.get("interval") and str(row.get("interval")) != "nan" else None
        currency = str(row.get("currency", "")) if row.get("currency") and str(row.get("currency")) != "nan" else None
        job_type_val = str(row.get("job_type", "")) if row.get("job_type") and str(row.get("job_type")) != "nan" else None
        is_remote = bool(row.get("is_remote")) if row.get("is_remote") and str(row.get("is_remote")) != "nan" else None
        job_level = str(row.get("job_level", "")) if row.get("job_level") and str(row.get("job_level")) != "nan" else None
        job_url_direct = str(row.get("job_url_direct", "")) if row.get("job_url_direct") and str(row.get("job_url_direct")) != "nan" else None
        date_posted = str(row.get("date_posted", "")) if row.get("date_posted") and str(row.get("date_posted")) != "nan" and str(row.get("date_posted")) != "NaT" else None

        jobs.append({
            "job_id": job_id,
            "company": company,
            "job_title": title,
            "location": location,
            "description": description,
            "provider": site,
            "level": job_level,
            "job_type": job_type_val,
            "salary_min": min_amount,
            "salary_max": max_amount,
            "salary_interval": interval,
            "salary_currency": currency,
            "is_remote": is_remote,
            "job_url_direct": job_url_direct,
            "date_posted": date_posted,
        })

    return jobs


def scrape_all_queries() -> list:
    """
    Run all configured search queries through JobSpy.
    Deduplicates against existing jobs in Supabase and across queries.

    Returns:
        List of new, unique job dicts not already in the database.
    """
    logging.info("--- Starting Job Scraping ---")

    # Get existing jobs from Supabase for deduplication
    existing_ids, existing_company_title_pairs = supabase_utils.get_existing_jobs_from_supabase()
    logging.info(f"Found {len(existing_ids)} existing jobs in database")

    all_new_jobs = []
    seen_ids = set()
    seen_company_title = set()

    for query in config.SEARCH_QUERIES:
        jobs = scrape_jobs_for_query(query)

        for job in jobs:
            job_id = job["job_id"]

            # Skip if already in DB by ID
            if job_id in existing_ids:
                continue

            # Skip if already seen in this run by ID
            if job_id in seen_ids:
                continue

            # Skip if company+title combo already exists (DB or this run)
            if job.get("company") and job.get("job_title"):
                key = (
                    job["company"].strip().lower(),
                    job["job_title"].strip().lower(),
                )
                if key in existing_company_title_pairs:
                    continue
                if key in seen_company_title:
                    continue
                seen_company_title.add(key)

            # Skip jobs with empty descriptions (LinkedIn often returns these)
            desc = job.get("description", "")
            if not desc or len(desc) < 50:
                continue

            seen_ids.add(job_id)
            all_new_jobs.append(job)

    logging.info(f"--- Scraping complete: {len(all_new_jobs)} new unique jobs found ---")
    return all_new_jobs


if __name__ == "__main__":
    new_jobs = scrape_all_queries()
    if new_jobs:
        logging.info(f"Saving {len(new_jobs)} new jobs to Supabase...")
        supabase_utils.save_jobs_to_supabase(new_jobs)
    else:
        logging.info("No new jobs to save.")
