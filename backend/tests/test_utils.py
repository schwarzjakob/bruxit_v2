from src.utils.utils import rectify_signal
import numpy as np


def test_rectify_signal():
    arr = np.array([-1, 2, -3])
    result = rectify_signal(arr)
    assert np.all(result == np.array([1, 2, 3]))
