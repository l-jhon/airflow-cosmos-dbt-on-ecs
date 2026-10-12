output "aws_region" {
  value = var.aws_region
}

output "athena_staging_bucket" {
  value = aws_s3_bucket.athena_staging.bucket
}

output "athena_staging_dir" {
  value = local.athena_staging_dir
}

output "athena_tmp_dir" {
  value = local.athena_tmp_dir
}

output "dbt_manifest_bucket" {
  value = aws_s3_bucket.dbt_manifest.bucket
}

output "dbt_manifest_uri" {
  value = local.dbt_manifest_uri
}

output "raw_schema" {
  value = aws_glue_catalog_database.raw.name
}

output "stage_schema" {
  value = aws_glue_catalog_database.stage.name
}

output "analytics_schema" {
  value = aws_glue_catalog_database.analytics.name
}

output "ci_schema_prefix" {
  value = local.ci_schema_prefix
}

output "ecs_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "ecs_security_group_id" {
  value = aws_security_group.ecs.id
}

output "ecs_network_configuration" {
  value = {
    awsvpcConfiguration = {
      assignPublicIp = "ENABLED"
      securityGroups = [aws_security_group.ecs.id]
      subnets        = aws_subnet.public[*].id
    }
  }
}

output "ecs_task_execution_role_arn" {
  value = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  value = aws_iam_role.ecs_task.arn
}

output "ecs_log_group" {
  value = aws_cloudwatch_log_group.ecs.name
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}

output "mwaa_bucket" {
  value = var.enable_mwaa ? aws_s3_bucket.mwaa[0].bucket : null
}

output "mwaa_name" {
  value = var.enable_mwaa ? aws_mwaa_environment.demo[0].name : null
}

output "mwaa_webserver_url" {
  value = var.enable_mwaa ? aws_mwaa_environment.demo[0].webserver_url : null
}
