import argparse
import logging
import re
from pathlib import Path

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).with_name("dbt_models_dag_config.yaml")
DEFAULT_OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "dags" / "dbt_models_dags"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
LOGGER = logging.getLogger(__name__)


def sanitize_identifier(value: str) -> str:
    sanitized = re.sub(r"[^0-9a-zA-Z_]+", "_", value.strip()).strip("_")
    return sanitized or "dbt_task"


def normalize_task(task):
    if isinstance(task, str):
        return {
            "id": sanitize_identifier(task),
            "select": task,
        }

    task_id = sanitize_identifier(task["id"])
    return {
        "id": task_id,
        "select": task["select"],
    }


def normalize_group(group):
    raw_tasks = group.get("tasks")
    if raw_tasks is None:
        raw_tasks = [
            {
                "id": sanitize_identifier(model),
                "select": f"path:models/{model}",
            }
            for model in group.get("models", [])
        ]

    if not raw_tasks:
        raise ValueError(f"Group '{group['name']}' must define at least one task.")

    execution_strategy = group.get("execution_strategy", "parallel").lower()
    if execution_strategy not in {"parallel", "sequential"}:
        raise ValueError(
            f"Group '{group['name']}' has invalid execution_strategy '{execution_strategy}'."
        )

    ecs_config = group.get("ecs", {})
    schedule = group.get("schedule", "None")

    return {
        "name": group["name"],
        "dag_id": f"dag_dbt_model_{group['name'].replace('-', '_')}",
        "owner": group["owner"],
        "description": group["description"],
        "schedule_interval": None if str(schedule).lower() == "none" else schedule,
        "tags": group["tags"],
        "max_active_tasks": group.get(
            "max_active_tasks",
            group.get("max_active_task", 1),
        ),
        "execution_strategy": execution_strategy,
        "cpu": ecs_config.get("cpu", 4096),
        "memory": ecs_config.get("memory", 8192),
        "tasks": [normalize_task(task) for task in raw_tasks],
    }


def render_task_group(task):
    python_name = sanitize_identifier(task["id"])
    return f'''
    with TaskGroup(group_id="{task["id"]}") as {python_name}_group:
        DbtTaskGroup(
            group_id="run_dbt_model_{task["id"]}",
            project_config=project_config,
            profile_config=profile_config,
            execution_config=ExecutionConfig(execution_mode=ExecutionMode.AWS_ECS),
            operator_args={{
                "aws_conn_id": "aws_default",
                "cluster": f"{{PROJECT_NAME}}-{{DBT_TARGET}}-fargate-cluster",
                "task_definition": f"{{PROJECT_NAME}}-{{DBT_TARGET}}-task-definition",
                "container_name": "main-container",
                "launch_type": "FARGATE",
                "deferrable": DBT_TARGET == "prod",
                "network_configuration": NETWORK_CONFIGURATION,
            }},
            render_config=RenderConfig(
                load_method=LoadMode.DBT_MANIFEST,
                select=["{task["select"]}"],
            ),
            dag=dag,
        )
    '''


def build_task_chain(group):
    group_refs = [f"{sanitize_identifier(task['id'])}_group" for task in group["tasks"]]
    prefix = "start_dag >> create_cluster >> register_task >> "
    suffix = " >> deregister_task >> delete_cluster >> end_dag"

    if group["execution_strategy"] == "sequential":
        return prefix + " >> ".join(group_refs) + suffix

    return prefix + f"[{', '.join(group_refs)}]" + suffix


def generate_dag_file_content(group):
    task_groups = "".join(render_task_group(task) for task in group["tasks"])
    task_chain = build_task_chain(group)

    dag_template = '''import json
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


default_args = {{
    "owner": {owner!r},
    "description": {description!r},
    "retry": 3,
    "retry_delay": timedelta(minutes=1),
    "start_date": datetime(2025, 1, 1),
    "depend_on_past": False,
    "on_failure_callback": task_fail_log_alert,
}}

PROJECT_NAME = {project_name!r}
DBT_PROFILE = _variable_or_env("dbt_profile_name", "DBT_PROFILE_NAME", "demo-athena")
DBT_TARGET = _variable_or_env("environment", "DBT_TARGET", "dev")
DBT_PROJECT_PATH = _variable_or_env(
    "dbt_project_path",
    "DBT_PROJECT_PATH",
    f"{{os.environ['AIRFLOW_HOME']}}/dags/dbt-models",
)
DBT_MANIFEST_URI = _variable_or_env(
    "dbt_manifest_uri",
    "DBT_MANIFEST_URI",
    f"{{DBT_PROJECT_PATH}}/target/manifest.json",
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
                '{{"awsvpcConfiguration": {{"assignPublicIp": "ENABLED", "securityGroups": [], "subnets": []}}}}',
            )
        )

profile_config = ProfileConfig(
    profile_name=DBT_PROFILE,
    target_name=DBT_TARGET,
    profiles_yml_filepath=Path(f"{{DBT_PROJECT_PATH}}/profiles.yml"),
)

project_config = ProjectConfig(
    dbt_project_path=DBT_PROJECT_PATH,
    partial_parse=False,
    models_relative_path="models/",
    manifest_path=DBT_MANIFEST_URI,
)

with DAG(
    dag_id={dag_id!r},
    default_args=default_args,
    schedule_interval={schedule_interval!r},
    tags={tags!r},
    catchup=False,
    max_active_runs=1,
    max_active_tasks={max_active_tasks},
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
        cpu={cpu},
        memory={memory},
        image_uri=DBT_IMAGE_URI or None,
        execution_role_arn=ECS_TASK_EXECUTION_ROLE_ARN,
        task_role_arn=ECS_TASK_ROLE_ARN,
        log_group=ECS_LOG_GROUP,
    )

{task_groups}

    deregister_task = deregister_ecs_task(
        task_definition=register_task.output,
        dag=dag,
    )
    deregister_task.trigger_rule = "all_done"

    delete_cluster = delete_ecs_cluster(
        project_name=PROJECT_NAME,
        dag=dag,
    )

    {task_chain}
'''

    return dag_template.format(
        owner=group["owner"],
        description=group["description"],
        project_name=group["name"],
        dag_id=group["dag_id"],
        schedule_interval=group["schedule_interval"],
        tags=group["tags"],
        max_active_tasks=group["max_active_tasks"],
        cpu=group["cpu"],
        memory=group["memory"],
        task_groups=task_groups,
        task_chain=task_chain,
    )


def load_config(config_path):
    with Path(config_path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def write_dag_files(config_path=DEFAULT_CONFIG_PATH, output_directory=DEFAULT_OUTPUT_DIRECTORY):
    config = load_config(config_path)
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    generated_files = []
    for raw_group in config["model_groups"]:
        group = normalize_group(raw_group)
        dag_content = generate_dag_file_content(group)
        output_file = output_directory / f"{group['dag_id']}.py"
        output_file.write_text(dag_content, encoding="utf-8")
        generated_files.append(output_file)
        LOGGER.info("Generated DAG file: %s", output_file)

    return generated_files


def parse_args():
    parser = argparse.ArgumentParser(description="Generate dbt ECS DAG files from YAML.")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the YAML config file.",
    )
    parser.add_argument(
        "--output-directory",
        default=str(DEFAULT_OUTPUT_DIRECTORY),
        help="Directory where DAG files should be written.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    write_dag_files(args.config, args.output_directory)
