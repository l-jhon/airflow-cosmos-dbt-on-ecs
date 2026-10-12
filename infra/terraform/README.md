# Terraform bootstrap for the public dbt-on-ECS demo

This Terraform stack provisions the AWS resources used by the public demo:

- public-subnet networking for ECS Fargate
- Athena/Glue databases for the demo schemas
- S3 buckets for Athena staging and the dbt manifest artifact
- ECS task execution and task roles
- GitHub OIDC role for CI/CD
- optional MWAA resources when `enable_mwaa=true`

## Usage

```bash
cd infra/terraform
terraform init
terraform apply \
  -var github_org=your-org \
  -var github_repo=your-repo
```

To enable the optional MWAA path:

```bash
terraform apply \
  -var github_org=your-org \
  -var github_repo=your-repo \
  -var enable_mwaa=true
```

After apply, use the outputs to populate:

- `dbt-models` env vars such as `DBT_ATHENA_S3_STAGING_DIR`
- GitHub repository variables used by the demo workflows
- `airflow-local-runner/config/airflow-variables.json`
