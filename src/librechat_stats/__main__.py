import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from rich import live, print
from rich.console import Console
from rich.spinner import Spinner

from .bq import Bq
from .mongo import LibreChatMongo

console = Console()


@dataclass
class Config:
    mongodb_url: str
    gcp_project_id: str
    gcp_dataset_id: str
    gcp_dataset_location: str
    since_days: int = 2

    @classmethod
    def from_env(cls):
        missing = []
        mapping = {
            "MONGODB_URL": (True, "mongodb_url", str),
            "GCP_PROJECT_ID": (True, "gcp_project_id", str),
            "GCP_DATASET_ID": (True, "gcp_dataset_id", str),
            "GCP_DATASET_LOCATION": (False, "gcp_dataset_location", str),
            "SINCE_DAYS": (False, "since_days", int),
        }
        kwargs = {
            "gcp_dataset_location": "EU",
            "since_days": 2,
        }

        for env_var, (req, attr, typ) in mapping.items():
            if value := os.getenv(env_var):
                try:
                    kwargs[attr] = typ(value)
                except ValueError:
                    missing.append(env_var)
            elif req:
                missing.append(env_var)

        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            missing.append("GOOGLE_APPLICATION_CREDENTIALS")

        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")

        return cls(**kwargs)


@contextmanager
def action(title: str):
    try:
        with live.Live(
            Spinner("dots2", title), refresh_per_second=12, transient=True
        ) as spinner:
            yield

        print(f"✅ {title}")
    except Exception:
        print(f"❌ {title}")
        raise


def main():
    config = Config.from_env()
    mongo = LibreChatMongo(config.mongodb_url)
    bq = Bq(
        project_id=config.gcp_project_id,
        dataset_id=config.gcp_dataset_id,
        dataset_location=config.gcp_dataset_location,
    )

    with action("Migrate BigQuery"):
        bq.migrate()

    start = datetime.now(timezone.utc) - timedelta(days=config.since_days)

    with action("Copy messages"):
        bq.upsert("message", mongo.get_messages(start))

    with action("Copy transactions"):
        bq.upsert("transaction", mongo.get_transactions(start))

    with action("Copy conversations"):
        bq.upsert("conversation", mongo.get_conversations(start))

    with action("Copy users"):
        bq.upsert("user", mongo.get_users(start))


def __main__():
    try:
        load_dotenv()
        main()
    except KeyboardInterrupt:
        print("k bye")
        sys.exit(1)
    except Exception:
        console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    __main__()
