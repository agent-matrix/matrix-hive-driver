from matrix_hive_driver.mapping.plan_ir_to_hive import compile_plan_ir_to_hive_graph


def test_compile_cmd_node():
    plan = {
        "plan_id": "p1",
        "goal": "test",
        "nodes": [{"id": "n1", "type": "CMD", "depends_on": [], "inputs": {"cmd": "ls"}}],
    }
    graph = compile_plan_ir_to_hive_graph(plan)
    assert graph["plan_id"] == "p1"
    assert len(graph["nodes"]) == 1
    assert graph["nodes"][0]["kind"] == "tool_proxy"
    assert graph["nodes"][0]["tool"] == "cmd.exec"


def test_compile_patch_node():
    plan = {
        "plan_id": "p2",
        "nodes": [{"id": "n1", "type": "PATCH", "inputs": {"diff": "..."}}],
    }
    graph = compile_plan_ir_to_hive_graph(plan)
    assert graph["nodes"][0]["tool"] == "fs.apply_patch"


def test_compile_test_node():
    plan = {
        "plan_id": "p3",
        "nodes": [{"id": "n1", "type": "TEST", "inputs": {"command": "pytest"}}],
    }
    graph = compile_plan_ir_to_hive_graph(plan)
    assert graph["nodes"][0]["tool"] == "verify.run"


def test_compile_approval_node():
    plan = {
        "plan_id": "p4",
        "nodes": [
            {
                "id": "n1",
                "type": "APPROVAL",
                "inputs": {"policy_grant_id": "pg-123"},
            }
        ],
    }
    graph = compile_plan_ir_to_hive_graph(plan)
    assert graph["nodes"][0]["kind"] == "approval_gate"
    assert graph["nodes"][0]["policy_grant_id"] == "pg-123"


def test_compile_decision_node():
    plan = {
        "plan_id": "p5",
        "nodes": [{"id": "n1", "type": "DECISION", "inputs": {"condition": "x > 0"}}],
    }
    graph = compile_plan_ir_to_hive_graph(plan)
    assert graph["nodes"][0]["kind"] == "decision"


def test_compile_unknown_node_becomes_noop():
    plan = {
        "plan_id": "p6",
        "nodes": [{"id": "n1", "type": "CUSTOM_THING", "inputs": {}}],
    }
    graph = compile_plan_ir_to_hive_graph(plan)
    assert graph["nodes"][0]["kind"] == "noop"


def test_compile_preserves_dependencies():
    plan = {
        "plan_id": "p7",
        "nodes": [
            {"id": "n1", "type": "CMD", "inputs": {}},
            {"id": "n2", "type": "TEST", "depends_on": ["n1"], "inputs": {}},
        ],
    }
    graph = compile_plan_ir_to_hive_graph(plan)
    assert graph["nodes"][1]["depends_on"] == ["n1"]
