# Statistics exporter for LibreChat

This project will export statistics from LibreChat into a BigQuery database.

The environment variables that need to be set are:

-   `MONGODB_URL` &mdash; URL to LibreChat's MongoDB database
-   `GCP_PROJECT` &mdash; Google Cloud Platform project ID
-   `GCP_DATASET_ID` &mdash; BigQuery dataset ID (will be created automatically
    if not present)
-   `GOOGLE_APPLICATION_CREDENTIALS` &mdash; Path to the Google Cloud Platform
    service account key file

In addition, the following variables are available:

-   `SINCE_DAYS` &mdash; Number of days to go back in time when exporting
    statistics (default: `2`)
-   `GCP_DATASET_LOCATION` &mdash; BigQuery dataset location (default: `EU`)

## Running the exporter

You need to run the exporter regularly to keep the data in sync. A good number
is to do it every 6 hours.

The command to run the exporter is:

```sh
python -m librechat_stats
```

Let's say you want to run it using Docker Compose, first checkout the
`librechat-stats` folder next to the `LibreChat` folder on your server, then add
to your `docker-compose.override.yml`:

```yaml
services:
    librechat-stats:
        container_name: stats
        build:
            context: ../librechat-stats
            dockerfile: Dockerfile
        environment:
            MONGODB_URL: "mongodb://mongodb:27017/LibreChat"
            GCP_PROJECT_ID: "your-gcp-project-id"
            GCP_DATASET_ID: "your-bigquery-dataset-id"
            GOOGLE_APPLICATION_CREDENTIALS: "service-account.json"
        volumes:
            - /path/to/your/service-account-key.json:/app/service-account.json
        restart: always
```
