from datetime import datetime as real_datetime

from automation import upload_logs


class FixedDatetime:
    @classmethod
    def now(cls):
        return real_datetime(
            2026,
            8,
            25,
            10,
            0,
            0
        )


def test_upload_logs_uploads_expected_file(
    tmp_path,
    monkeypatch,
    capsys
):
    log_file = tmp_path / "application.log"

    log_file.write_text(
        "test log\n",
        encoding="utf-8"
    )

    uploaded = {}

    def fake_upload_file(
        filename,
        bucket,
        key
    ):
        uploaded["filename"] = filename
        uploaded["bucket"] = bucket
        uploaded["key"] = key

    monkeypatch.setattr(
        upload_logs,
        "LOG_FILE",
        log_file
    )

    monkeypatch.setattr(
        upload_logs,
        "datetime",
        FixedDatetime
    )

    monkeypatch.setattr(
        upload_logs.s3,
        "upload_file",
        fake_upload_file
    )

    upload_logs.upload_logs()

    assert uploaded == {
        "filename": str(log_file),
        "bucket": "python-aws-automation-logs-aastha",
        "key": "logs/2026/08/25/application.log",
    }

    output = capsys.readouterr().out

    assert "Uploaded logs to s3://" in output


def test_upload_logs_skips_when_log_file_is_missing(
    tmp_path,
    monkeypatch,
    capsys
):
    missing_file = tmp_path / "missing.log"

    called = False

    def fake_upload_file(
        filename,
        bucket,
        key
    ):
        nonlocal called

        called = True

    monkeypatch.setattr(
        upload_logs,
        "LOG_FILE",
        missing_file
    )

    monkeypatch.setattr(
        upload_logs.s3,
        "upload_file",
        fake_upload_file
    )

    upload_logs.upload_logs()

    assert called is False

    output = capsys.readouterr().out

    assert "Log file not found." in output