from batch.processor import process_batch


def test_all_success_batch_returns_every_result_in_order():
    result = process_batch([1, 2, 3], lambda x: x * 2)
    assert result.succeeded == [2, 4, 6]
    assert result.failed == []
