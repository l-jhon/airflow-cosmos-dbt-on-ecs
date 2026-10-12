# Public Athena dbt-on-ECS Demo

This folder is the public-safe dbt project used by the ECS + Airflow demo.
It keeps the same core pattern as the original internal setup:

- dbt models are packaged into a Docker image
- Airflow schedules the models through generated DAGs
- Cosmos runs dbt task groups in ECS Fargate
- GitHub Actions validates models and publishes the container image + `manifest.json`

## Demo shape

The synthetic workload is intentionally small:

- `seeds/demo_raw_orders.csv` acts as the raw dataset
- `models/demo/stage/stg_demo_orders.sql` standardizes the seed data
- `models/demo/analytics/fct_daily_orders.sql` produces a daily aggregate

That is enough to show:

- dbt on Athena
- multi-step DAG generation
- ECS task registration and execution
- manifest-driven Cosmos rendering

## Project structure

```text
dbt-models/
├── dbt_dag_factory.py
├── dbt_models_dag_config.yaml
├── dbt_project.yml
├── Dockerfile
├── Makefile
├── macros/
├── models/demo/
├── profiles.yml
└── seeds/
```

## Required environment variables

The demo is environment-driven and does not assume any internal AWS profile, bucket, or account.

```bash
AWS_REGION=us-east-1
AWS_PROFILE=demo-athena
DBT_TARGET=dev

DBT_ATHENA_S3_STAGING_DIR=s3://replace-me-athena-staging/
DBT_ATHENA_S3_TMP_TABLE_DIR=s3://replace-me-athena-staging/tmp/
```

The demo database, work group, and schema names live in `profiles.yml` and `dbt_project.yml` because they are not secrets.

For container publishing:

```bash
PROJECT_NAME=airflow-cosmos-dbt-on-ecs
ENV=dev
AWS_ACCOUNT_ID=123456789012
ECR_REPOSITORY=${PROJECT_NAME}-${ENV}
DBT_MANIFEST_URI=s3://replace-me-manifest/manifest.json
```

## Local dbt workflow

Install dependencies and validate the demo models:

```bash
cd dbt-models
poetry install --no-interaction --no-root
poetry run dbt deps --target dev
poetry run dbt build --select +path:models/demo --target dev
```

To clean up CI/demo schemas after an isolated run:

```bash
poetry run dbt run-operation cleanup_demo_schemas --args '{"schemas": ["demo_raw", "demo_stage", "demo_analytics"]}' --target dev
```

## Docker workflow

Build the image:

```bash
cd dbt-models
make build_image ENV=dev PROJECT_NAME=airflow-cosmos-dbt-on-ecs
```

Run dbt inside the image:

```bash
docker run \
  -e AWS_PROFILE="${AWS_PROFILE}" \
  -e AWS_REGION="${AWS_REGION}" \
  -e DBT_TARGET=prod \
  -e DBT_ATHENA_S3_STAGING_DIR="${DBT_ATHENA_S3_STAGING_DIR}" \
  -e DBT_ATHENA_S3_TMP_TABLE_DIR="${DBT_ATHENA_S3_TMP_TABLE_DIR}" \
  -v ~/.aws:/home/appuser/.aws \
  -it airflow-cosmos-dbt-on-ecs-dev \
  dbt build --select +path:models/demo --target prod
```

## Generate the Airflow DAG

The public contract lives in `dbt_models_dag_config.yaml`.
Each DAG group must define:

- `name`
- `schedule`
- `owner`
- `description`
- `tags`
- `max_active_tasks`
- `execution_strategy`
- `ecs.cpu`
- `ecs.memory`
- `tasks[].id`
- `tasks[].select`

Generate the checked-in demo DAG:

```bash
cd dbt-models
python dbt_dag_factory.py
```

The output is written to `../dags/dbt_models_dags/`.

## Local Airflow quickstart

The primary orchestration path is the Docker Compose setup in `../airflow-local-runner`.

```bash
cd dbt-models
make setup_airflow_locally
```

Before starting Airflow, update `../airflow-local-runner/config/airflow-variables.json` with:

- `dbt_manifest_uri`
- `dbt_image_uri`
- `ecs_task_execution_role_arn`
- `ecs_task_role_arn`
- `ecs_network_configuration`

The local Airflow UI is available at `http://localhost:8080` with `admin` / `admin`.

## CI/CD and Terraform

- `.github/workflows/dbt_models_ci_pipeline.yml` validates DAG generation and runs Athena-backed dbt integration tests for trusted runs.
- `.github/workflows/dbt_models_cd_pipeline.yml` assumes AWS via GitHub OIDC, creates the ECR repo if needed, pushes the image, and uploads `manifest.json`.
- `../infra/terraform/` provisions the public demo AWS layer and optionally MWAA when `enable_mwaa=true`.
