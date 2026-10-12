resource "aws_s3_object" "mwaa_requirements" {
  count = var.enable_mwaa ? 1 : 0

  bucket = aws_s3_bucket.mwaa[0].id
  key    = "requirements/requirements.txt"
  source = "${path.module}/../../airflow-local-runner/requirements.txt"
  etag   = filemd5("${path.module}/../../airflow-local-runner/requirements.txt")
}

resource "aws_mwaa_environment" "demo" {
  count = var.enable_mwaa ? 1 : 0

  name                  = "${local.name_prefix}-mwaa"
  airflow_version       = var.mwaa_airflow_version
  environment_class     = "mw1.small"
  execution_role_arn    = aws_iam_role.mwaa_execution[0].arn
  source_bucket_arn     = aws_s3_bucket.mwaa[0].arn
  dag_s3_path           = "dags"
  requirements_s3_path  = aws_s3_object.mwaa_requirements[0].key
  max_workers           = 2
  min_workers           = 1
  schedulers            = 2
  webserver_access_mode = "PUBLIC_ONLY"

  network_configuration {
    security_group_ids = [aws_security_group.ecs.id]
    subnet_ids         = aws_subnet.public[*].id
  }

  depends_on = [
    aws_s3_bucket_public_access_block.mwaa,
    aws_iam_role_policy.mwaa_execution,
  ]
}
