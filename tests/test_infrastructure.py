from automation import infrastructure


def test_project_tags_are_consistent():
    assert infrastructure.project_tags() == [
        {
            "Key": "Project",
            "Value": "python-aws-automation"
        },
        {
            "Key": "ManagedBy",
            "Value": "Boto3"
        },
    ]


def test_create_s3_bucket_returns_existing_bucket(
    monkeypatch
):
    class FakeS3:
        def list_buckets(self):
            return {
                "Buckets": [
                    {
                        "Name": infrastructure.S3_BUCKET_NAME
                    }
                ]
            }

    monkeypatch.setattr(
        infrastructure,
        "s3",
        FakeS3()
    )

    result = infrastructure.create_s3_bucket()

    assert result == infrastructure.S3_BUCKET_NAME


def test_create_s3_bucket_creates_and_tags_bucket(
    monkeypatch
):
    calls = []

    class FakeS3:
        def list_buckets(self):
            return {
                "Buckets": []
            }

        def create_bucket(
            self,
            **kwargs
        ):
            calls.append(
                (
                    "create_bucket",
                    kwargs
                )
            )

        def put_bucket_tagging(
            self,
            **kwargs
        ):
            calls.append(
                (
                    "put_bucket_tagging",
                    kwargs
                )
            )

    monkeypatch.setattr(
        infrastructure,
        "s3",
        FakeS3()
    )

    result = infrastructure.create_s3_bucket()

    assert result == infrastructure.S3_BUCKET_NAME

    assert calls[0][0] == "create_bucket"

    assert (
        calls[0][1]["Bucket"]
        == infrastructure.S3_BUCKET_NAME
    )

    assert (
        calls[0][1]["CreateBucketConfiguration"]
        == {
            "LocationConstraint": infrastructure.REGION
        }
    )

    assert calls[1][0] == "put_bucket_tagging"


def test_configure_s3_lifecycle_has_expected_transitions(
    monkeypatch
):
    captured = {}

    class FakeS3:
        def put_bucket_lifecycle_configuration(
            self,
            **kwargs
        ):
            captured.update(kwargs)

    monkeypatch.setattr(
        infrastructure,
        "s3",
        FakeS3()
    )

    infrastructure.configure_s3_lifecycle(
        "example-bucket"
    )

    rule = (
        captured[
            "LifecycleConfiguration"
        ]["Rules"][0]
    )

    assert captured["Bucket"] == "example-bucket"

    assert rule["Status"] == "Enabled"

    assert rule["Transitions"] == [
        {
            "Days": 15,
            "StorageClass": "STANDARD_IA"
        },
        {
            "Days": 60,
            "StorageClass": "GLACIER"
        },
    ]