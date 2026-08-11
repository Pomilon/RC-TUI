import importlib.metadata

import rc_tui
from rc_tui import _version


def test_version_single_source():
    assert rc_tui.__version__ == _version.__version__


def test_version_matches_dist_metadata():
    try:
        dist = importlib.metadata.version("rc-tui")
    except importlib.metadata.PackageNotFoundError:
        return  # not installed; editable install in CI is, so this usually runs
    assert dist == rc_tui.__version__
