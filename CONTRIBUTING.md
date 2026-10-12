# Contributing

Thanks for your interest in improving this project. Issues and pull requests are
welcome.

## Development setup

```bash
# dbt project + DAG factory
cd dbt-models
poetry install --no-interaction --no-root
poetry run dbt deps --target dev

# regenerate DAGs after editing the factory or YAML config
python dbt_dag_factory.py
```

## Before opening a pull request

Run the factory tests (this is what CI runs on every PR):

```bash
python -m unittest dags.tests.test_dbt_dag_factory
```

The test asserts that the checked-in DAG under `dags/dbt_models_dags/` matches the
output of `dbt_dag_factory.py`. If you change the factory or the YAML config,
regenerate the DAG and commit the result.

If you can, also validate the dbt project (requires AWS access to an Athena staging
location):

```bash
cd dbt-models
poetry run dbt build --select +path:models/demo --target dev
```

And format the Terraform:

```bash
cd infra/terraform
terraform fmt
```

## Guidelines

- Keep the YAML factory config-driven; avoid hardcoding pipeline specifics in the
  generator template.
- Keep ECS resource lifecycle (create → register → run → deregister → delete) inside
  the DAG tasks.
- Do not commit secrets or real AWS account IDs. `.env` is gitignored; use
  `.env.example` for documented defaults.
- Update the README and `dbt-models/README.md` when you change behavior or config.

## Reporting issues

Include what you ran, what you expected, and what happened. For DAG-generation
issues, paste the YAML config and the generated DAG.
