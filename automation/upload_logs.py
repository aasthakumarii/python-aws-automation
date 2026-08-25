import boto3
from datetime import datetime
from pathlib import Path


BUCKET_NAME = "python-aws-automation-logs-aastha"

LOG_FILE = Path(
    "/home/ubuntu/python-aws-automation/app/logs/application.log"
)

s3 = boto3.client("s3")


def upload_logs():

    if not LOG_FILE.exists():
        print("Log file not found.")
        return

    now = datetime.now()

    s3_key = (
        f"logs/"
        f"{now.year}/"
        f"{now.month:02d}/"
        f"{now.day:02d}/"
        f"application.log"
    )

    s3.upload_file(
        str(LOG_FILE),
        BUCKET_NAME,
        s3_key
    )

    print(f"Uploaded logs to s3://{BUCKET_NAME}/{s3_key}")


if __name__ == "__main__":
    upload_logs()