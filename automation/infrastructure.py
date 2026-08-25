import sys
import time
import boto3
from botocore.exceptions import ClientError


# ============================================================
# CONFIGURATION
# ============================================================

REGION = "ap-south-1"

PROJECT_NAME = "python-aws-automation"

INSTANCE_NAME = f"{PROJECT_NAME}-ec2"
SECURITY_GROUP_NAME = f"{PROJECT_NAME}-sg"
IAM_ROLE_NAME = f"{PROJECT_NAME}-ec2-role"
INSTANCE_PROFILE_NAME = f"{PROJECT_NAME}-instance-profile"

KEY_NAME = "key-pair-test"

AMI_ID = "ami-01a00762f46d584a1"

INSTANCE_TYPE = "t3.micro"

# Keep this stable so every setup uses the same bucket
S3_BUCKET_NAME = "python-aws-automation-logs-aastha"


# ============================================================
# AWS CLIENTS
# ============================================================

ec2 = boto3.client("ec2", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)
iam = boto3.client("iam")


# ============================================================
# TAGS
# ============================================================

def project_tags():
    return [
        {"Key": "Project", "Value": PROJECT_NAME},
        {"Key": "ManagedBy", "Value": "Boto3"}
    ]


# ============================================================
# S3
# ============================================================

def create_s3_bucket():

    print("Checking S3 bucket...")

    response = s3.list_buckets()

    for bucket in response["Buckets"]:
        if bucket["Name"] == S3_BUCKET_NAME:
            print(f"S3 bucket already exists: {S3_BUCKET_NAME}")
            return S3_BUCKET_NAME

    print(f"Creating S3 bucket: {S3_BUCKET_NAME}")

    s3.create_bucket(
        Bucket=S3_BUCKET_NAME,
        CreateBucketConfiguration={
            "LocationConstraint": REGION
        }
    )

    s3.put_bucket_tagging(
        Bucket=S3_BUCKET_NAME,
        Tagging={"TagSet": project_tags()}
    )

    print("S3 bucket created.")

    return S3_BUCKET_NAME


def configure_s3_lifecycle(bucket_name):

    print("Configuring S3 lifecycle policy...")

    s3.put_bucket_lifecycle_configuration(
        Bucket=bucket_name,
        LifecycleConfiguration={
            "Rules": [
                {
                    "ID": "log-storage-lifecycle",
                    "Status": "Enabled",
                    "Filter": {"Prefix": ""},
                    "Transitions": [
                        {
                            "Days": 15,
                            "StorageClass": "STANDARD_IA"
                        },
                        {
                            "Days": 60,
                            "StorageClass": "GLACIER"
                        }
                    ]
                }
            ]
        }
    )

    print("S3 lifecycle configured.")


# ============================================================
# IAM ROLE
# ============================================================

def create_iam_role():

    print("Checking IAM role...")

    try:
        response = iam.get_role(
            RoleName=IAM_ROLE_NAME
        )

        print(f"IAM role already exists: {IAM_ROLE_NAME}")

        return response["Role"]["Arn"]

    except iam.exceptions.NoSuchEntityException:
        pass

    print(f"Creating IAM role: {IAM_ROLE_NAME}")

    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "ec2.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    response = iam.create_role(
        RoleName=IAM_ROLE_NAME,
        AssumeRolePolicyDocument=str(
            assume_role_policy
        ).replace("'", '"'),
        Tags=project_tags()
    )

    iam.attach_role_policy(
        RoleName=IAM_ROLE_NAME,
        PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess"
    )

    print("IAM role created.")

    return response["Role"]["Arn"]


# ============================================================
# INSTANCE PROFILE
# ============================================================

def create_instance_profile():

    print("Checking instance profile...")

    try:
        response = iam.get_instance_profile(
            InstanceProfileName=INSTANCE_PROFILE_NAME
        )

        print("Instance profile already exists.")

        return response["InstanceProfile"]["Arn"]

    except iam.exceptions.NoSuchEntityException:
        pass

    print("Creating instance profile...")

    iam.create_instance_profile(
        InstanceProfileName=INSTANCE_PROFILE_NAME,
        Tags=project_tags()
    )

    iam.add_role_to_instance_profile(
        InstanceProfileName=INSTANCE_PROFILE_NAME,
        RoleName=IAM_ROLE_NAME
    )

    print("Waiting for IAM instance profile...")

    for attempt in range(12):

        try:
            response = iam.get_instance_profile(
                InstanceProfileName=INSTANCE_PROFILE_NAME
            )

            if response["InstanceProfile"]["Roles"]:
                print("Instance profile is available.")

                return response["InstanceProfile"]["Arn"]

        except iam.exceptions.NoSuchEntityException:
            pass

        time.sleep(5)

    raise RuntimeError(
        "IAM instance profile was not ready."
    )


# ============================================================
# SECURITY GROUP
# ============================================================

def create_security_group():

    print("Checking security group...")

    response = ec2.describe_security_groups(
        Filters=[
            {
                "Name": "group-name",
                "Values": [SECURITY_GROUP_NAME]
            }
        ]
    )

    if response["SecurityGroups"]:

        sg_id = response["SecurityGroups"][0]["GroupId"]

        print(f"Security group already exists: {sg_id}")

        return sg_id

    print("Creating security group...")

    response = ec2.create_security_group(
        GroupName=SECURITY_GROUP_NAME,
        Description="Security group for Python automation"
    )

    sg_id = response["GroupId"]

    ec2.create_tags(
        Resources=[sg_id],
        Tags=project_tags()
    )

    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [
                    {"CidrIp": "0.0.0.0/0"}
                ]
            },
            {
                "IpProtocol": "tcp",
                "FromPort": 5000,
                "ToPort": 5000,
                "IpRanges": [
                    {"CidrIp": "0.0.0.0/0"}
                ]
            },
            {
                "IpProtocol": "tcp",
                "FromPort": 80,
                "ToPort": 80,
                "IpRanges": [
                    {"CidrIp": "0.0.0.0/0"}
                ]
            }
        ]
    )

    print(f"Security group created: {sg_id}")

    return sg_id


# ============================================================
# EC2
# ============================================================

def create_ec2(security_group_id):

    print("Checking EC2 instance...")

    response = ec2.describe_instances(
        Filters=[
            {
                "Name": "tag:Project",
                "Values": [PROJECT_NAME]
            },
            {
                "Name": "instance-state-name",
                "Values": [
                    "pending",
                    "running",
                    "stopping",
                    "stopped"
                ]
            }
        ]
    )

    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:

            print(
                f"EC2 already exists: "
                f"{instance['InstanceId']}"
            )

            return instance["InstanceId"]

    print("Creating EC2 instance...")

    user_data = """#!/bin/bash

apt-get update -y
apt-get install -y docker.io git

systemctl enable docker
systemctl start docker

usermod -aG docker ubuntu
"""

    # IAM can take a few seconds to propagate to EC2.
    for attempt in range(6):

        try:

            response = ec2.run_instances(
                ImageId=AMI_ID,
                InstanceType=INSTANCE_TYPE,
                KeyName=KEY_NAME,
                MinCount=1,
                MaxCount=1,
                SecurityGroupIds=[security_group_id],

                IamInstanceProfile={
                    "Name": INSTANCE_PROFILE_NAME
                },

                UserData=user_data,

                TagSpecifications=[
                    {
                        "ResourceType": "instance",
                        "Tags": [
                            {
                                "Key": "Name",
                                "Value": INSTANCE_NAME
                            },
                            {
                                "Key": "Project",
                                "Value": PROJECT_NAME
                            },
                            {
                                "Key": "ManagedBy",
                                "Value": "Boto3"
                            }
                        ]
                    }
                ]
            )

            instance_id = response["Instances"][0]["InstanceId"]

            print(f"EC2 created: {instance_id}")

            return instance_id

        except ClientError as error:

            if (
                error.response["Error"]["Code"]
                == "InvalidParameterValue"
            ):

                print(
                    "Waiting for IAM instance profile "
                    "to propagate..."
                )

                time.sleep(10)

            else:
                raise

    raise RuntimeError(
        "EC2 creation failed after retries."
    )


# ============================================================
# SETUP
# ============================================================

def setup():

    print("\n==============================")
    print("Starting AWS infrastructure setup")
    print("==============================\n")

    bucket = create_s3_bucket()

    configure_s3_lifecycle(bucket)

    create_iam_role()

    create_instance_profile()

    security_group = create_security_group()

    instance = create_ec2(security_group)

    print("\n==============================")
    print("SETUP COMPLETE")
    print("==============================")

    print(f"S3 Bucket: {bucket}")
    print(f"Security Group: {security_group}")
    print(f"EC2 Instance: {instance}")


# ============================================================
# STATUS
# ============================================================

def status():

    print("\nChecking project resources...\n")

    print("EC2:")

    response = ec2.describe_instances(
        Filters=[
            {
                "Name": "tag:Project",
                "Values": [PROJECT_NAME]
            }
        ]
    )

    found = False

    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:

            found = True

            print(
                f"{instance['InstanceId']} "
                f"- {instance['State']['Name']} "
                f"- {instance.get('PublicIpAddress', 'N/A')}"
            )

    if not found:
        print("Not found")

    print("\nS3 buckets:")

    response = s3.list_buckets()

    for bucket in response["Buckets"]:
        if bucket["Name"] == S3_BUCKET_NAME:
            print(bucket["Name"])

    print("\nIAM role:")

    try:
        iam.get_role(RoleName=IAM_ROLE_NAME)
        print(IAM_ROLE_NAME)

    except iam.exceptions.NoSuchEntityException:
        print("Not found")

# ============================================================
# GET IP
# ============================================================

def get_ec2_ip():

    response = ec2.describe_instances(
        Filters=[
            {
                "Name": "tag:Project",
                "Values": [PROJECT_NAME]
            },
            {
                "Name": "instance-state-name",
                "Values": [
                    "pending",
                    "running"
                ]
            }
        ]
    )

    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:

            ip = instance.get("PublicIpAddress")

            if ip:
                print(ip)
                return

    print("EC2 public IP not found.")
# ============================================================
# DESTROY
# ============================================================

def destroy():

    print("\n==============================")
    print("DESTROYING PROJECT RESOURCES")
    print("==============================\n")

    if input("Type DELETE to continue: ") != "DELETE":
        print("Destroy cancelled.")
        return

    # --------------------------------------------------------
    # EC2
    # --------------------------------------------------------

    response = ec2.describe_instances(
        Filters=[
            {
                "Name": "tag:Project",
                "Values": [PROJECT_NAME]
            },
            {
                "Name": "instance-state-name",
                "Values": [
                    "pending",
                    "running",
                    "stopping",
                    "stopped"
                ]
            }
        ]
    )

    instance_ids = []

    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            instance_ids.append(instance["InstanceId"])

    if instance_ids:

        print(f"Terminating EC2: {instance_ids}")

        ec2.terminate_instances(
            InstanceIds=instance_ids
        )

        ec2.get_waiter(
            "instance_terminated"
        ).wait(
            InstanceIds=instance_ids
        )

        print("EC2 terminated.")

    # --------------------------------------------------------
    # SECURITY GROUP
    # --------------------------------------------------------

    response = ec2.describe_security_groups(
        Filters=[
            {
                "Name": "group-name",
                "Values": [SECURITY_GROUP_NAME]
            }
        ]
    )

    for sg in response["SecurityGroups"]:

        try:

            ec2.delete_security_group(
                GroupId=sg["GroupId"]
            )

            print(
                f"Deleted security group: "
                f"{sg['GroupId']}"
            )

        except ClientError as error:
            print(error)

    # --------------------------------------------------------
    # S3
    # --------------------------------------------------------

    try:

        s3.head_bucket(
            Bucket=S3_BUCKET_NAME
        )

        print(
            f"Deleting S3 bucket: "
            f"{S3_BUCKET_NAME}"
        )

        response = s3.list_objects_v2(
            Bucket=S3_BUCKET_NAME
        )

        for obj in response.get("Contents", []):

            s3.delete_object(
                Bucket=S3_BUCKET_NAME,
                Key=obj["Key"]
            )

        s3.delete_bucket(
            Bucket=S3_BUCKET_NAME
        )

        print("S3 bucket deleted.")

    except ClientError:
        print("S3 bucket not found.")

    # --------------------------------------------------------
    # IAM
    # --------------------------------------------------------

    try:

        iam.remove_role_from_instance_profile(
            InstanceProfileName=INSTANCE_PROFILE_NAME,
            RoleName=IAM_ROLE_NAME
        )

        iam.delete_instance_profile(
            InstanceProfileName=INSTANCE_PROFILE_NAME
        )

        iam.detach_role_policy(
            RoleName=IAM_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess"
        )

        iam.delete_role(
            RoleName=IAM_ROLE_NAME
        )

        print("IAM resources deleted.")

    except iam.exceptions.NoSuchEntityException:

        print("IAM resources not found.")

    print("\n==============================")
    print("DESTROY COMPLETE")
    print("==============================")


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) < 2:

        print("""
Usage:

    python infrastructure.py setup
    python infrastructure.py status
    python infrastructure.py destroy
""")

        sys.exit(1)

    command = sys.argv[1]

    if command == "setup":
        setup()

    elif command == "status":
        status()

    elif command == "ip":
        get_ec2_ip()

    elif command == "destroy":
        destroy()

    else:
        print(f"Unknown command: {command}")