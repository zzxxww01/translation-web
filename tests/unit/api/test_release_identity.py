from unittest.mock import patch
import subprocess

from src.api import release_identity as identity


def test_revision_is_validated(tmp_path):
    with patch.object(identity.subprocess, 'check_output', return_value='a' * 40 + '\n'):
        assert identity.read_revision(tmp_path) == 'a' * 40
    with patch.object(identity.subprocess, 'check_output', return_value='not-a-revision'):
        assert identity.read_revision(tmp_path) is None
    with patch.object(identity.subprocess, 'check_output', side_effect=subprocess.TimeoutExpired('git', 3)):
        assert identity.read_revision(tmp_path) is None


def test_process_identity_does_not_follow_pointer_or_changed_head():
    before = identity.release_identity()
    with patch.object(identity.subprocess, 'check_output', side_effect=AssertionError('must not re-read HEAD')):
        assert identity.release_identity() == before
    assert before['instance_id']
