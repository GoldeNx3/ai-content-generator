"""Back up and clear application data (database and Redis queue) in the local Compose stack."""

from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SQL = """
TRUNCATE TABLE pipeline_job_attempts, pipeline_jobs, pipeline_job_batches, failed_jobs,
wordpress_publications, article_fix_issues, article_fixes, article_qa_issues, article_qas, articles,
research_fact_sources, research_facts, research_sources, researches,
candidates, sources RESTART IDENTITY CASCADE;
"""

# Zadania kolejki Laravela w Redisie wskazują na usunięte joby; sesje i cache zostają.
FLUSH_QUEUES = "redis-cli --scan --pattern '*queues:*' | xargs -r redis-cli del"


def compose(*args, **kwargs):
    return subprocess.run(
        ["docker", "compose", *args], cwd=ROOT, check=True, **kwargs
    )


def wipe():
    running = compose(
        "ps", "--status", "running", "--services", capture_output=True, text=True
    ).stdout.splitlines()
    if "db" not in running:
        raise RuntimeError("Kontener db nie działa. Uruchom najpierw make up lub make dev.")
    services = [name for name in ("platform", "queue", "scheduler") if name in running]
    try:
        if services:
            compose("stop", *services)
        with tempfile.NamedTemporaryFile(
            prefix="content-before-reset-", suffix=".sql", delete=False
        ) as backup:
            backup_path = Path(backup.name)
            try:
                compose(
                    "exec", "-T", "db", "pg_dump", "-U", "content", "-d", "content",
                    stdout=backup,
                )
            except BaseException:
                backup_path.unlink(missing_ok=True)
                raise
        print(f"Kopia bazy: {backup_path}", flush=True)
        compose(
            "exec", "-T", "db", "psql", "-v", "ON_ERROR_STOP=1",
            "-U", "content", "-d", "content", "-c", SQL,
        )
        compose("exec", "-T", "redis", "sh", "-c", FLUSH_QUEUES)
    finally:
        if services:
            compose("start", *services)
    print("Dane i kolejka wyczyszczone. Schemat i migracje zachowane.")
    print("Aby zasilić źródła: make seed, następnie make pipeline.")


if __name__ == "__main__":
    try:
        wipe()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Reset nie został ukończony: {error}", file=sys.stderr)
        sys.exit(1)
