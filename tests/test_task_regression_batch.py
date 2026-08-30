from batch.processor import process_batch


def test_a_failing_item_does_not_abort_the_rest_of_the_batch():
    def worker(x):
        if x == 2:
            raise ValueError("boom")
        return x * 10

    result = process_batch([1, 2, 3], worker)
    assert result.succeeded == [10, 30]
    assert len(result.failed) == 1
    assert result.failed[0][0] == 2
