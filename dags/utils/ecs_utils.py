import json
import os

from airflow.models import Variable
from airflow.models.dag import DAG
from airflow.providers.amazon.aws.operators.ecs import (
    EcsCreateClusterOperator,
    EcsDeleteClusterOperator,
    EcsDeregisterTaskDefinitionOperator,
    EcsRegisterTaskDefinitionOperator,
    EcsRunTaskOperator,
)


DEFAULT_REGION = os.getenv("AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_DEFAULT_REGION", DEFAULT_REGION)


def _setting(
    variable_names,
    env_names=None,
    default=None,
    deserialize_json=False,
):
    if env_names is None:
        env_names = []

    if isinstance(variable_names, str):
        variable_names = [variable_names]

    if isinstance(env_names, str):
        env_names = [env_names]

    for variable_name in variable_names:
        try:
            return Variable.get(variable_name, deserialize_json=deserialize_json)
        except Exception:
            continue

    for env_name in env_names:
        env_value = os.getenv(env_name)
        if env_value is None:
            continue
        if deserialize_json:
            return json.loads(env_value)
        return env_value

    return default


ENV = _setting(["environment"], ["ENVIRONMENT", "DBT_TARGET"], "dev")
DBT_RUNTIME_ENV_KEYS = [
    (["dbt_athena_s3_staging_dir"], ["DBT_ATHENA_S3_STAGING_DIR"], "DBT_ATHENA_S3_STAGING_DIR"),
    (["dbt_athena_s3_tmp_table_dir"], ["DBT_ATHENA_S3_TMP_TABLE_DIR"], "DBT_ATHENA_S3_TMP_TABLE_DIR"),
]
NETWORK_CONFIGURATION = _setting(
    ["ecs_network_configuration", "ecs_network_configurations"],
    ["ECS_NETWORK_CONFIGURATION"],
    {
        "awsvpcConfiguration": {
            "assignPublicIp": "ENABLED",
            "securityGroups": [],
            "subnets": [],
        }
    },
    deserialize_json=True,
)


def _dbt_container_environment(environment: str, aws_region: str):
    dbt_environment = {
        "DBT_TARGET": environment,
        "AWS_REGION": aws_region,
    }

    profile_name = _setting(["dbt_profile_name"], ["DBT_PROFILE_NAME"], "demo-athena")
    if profile_name:
        dbt_environment["DBT_PROFILE_NAME"] = str(profile_name)

    for variable_names, env_names, key in DBT_RUNTIME_ENV_KEYS:
        value = _setting(variable_names, env_names, None)
        if value:
            dbt_environment[key] = str(value)

    return [{"name": key, "value": value} for key, value in dbt_environment.items()]


def create_ecs_cluster(
    project_name: str,
    dag: DAG,
    env: str = None,
    aws_conn_id: str = "aws_default",
) -> EcsCreateClusterOperator:
    environment = env if env is not None else ENV

    return EcsCreateClusterOperator(
        task_id="create_ecs_cluster",
        cluster_name=f"{project_name}-{environment}-fargate-cluster",
        wait_for_completion=True,
        create_cluster_kwargs={
            "capacityProviders": ["FARGATE_SPOT", "FARGATE"],
            "defaultCapacityProviderStrategy": [
                {
                    "capacityProvider": "FARGATE_SPOT",
                    "weight": 100,
                    "base": 1,
                }
            ],
            "tags": [
                {"key": "project", "value": project_name},
            ],
        },
        aws_conn_id=aws_conn_id,
        dag=dag,
    )


def register_ecs_task(
    project_name: str,
    dag: DAG,
    cpu: int,
    memory: int,
    env: str = None,
    image_uri: str = None,
    execution_role_arn: str = None,
    task_role_arn: str = None,
    log_group: str = None,
    container_name: str = "main-container",
    aws_conn_id: str = "aws_default",
) -> EcsRegisterTaskDefinitionOperator:
    environment = env if env is not None else ENV
    aws_region = _setting(["aws_region"], ["AWS_REGION"], DEFAULT_REGION)
    aws_account_id = _setting(["aws_account_id"], ["AWS_ACCOUNT_ID"], "123456789012")

    image_uri = image_uri or _setting(
        ["dbt_image_uri", "ecs_task_image_uri"],
        ["DBT_IMAGE_URI", "ECS_TASK_IMAGE_URI"],
        f"{aws_account_id}.dkr.ecr.{aws_region}.amazonaws.com/{project_name}-{environment}:latest",
    )
    execution_role_arn = execution_role_arn or _setting(
        ["ecs_task_execution_role_arn"],
        ["ECS_TASK_EXECUTION_ROLE_ARN"],
        f"arn:aws:iam::{aws_account_id}:role/airflow-cosmos-dbt-on-ecs-ecs-task-execution",
    )
    task_role_arn = task_role_arn or _setting(
        ["ecs_task_role_arn"],
        ["ECS_TASK_ROLE_ARN"],
        execution_role_arn,
    )
    log_group = log_group or _setting(
        ["ecs_log_group"],
        ["ECS_LOG_GROUP"],
        f"/ecs/{project_name}-{environment}",
    )

    return EcsRegisterTaskDefinitionOperator(
        task_id="register_ecs_task_definition",
        family=f"{project_name}-{environment}-task-definition",
        container_definitions=[
            {
                "name": container_name,
                "image": image_uri,
                "environment": _dbt_container_environment(environment, aws_region),
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": log_group,
                        "awslogs-region": aws_region,
                        "awslogs-create-group": "true",
                        "awslogs-stream-prefix": project_name,
                    },
                },
            },
        ],
        register_task_kwargs={
            "requiresCompatibilities": ["FARGATE"],
            "cpu": str(cpu),
            "memory": str(memory),
            "networkMode": "awsvpc",
            "executionRoleArn": execution_role_arn,
            "taskRoleArn": task_role_arn,
            "tags": [
                {"key": "project", "value": project_name},
            ],
        },
        aws_conn_id=aws_conn_id,
        dag=dag,
    )


def run_ecs_task(
    project_name: str,
    task_name: str,
    command: str,
    dag: DAG,
    pool=None,
    env: str = None,
    deferrable_enabled: bool = True,
    aws_conn_id: str = "aws_default",
    network_configuration=None,
    log_group: str = None,
    container_name: str = "main-container",
) -> EcsRunTaskOperator:
    environment = env if env is not None else ENV
    aws_region = _setting(["aws_region"], ["AWS_REGION"], DEFAULT_REGION)
    network_configuration = network_configuration or NETWORK_CONFIGURATION
    log_group = log_group or _setting(
        ["ecs_log_group"],
        ["ECS_LOG_GROUP"],
        f"/ecs/{project_name}-{environment}",
    )

    run_task_operator = EcsRunTaskOperator(
        task_id=task_name,
        cluster=f"{project_name}-{environment}-fargate-cluster",
        task_definition=f"{project_name}-{environment}-task-definition",
        launch_type="FARGATE",
        network_configuration=network_configuration,
        overrides={
            "containerOverrides": [
                {
                    "name": container_name,
                    "command": command.split() if isinstance(command, str) else command,
                    "environment": [{"name": "ENV", "value": environment}],
                },
            ],
        },
        tags={"project": project_name},
        deferrable=deferrable_enabled if environment == "prod" else False,
        awslogs_group=log_group,
        awslogs_region=aws_region,
        awslogs_stream_prefix=f"{project_name}/{container_name}",
        aws_conn_id=aws_conn_id,
        dag=dag,
    )

    if pool is not None:
        run_task_operator.pool = pool

    return run_task_operator


def deregister_ecs_task(
    task_definition: str,
    dag: DAG,
    aws_conn_id: str = "aws_default",
) -> EcsDeregisterTaskDefinitionOperator:
    return EcsDeregisterTaskDefinitionOperator(
        task_id="deregister_ecs_task_definition",
        task_definition=task_definition,
        aws_conn_id=aws_conn_id,
        dag=dag,
    )


def delete_ecs_cluster(
    project_name: str,
    dag: DAG,
    env: str = None,
    aws_conn_id: str = "aws_default",
) -> EcsDeleteClusterOperator:
    environment = env if env is not None else ENV

    return EcsDeleteClusterOperator(
        task_id="delete_ecs_cluster",
        cluster_name=f"{project_name}-{environment}-fargate-cluster",
        aws_conn_id=aws_conn_id,
        dag=dag,
    )
