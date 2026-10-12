variable "project_name" {
  description = "Base name used for buckets, IAM roles, and networking tags."
  type        = string
  default     = "airflow-cosmos-dbt-on-ecs"
}

variable "aws_region" {
  description = "AWS region for the demo."
  type        = string
  default     = "us-east-1"
}

variable "github_org" {
  description = "GitHub organization or user that owns the public repository."
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name for the public demo."
  type        = string
}

variable "enable_mwaa" {
  description = "Whether to provision the optional MWAA environment."
  type        = bool
  default     = false
}

variable "dbt_schema_prefix" {
  description = "Prefix for the Glue/Athena databases that dbt writes to."
  type        = string
  default     = "demo"
}

variable "vpc_cidr" {
  description = "CIDR block for the ECS demo VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Two public subnets used by ECS tasks and optional MWAA."
  type        = list(string)
  default     = ["10.42.1.0/24", "10.42.2.0/24"]
}

variable "mwaa_airflow_version" {
  description = "Airflow version for the optional MWAA environment."
  type        = string
  default     = "2.8.1"
}
