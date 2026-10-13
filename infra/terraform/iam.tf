data "aws_iam_policy_document" "ecs_task_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "ecs_task_execution" {
  name               = "${local.name_prefix}-ecs-task-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

resource "aws_iam_role" "ecs_task" {
  name               = "${local.name_prefix}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_managed" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "ecs_data_access" {
  statement {
    effect = "Allow"
    actions = [
      "athena:*",
      "glue:*",
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
      "s3:GetBucketLocation",
      "s3:AbortMultipartUpload",
      "s3:ListMultipartUploadParts",
    ]
    resources = local.s3_data_resources
  }

  statement {
    effect    = "Allow"
    actions   = ["logs:CreateLogGroup"]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.ecs.arn}:*"]
  }
}

resource "aws_iam_role_policy" "ecs_task_execution" {
  name   = "${local.name_prefix}-ecs-task-execution-inline"
  role   = aws_iam_role.ecs_task_execution.id
  policy = data.aws_iam_policy_document.ecs_data_access.json
}

resource "aws_iam_role_policy" "ecs_task" {
  name   = "${local.name_prefix}-ecs-task-inline"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.ecs_data_access.json
}

resource "aws_iam_openid_connect_provider" "github_actions" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github_actions.certificates[0].sha1_fingerprint]
}

data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github_actions.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${local.github_repository}:ref:refs/heads/main",
        "repo:${local.github_repository}:pull_request",
      ]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  name               = "${local.name_prefix}-github-actions"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume_role.json
}

data "aws_iam_policy_document" "github_actions" {
  statement {
    effect = "Allow"
    actions = [
      "athena:*",
      "cloudwatch:*",
      "ecs:*",
      "glue:*",
      "logs:*",
    ]
    resources = ["*"]
  }

  statement {
    effect    = "Allow"
    actions   = ["ecr:*"]
    resources = ["arn:aws:ecr:${var.aws_region}:${local.account_id}:repository/${local.name_prefix}*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = local.s3_data_resources
  }

  statement {
    effect    = "Allow"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.ecs_task_execution.arn, aws_iam_role.ecs_task.arn]
  }
}

resource "aws_iam_role_policy" "github_actions" {
  name   = "${local.name_prefix}-github-actions-inline"
  role   = aws_iam_role.github_actions.id
  policy = data.aws_iam_policy_document.github_actions.json
}

data "aws_iam_policy_document" "mwaa_assume_role" {
  count = var.enable_mwaa ? 1 : 0

  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["airflow.amazonaws.com", "airflow-env.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "mwaa_execution" {
  count              = var.enable_mwaa ? 1 : 0
  name               = "${local.name_prefix}-mwaa-execution"
  assume_role_policy = data.aws_iam_policy_document.mwaa_assume_role[0].json
}

data "aws_iam_policy_document" "mwaa_execution" {
  count = var.enable_mwaa ? 1 : 0

  statement {
    effect = "Allow"
    actions = [
      "airflow:PublishMetrics",
      "athena:*",
      "ecs:*",
      "glue:*",
      "logs:*",
      "s3:*"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "mwaa_execution" {
  count  = var.enable_mwaa ? 1 : 0
  name   = "${local.name_prefix}-mwaa-execution-inline"
  role   = aws_iam_role.mwaa_execution[0].id
  policy = data.aws_iam_policy_document.mwaa_execution[0].json
}
