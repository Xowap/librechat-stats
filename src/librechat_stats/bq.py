import functools
import logging
import weakref
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from google.cloud import bigquery
from google.cloud.exceptions import NotFound

logger = logging.getLogger(__name__)


def memoized_method(*lru_args, **lru_kwargs):
    def decorator(func):
        @functools.wraps(func)
        def wrapped_func(self, *args, **kwargs):
            # We're storing the wrapped method inside the instance. If we had
            # a strong reference to self the instance would never die.
            self_weak = weakref.ref(self)

            @functools.wraps(func)
            @functools.lru_cache(*lru_args, **lru_kwargs)
            def cached_method(*args, **kwargs):
                return func(self_weak(), *args, **kwargs)

            setattr(self, func.__name__, cached_method)
            return cached_method(*args, **kwargs)

        return wrapped_func

    return decorator


@dataclass(kw_only=True)
class Bq:
    project_id: str
    dataset_id: str
    client: bigquery.Client = field(init=False)
    dataset_location: str = "EU"

    def __post_init__(self):
        self.client = bigquery.Client()

    def table(self, table_id: str) -> str:
        return f"{self.project_id}.{self.dataset_id}.{table_id}"

    def ensure_dataset(self):
        did = f"{self.project_id}.{self.dataset_id}"

        try:
            self.client.get_dataset(did)
        except NotFound:
            dataset = bigquery.Dataset(did)
            dataset.location = self.dataset_location
            self.client.create_dataset(dataset)

            logger.info("Dataset %s created", self.dataset_id)

    def ensure_migrations(self):
        try:
            self.client.get_table(self.table("migration"))
        except NotFound:
            mt = bigquery.Table(self.table("migration"))
            mt.schema = [
                bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("apply_date", "TIMESTAMP", mode="REQUIRED"),
            ]
            self.client.create_table(mt)

    def migrate(self):
        self.ensure_dataset()
        self.ensure_migrations()
        migrations = [method for method in dir(self) if method.startswith("migration_")]

        migrations = sorted(migrations)
        applied_migrations = {
            x["id"]
            for x in self.client.query(
                f"SELECT id FROM `{self.table('migration')}`"  # noqa S608
            ).result()
        }

        mt = None

        for migration in migrations:
            if migration in applied_migrations:
                continue

            if not mt:
                mt = self.client.get_table(self.table("migration"))

            logger.info("Applying migration %s", repr(migration))
            getattr(self, migration)()

            self.client.insert_rows_json(
                mt,
                [
                    {
                        "id": migration,
                        "apply_date": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            )

    def migration_0001(self):
        """Create tables for Message, Transaction and Conversation."""
        message_table = bigquery.Table(self.table("message"))
        message_table.schema = [
            bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("conversation_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("date", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("sender", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("endpoint", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("model", "STRING", mode="REQUIRED"),
        ]
        self.client.create_table(message_table)
        logger.info("Table message created")

        transaction_table = bigquery.Table(self.table("transaction"))
        transaction_table.schema = [
            bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("conversation_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("context", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("date", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("model", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("pricing_type", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("token_count", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("usd_per_million", "FLOAT64", mode="REQUIRED"),
            bigquery.SchemaField("usd_total", "FLOAT64", mode="REQUIRED"),
        ]
        self.client.create_table(transaction_table)
        logger.info("Table transaction created")

        conversation_table = bigquery.Table(self.table("conversation"))
        conversation_table.schema = [
            bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("date", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("endpoint", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("model", "STRING", mode="REQUIRED"),
        ]
        self.client.create_table(conversation_table)
        logger.info("Table conversation created")

    def migration_0002(self):
        """Create table for User."""
        user_table = bigquery.Table(self.table("user"))
        user_table.schema = [
            bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("domain", "STRING", mode="REQUIRED"),
        ]
        self.client.create_table(user_table)
        logger.info("Table user created")

    def insert_rows(self, table_name: str, rows: list[dict]) -> None:
        table = self.client.get_table(self.table(table_name))
        out = self.client.insert_rows(table, rows)

        for x in out:
            match x:
                case {"errors": errors}:
                    if errors:
                        msg = f"Error inserting rows: {errors}"
                        raise Exception(msg)

    def insert_rows_json(self, table_name: str, rows: list[dict]) -> None:
        table = self.client.get_table(self.table(table_name))
        out = self.client.insert_rows_json(table, rows)

        for x in out:
            match x:
                case {"errors": errors}:
                    if errors:
                        msg = f"Error inserting rows: {errors}"
                        raise Exception(msg)

    @memoized_method(maxsize=1000)
    def get_table(self, table_id: str) -> bigquery.Table:
        return self.client.get_table(self.table(table_id))

    def upsert(self, table: str, items: list[object]) -> None:
        """Upsert items that don't yet exist."""

        if not items:
            return

        temp_table_name = f"{table}_temp_{int(datetime.now().timestamp())}"
        temp_table = bigquery.Table(self.table(temp_table_name))
        temp_table.schema = self.get_table(table).schema
        self.client.create_table(temp_table)

        try:
            rows = [asdict(item) for item in items]
            self.insert_rows(temp_table_name, rows)

            merge_sql = f"""
                MERGE `{self.table(table)}` AS target
                USING `{self.table(temp_table_name)}` AS source
                ON target.id = source.id
                WHEN NOT MATCHED BY TARGET THEN
                    INSERT ROW
            """
            self.client.query(merge_sql).result()
        finally:
            self.client.delete_table(temp_table)
