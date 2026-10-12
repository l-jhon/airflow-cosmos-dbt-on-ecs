data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

data "tls_certificate" "github_actions" {
  url = "https://token.actions.githubusercontent.com"
}

locals {
  name_prefix           = lower(replace(var.project_name, "_", "-"))
  account_id            = data.aws_caller_identity.current.account_id
  athena_staging_bucket = "${local.name_prefix}-${local.account_id}-${var.aws_region}-athena-staging"
  dbt_manifest_bucket   = "${local.name_prefix}-${local.account_id}-${var.aws_region}-manifest"
  mwaa_bucket           = "${local.name_prefix}-${local.account_id}-${var.aws_region}-mwaa"
  raw_schema            = "${var.dbt_schema_prefix}_raw"
  stage_schema          = "${var.dbt_schema_prefix}_stage"
  analytics_schema      = "${var.dbt_schema_prefix}_analytics"
  ci_schema_prefix      = "${var.dbt_schema_prefix}_ci"
  github_repository     = "${var.github_org}/${var.github_repo}"
  task_log_group_name   = "/ecs/${local.name_prefix}"
  dbt_manifest_uri      = "s3://${aws_s3_bucket.dbt_manifest.bucket}/manifest.json"
  athena_staging_dir    = "s3://${aws_s3_bucket.athena_staging.bucket}/"
  athena_tmp_dir        = "s3://${aws_s3_bucket.athena_staging.bucket}/tmp/"
  s3_data_resources = concat(
    [
      aws_s3_bucket.athena_staging.arn,
      "${aws_s3_bucket.athena_staging.arn}/*",
      aws_s3_bucket.dbt_manifest.arn,
      "${aws_s3_bucket.dbt_manifest.arn}/*",
    ],
    var.enable_mwaa ? [aws_s3_bucket.mwaa[0].arn, "${aws_s3_bucket.mwaa[0].arn}/*"] : []
  )
}
