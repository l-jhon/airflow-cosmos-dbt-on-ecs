import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.models import Variable
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup
from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import ExecutionMode, LoadMode

from utils.ecs_utils import create_ecs_cluster, delete_ecs_cluster, deregister_ecs_task, register_ecs_task


def task_fail_log_alert(context):
    task_instance = context.get("task_instance")
    logging.error(
        "Task failed. dag_id=%s task_id=%s execution_date=%s",
        getattr(task_instance, "dag_id", "unknown"),
        getattr(task_instance, "task_id", "unknown"),
        context.get("execution_date"),
    )


def _variable_or_env(name, env_name, default, deserialize_json=False):
    try:
        return Variable.get(name, deserialize_json=deserialize_json)
    except Exception:
        env_value = os.getenv(env_name)
        if env_value is None:
            return default
        if deserialize_json:
            return json.loads(env_value)
        return env_value


default_args = {
    "owner": 'community-demo',
    "description": 'Run the public Athena dbt demo in ECS.',
    "retry": 3,
    "retry_delay": timedelta(minutes=1),
    "start_date": datetime(2025, 1, 1),
    "depend_on_past": False,
    "on_failure_callback": task_fail_log_alert,
}

PROJECT_NAME = 'demo_orders_pipeline'
DBT_PROFILE = _variable_or_env("dbt_profile_name", "DBT_PROFILE_NAME", "demo-athena")
DBT_TARGET = _variable_or_env("environment", "DBT_TARGET", "dev")
DBT_PROJECT_PATH = _variable_or_env(
    "dbt_project_path",
    "DBT_PROJECT_PATH",
    f"{os.environ['AIRFLOW_HOME']}/dags/dbt-models",
)
DBT_MANIFEST_URI = _variable_or_env(
    "dbt_manifest_uri",
    "DBT_MANIFEST_URI",
    f"{DBT_PROJECT_PATH}/target/manifest.json",
)
DBT_IMAGE_URI = _variable_or_env("dbt_image_uri", "DBT_IMAGE_URI", "")
ECS_TASK_EXECUTION_ROLE_ARN = _variable_or_env(
    "ecs_task_execution_role_arn",
    "ECS_TASK_EXECUTION_ROLE_ARN",
    None,
)
ECS_TASK_ROLE_ARN = _variable_or_env(
    "ecs_task_role_arn",
    "ECS_TASK_ROLE_ARN",
    ECS_TASK_EXECUTION_ROLE_ARN,
)
ECS_LOG_GROUP = _variable_or_env("ecs_log_group", "ECS_LOG_GROUP", None)

try:
    NETWORK_CONFIGURATION = Variable.get("ecs_network_configuration", deserialize_json=True)
except Exception:
    try:
        NETWORK_CONFIGURATION = Variable.get("ecs_network_configurations", deserialize_json=True)
    except Exception:
        NETWORK_CONFIGURATION = json.loads(
            os.getenv(
                "ECS_NETWORK_CONFIGURATION",
                '{"awsvpcConfiguration": {"assignPublicIp": "ENABLED", "securityGroups": [], "subnets": []}}',
            )
        )

profile_config = ProfileConfig(
    profile_name=DBT_PROFILE,
    target_name=DBT_TARGET,
    profiles_yml_filepath=Path(f"{DBT_PROJECT_PATH}/profiles.yml"),
)

project_config = ProjectConfig(
    dbt_project_path=DBT_PROJECT_PATH,
    partial_parse=False,
    models_relative_path="models/",
    manifest_path=DBT_MANIFEST_URI,
)

with DAG(
    dag_id='dag_dbt_model_demo_orders_pipeline',
    default_args=default_args,
    schedule_interval='0 6 * * *',
    tags=['demo', 'dbt', 'athena', 'ecs'],
    catchup=False,
    max_active_runs=1,
    max_active_tasks=2,
) as dag:
    start_dag = EmptyOperator(task_id="start_dag", dag=dag)
    end_dag = EmptyOperator(task_id="end_dag", dag=dag)

    create_cluster = create_ecs_cluster(
        project_name=PROJECT_NAME,
        dag=dag,
    )

    register_task = register_ecs_task(
        project_name=PROJECT_NAME,
        dag=dag,
        cpu=1024,
        memory=2048,
        image_uri=DBT_IMAGE_URI or None,
        execution_role_arn=ECS_TASK_EXECUTION_ROLE_ARN,
        task_role_arn=ECS_TASK_ROLE_ARN,
        log_group=ECS_LOG_GROUP,
    )


    with TaskGroup(group_id="demo_stage") as demo_stage_group:
        DbtTaskGroup(
            group_id="run_dbt_model_demo_stage",
            project_config=project_config,
            profile_config=profile_config,
            execution_config=ExecutionConfig(execution_mode=ExecutionMode.AWS_ECS),
            operator_args={
                "aws_conn_id": "aws_default",
                "cluster": f"{PROJECT_NAME}-{DBT_TARGET}-fargate-cluster",
                "task_definition": f"{PROJECT_NAME}-{DBT_TARGET}-task-definition",
                "container_name": "main-container",
                "launch_type": "FARGATE",
                "deferrable": DBT_TARGET == "prod",
                "network_configuration": NETWORK_CONFIGURATION,
            },
            render_config=RenderConfig(
                load_method=LoadMode.DBT_MANIFEST,
                select=["+path:models/demo/stage"],
            ),
            dag=dag,
        )
    
    with TaskGroup(group_id="demo_analytics") as demo_analytics_group:
        DbtTaskGroup(
            group_id="run_dbt_model_demo_analytics",
            project_config=project_config,
            profile_config=profile_config,
            execution_config=ExecutionConfig(execution_mode=ExecutionMode.AWS_ECS),
            operator_args={
                "aws_conn_id": "aws_default",
                "cluster": f"{PROJECT_NAME}-{DBT_TARGET}-fargate-cluster",
                "task_definition": f"{PROJECT_NAME}-{DBT_TARGET}-task-definition",
                "container_name": "main-container",
                "launch_type": "FARGATE",
                "deferrable": DBT_TARGET == "prod",
                "network_configuration": NETWORK_CONFIGURATION,
            },
            render_config=RenderConfig(
                load_method=LoadMode.DBT_MANIFEST,
                select=["path:models/demo/analytics"],
            ),
            dag=dag,
        )
    

    deregister_task = deregister_ecs_task(
        task_definition=register_task.output,
        dag=dag,
    )
    deregister_task.trigger_rule = "all_done"

    delete_cluster = delete_ecs_cluster(
        project_name=PROJECT_NAME,
        dag=dag,
    )

    start_dag >> create_cluster >> register_task >> demo_stage_group >> demo_analytics_group >> deregister_task >> delete_cluster >> end_dag
