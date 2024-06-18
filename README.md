# Statistics exporter for LibreChat

This project will export statistics from LibreChat into a BigQuery database.

The environment variables that need to be set are:

-   `MONGODB_URL` &mdash; URL to LibreChat's MongoDB database (more on that
    later)
-   `GCP_PROJECT` &mdash; Google Cloud Platform project ID
-   `GCP_DATASET_ID` &mdash; BigQuery dataset ID (will be created automatically
    if not present)
-   `GOOGLE_APPLICATION_CREDENTIALS` &mdash; Path to the Google Cloud Platform
    service account key file

In addition, the following variables are available:

-   `SINCE_DAYS` &mdash; Number of days to go back in time when exporting
    statistics (default: `2`)
-   `GCP_DATASET_LOCATION` &mdash; BigQuery dataset location (default: `EU`)

## Connecting to LibreChat's Mongo

Of course this depends on how you installed it. But for example if you used the
Docker Compose method, you can add to your `docker-compose.override.yml`:

```yaml
services:
    mongodb:
        ports:
            - 27018:27017
        extra_hosts:
            - "host.docker.internal:host-gateway"
```

And then you can connect to `mongodb://host.docker.internal:27018/LibreChat`.

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
        build:
            context: ../librechat-stats
            dockerfile: Dockerfile
        environment:
            MONGODB_URL: "mongodb://host.docker.internal:27018/LibreChat"
            GCP_PROJECT: "your-gcp-project-id"
            GCP_DATASET_ID: "your-bigquery-dataset-id"
            GOOGLE_APPLICATION_CREDENTIALS: "service-account.json"
        volumes:
            - /path/to/your/service-account-key.json:/app/service-account.json
        restart: always
```
