import os
from dotenv import load_dotenv

load_dotenv()

# =================================================================
# 1. CORE SYSTEM CONFIGURATION
# =================================================================
SUPABASE_URL: str = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_TABLE_NAME: str = "jobs"
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY")
EMAILIT_API_KEY: str = os.environ.get("EMAILIT_API_KEY")

# =================================================================
# 2. SEARCH CONFIGURATION
# =================================================================

# Target roles to search for (from agent_profile)
SEARCH_QUERIES = [
    "AI automation engineer",
    "workflow automation developer",
    "n8n Make Zapier developer",
    "no-code automation specialist",
    "AI integration developer",
    "React developer contract remote",
    "Supabase developer",
    "freelance web developer AI",
]

# JobSpy settings
JOBSPY_SITES = ["indeed", "google"]  # LinkedIn returns empty descriptions, skip it
JOBSPY_LOCATION = "Remote"
JOBSPY_DISTANCE = 50  # miles from zip code for non-remote
JOBSPY_ZIP_CODE = "34986"  # Port St. Lucie, FL
JOBSPY_JOB_TYPES = ["contract", "parttime"]  # Run a search for each type
JOBSPY_IS_REMOTE = True
JOBSPY_RESULTS_WANTED = 25  # per search query
JOBSPY_HOURS_OLD = 72  # jobs posted in last 72 hours (widen for initial runs)

# =================================================================
# 3. SCORING CONFIGURATION
# =================================================================
SCORING_MODEL = "claude-haiku-4-5-20251001"
SCORING_THRESHOLD = 5  # minimum score to include in digest (out of 10)
JOBS_TO_SCORE_PER_RUN = 50

# =================================================================
# 4. EMAIL CONFIGURATION
# =================================================================
EMAILIT_FROM = "Job Scout <notifications@coreindustries.io>"
EMAILIT_TO = "otis@ventr.so"
EMAILIT_API_URL = "https://api.emailit.com/v1/emails"

# =================================================================
# 5. PROCESSING LIMITS
# =================================================================
# =================================================================
# 6. FEEDBACK WEBHOOK
# =================================================================
N8N_FEEDBACK_WEBHOOK_URL = "https://coreindustries.app.n8n.cloud/webhook/job-feedback"

JOB_EXPIRY_DAYS = 30
JOB_DELETION_DAYS = 60
