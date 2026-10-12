resource "aws_s3_bucket" "athena_staging" {
  bucket        = local.athena_staging_bucket
  force_destroy = true
}

resource "aws_s3_bucket" "dbt_manifest" {
  bucket        = local.dbt_manifest_bucket
  force_destroy = true
}

resource "aws_s3_bucket" "mwaa" {
  count         = var.enable_mwaa ? 1 : 0
  bucket        = local.mwaa_bucket
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "athena_staging" {
  bucket = aws_s3_bucket.athena_staging.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "dbt_manifest" {
  bucket = aws_s3_bucket.dbt_manifest.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "mwaa" {
  count  = var.enable_mwaa ? 1 : 0
  bucket = aws_s3_bucket.mwaa[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = local.task_log_group_name
  retention_in_days = 14
}

resource "aws_glue_catalog_database" "raw" {
  name = local.raw_schema
}

resource "aws_glue_catalog_database" "stage" {
  name = local.stage_schema
}

resource "aws_glue_catalog_database" "analytics" {
  name = local.analytics_schema
}
