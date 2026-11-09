from wide_events.results.base import ExceptionResult, SingleStatus, Status, StatusCount


def test_single_status_repr():
    assert repr(SingleStatus("disk", Status.success)) == "SingleStatus(disk): success"


def test_status_count_repr_lists_every_status():
    results = [SingleStatus("a", Status.success)] * 3 + [SingleStatus("b", Status.failed)]

    assert repr(StatusCount.count([1] * 5, results)) == (
        "StatusCount(5): success=3, failed=1, warning=0, skipped=0, queued=0"
    )


def test_exception_result_repr_is_the_last_traceback_line():
    try:
        raise ValueError("disk gone")
    except ValueError as exc:
        result = ExceptionResult.from_exception(exc)

    assert (repr(result), repr(ExceptionResult(None, None))) == (
        "ExceptionResult: ValueError: disk gone", "ExceptionResult: None"
    )
