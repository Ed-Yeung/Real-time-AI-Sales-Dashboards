from graph import route_after_coder, route_after_planner


def test_planner_routes():
    assert route_after_planner({"refused": "no age column", "plan": []}) == "writer"
    assert route_after_planner({"refused": None, "plan": [{"purpose": "rank"}]}) == "coder"


def test_coder_routes():
    base = {"plan": [{}, {}, {}], "step_index": 0, "retry_count": 1, "error": "boom"}
    assert route_after_coder(base) == "retry"
    failed = {**base, "retry_count": 2}
    assert route_after_coder(failed) == "writer"
    done = {"plan": [{}], "step_index": 0, "retry_count": 1, "error": None}
    assert route_after_coder(done) == "writer"
    more = {"plan": [{}, {}], "step_index": 0, "retry_count": 1, "error": None}
    assert route_after_coder(more) == "next"


if __name__ == "__main__":
    test_planner_routes()
    test_coder_routes()
    print("routes ok")
