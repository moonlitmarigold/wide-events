import pytest
from wide_events.checks import Checks, InlineCheck
from wide_events.results.base import Status
from wide_events.results.checks import SingleCheckResult, MultiCheckResult

# carried over from execflow, where these sketch an API that isn't built yet
not_built = pytest.mark.xfail(strict=True, reason="target API from execflow, not implemented yet")


# module level, so the check names are stable
def path_exists(path):
    return path == "/ok"


def disk_gone(path):
    raise ValueError("disk gone")


def forgot_return(path):
    pass


def ignore():
    pass


def test_success_result_has_no_exception():
    result = SingleCheckResult.success("path_exists")

    assert (result.name, result.status, result.exception) == ("path_exists", Status.success, None)


def test_failed_result_has_no_exception():
    result = SingleCheckResult.failed("path_exists")

    assert (result.name, result.status, result.exception) == ("path_exists", Status.failed, None)


def test_result_from_exception_keeps_type_and_traceback():
    result = SingleCheckResult.from_exception("disk_gone", ValueError("disk gone"))

    assert result.status == Status.failed
    assert result.exception == "ValueError"
    assert "disk gone" in result.traceback


def test_truthy_return_is_success():
    assert InlineCheck(["path"], path_exists, ignore)(path="/ok").status == Status.success


def test_falsy_return_is_failed():
    assert InlineCheck(["path"], path_exists, ignore)(path="/no").status == Status.failed


def test_forgotten_return_is_failed():
    assert InlineCheck(["path"], forgot_return, ignore)(path="/ok").status == Status.failed


def test_raise_returns_a_failed_result_with_the_exception():
    result = InlineCheck(["path"], disk_gone, ignore)(path="/ok")

    assert result.status == Status.failed
    assert result.exception == "ValueError"


def test_on_error_runs_only_when_the_check_raises():
    calls = []
    on_error = lambda: calls.append("on_error")

    InlineCheck(["path"], path_exists, on_error)(path="/no")
    assert calls == []

    InlineCheck(["path"], disk_gone, on_error)(path="/ok")
    assert calls == ["on_error"]


def test_without_on_error_a_raise_still_returns_a_result():
    assert InlineCheck(["path"], disk_gone, None)(path="/ok").exception == "ValueError"


@not_built
def test_only_the_named_args_are_passed_to_the_check():
    check = InlineCheck(["path"], path_exists, ignore)

    assert check(path="/ok", host="vps-1").status == Status.success


@not_built
def test_missing_arg_raises_with_its_name():
    with pytest.raises(TypeError, match="path"):
        InlineCheck(["path"], path_exists, ignore)(pth="/ok")


def test_name_is_the_function_name():
    assert InlineCheck(["path"], path_exists, ignore)(path="/ok").name == "path_exists"


@not_built
def test_run_all_keeps_going_after_a_check_raises():
    checks = [
        InlineCheck(["path"], disk_gone, ignore),
        InlineCheck(["path"], path_exists, ignore),
        InlineCheck(["path"], forgot_return, ignore),
    ]

    result = Checks.run_all(checks, path="/ok")

    assert (result.success, result.failed) == (1, 2)
    assert [check.name for check in result.single_checks] == ["disk_gone", "path_exists", "forgot_return"]

def test_results():

    s = SingleCheckResult.success("func")
    print(s.dump())
    
    m = MultiCheckResult.count([1], [s])
    print(m)
    print(m.dump())

    checks = Checks([InlineCheck(["num"], lambda num:num % 2)])

    print(checks(num=3).dump())
    print(checks(num=2).dump())


def test_inline_check_dumps_its_func_by_name():
    assert InlineCheck(["path"], path_exists, ignore).dump() == {
        "exec": "wide_events.checks.InlineCheck",
        "exec_name": "path_exists",
        "args": ["path"],
        "func": f"{__name__}.path_exists",
        "on_error": f"{__name__}.ignore",
    }


def test_inline_check_dump_without_on_error():
    assert InlineCheck(["path"], path_exists).dump()["on_error"] is None

