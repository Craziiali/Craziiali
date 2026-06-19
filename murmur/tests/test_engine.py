import pytest

from murmur.transcribe.base import Capabilities, resolve_engine, TranscriptionError


def caps(local, cloud, online):
    return Capabilities(local_available=local, cloud_available=cloud, online=online)


def test_auto_prefers_local():
    assert resolve_engine("auto", caps(True, True, True)) == "local"
    assert resolve_engine("auto", caps(True, False, False)) == "local"


def test_auto_uses_cloud_when_no_local():
    assert resolve_engine("auto", caps(False, True, True)) == "cloud"


def test_auto_raises_when_nothing():
    with pytest.raises(TranscriptionError):
        resolve_engine("auto", caps(False, False, True))
    with pytest.raises(TranscriptionError):
        resolve_engine("auto", caps(False, True, False))  # cloud key but offline


def test_local_falls_back_to_cloud():
    assert resolve_engine("local", caps(True, True, True)) == "local"
    assert resolve_engine("local", caps(False, True, True)) == "cloud"
    with pytest.raises(TranscriptionError):
        resolve_engine("local", caps(False, True, False))


def test_cloud_requires_online_and_key():
    assert resolve_engine("cloud", caps(False, True, True)) == "cloud"
    # offline cloud -> fall back to local if available
    assert resolve_engine("cloud", caps(True, True, False)) == "local"
    # offline, cloud key, no local -> error mentioning offline
    with pytest.raises(TranscriptionError):
        resolve_engine("cloud", caps(False, True, False))
    # no key, no local
    with pytest.raises(TranscriptionError):
        resolve_engine("cloud", caps(False, False, True))
