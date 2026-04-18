import pytest
from logic import get_item

def test_get_item():
    assert get_item([1, 2, 3], 1) == 2
    assert get_item([], 0) is None
    # with pytest.raises(IndexError):
    #     get_item([], 0)  # Should fail initially