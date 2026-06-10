from bantu_os.core.intent.goal_tree import GoalNode, GoalStatus, GoalTree


def test_goal_node_round_trip():
    root = GoalNode(text="deploy", level=0)
    root.add_child(GoalNode(text="test", level=1))
    tree = GoalTree(root=root)
    payload = tree.to_dict()
    restored = GoalTree.from_dict(payload)
    assert restored.root.text == "deploy"
    assert restored.root.children[0].text == "test"
    assert restored.root.children[0].parent_id == restored.root.id


def test_goal_status_values():
    assert GoalStatus.PENDING.value == "PENDING"
    assert GoalStatus.DONE.value == "DONE"
