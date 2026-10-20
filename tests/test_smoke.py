import djx
import djx_engine


def test_packages_import():
    assert djx.__version__
    assert djx_engine
