from studio.services.github_backup_service import _backup_archive


def test_github_backup_builds_a_zip():
    archive, count = _backup_archive()
    assert archive[:2] == b"PK"
    assert count > 0
