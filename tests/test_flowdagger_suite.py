"""FlowDAgger MetaWorld-12 suite materialization tests."""

from pathlib import Path

import yaml

from scripts.flowdagger_suite import materialize_configs


def test_materialize_flowdagger_suite_has_12_smokes_and_36_full_runs(
    tmp_path: Path,
) -> None:
    suite_source = (
        Path(__file__).resolve().parents[1] / "experiments/flowdagger/metaworld12_suite.yaml"
    )
    suite_target = tmp_path / "experiments/flowdagger/metaworld12_suite.yaml"
    suite_target.parent.mkdir(parents=True)
    suite_target.write_bytes(suite_source.read_bytes())

    paths = materialize_configs(root=tmp_path)

    assert len(paths) == 48
    assert sum("_smoke_" in path.name for path in paths) == 12
    assert sum("_full_" in path.name for path in paths) == 36
    full = yaml.safe_load(
        (tmp_path / "experiments/flowdagger/configs/metaworld12_hammer_full_seed42.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert full["runtime"]["formal"] is True
    assert full["native"]["suite"]["adaptation_rollouts"] == 50
    assert full["native"]["suite"]["task"] == "metaworld_hammer"
    assert full["native"]["env"]["CUDA_VISIBLE_DEVICES"] == "0"
    argv = full["native"]["argv"]
    assert argv[argv.index("--dual_buffer") + 1] == "1"
    assert argv[argv.index("--eval_video_episodes") + 1] == "2"
    assert argv[argv.index("--eval_video_fps") + 1] == "30"
