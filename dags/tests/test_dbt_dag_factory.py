import importlib.util
import tempfile
import unittest
from pathlib import Path
from textwrap import dedent


REPO_ROOT = Path(__file__).resolve().parents[2]
FACTORY_PATH = REPO_ROOT / "dbt-models" / "dbt_dag_factory.py"
CONFIG_PATH = REPO_ROOT / "dbt-models" / "dbt_models_dag_config.yaml"
EXPECTED_DAG_PATH = (
    REPO_ROOT / "dags" / "dbt_models_dags" / "dag_dbt_model_demo_orders_pipeline.py"
)


def load_factory_module():
    spec = importlib.util.spec_from_file_location("dbt_dag_factory", FACTORY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestDbtDagFactory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = load_factory_module()

    def test_checked_in_demo_dag_matches_factory_output(self):
        with tempfile.TemporaryDirectory() as output_directory:
            generated_files = self.factory.write_dag_files(CONFIG_PATH, output_directory)
            self.assertEqual(len(generated_files), 1)

            generated_content = Path(generated_files[0]).read_text(encoding="utf-8")
            expected_content = EXPECTED_DAG_PATH.read_text(encoding="utf-8")

            self.assertEqual(generated_content, expected_content)

    def test_parallel_strategy_fans_out_task_groups(self):
        config = dedent(
            """
            model_groups:
              - name: parallel_demo
                schedule: "None"
                owner: "demo"
                description: "Parallel fan-out example."
                tags: ["demo", "parallel"]
                max_active_tasks: 2
                execution_strategy: parallel
                ecs:
                  cpu: 1024
                  memory: 2048
                tasks:
                  - id: stage_a
                    select: "path:models/demo/stage"
                  - id: stage_b
                    select: "path:models/demo/analytics"
            """
        )

        with tempfile.TemporaryDirectory() as temp_directory:
            config_path = Path(temp_directory) / "parallel.yaml"
            config_path.write_text(config, encoding="utf-8")

            generated_files = self.factory.write_dag_files(config_path, temp_directory)
            generated_content = Path(generated_files[0]).read_text(encoding="utf-8")

            self.assertIn(
                "start_dag >> create_cluster >> register_task >> [stage_a_group, stage_b_group] >> deregister_task >> delete_cluster >> end_dag",
                generated_content,
            )


if __name__ == "__main__":
    unittest.main()
