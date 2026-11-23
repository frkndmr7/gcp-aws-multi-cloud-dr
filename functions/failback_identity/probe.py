"""Read-only AWS workload identity probe. No tokens or credentials are logged."""
import os
import re

import boto3
import google.auth.aws
from google.auth.transport.requests import Request
from google.cloud import firestore

def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value or re.search(r"REPLACE|PLACEHOLDER|CHANGEME", value, re.I):
        raise ValueError(f"Missing or invalid configuration: {name}")
    return value


def credential_config() -> dict:
    PROJECT_NUMBER = required_env("MCDR_GCP_PROJECT_NUMBER")
    POOL = required_env("MCDR_WIF_POOL")
    PROVIDER = required_env("MCDR_WIF_PROVIDER")
    SERVICE_ACCOUNT = required_env("MCDR_GCP_SERVICE_ACCOUNT")
    audience = f"//iam.googleapis.com/projects/{PROJECT_NUMBER}/locations/global/workloadIdentityPools/{POOL}/providers/{PROVIDER}"
    return {
        "type": "external_account",
        "audience": audience,
        "subject_token_type": "urn:ietf:params:aws:token-type:aws4_request",
        "token_url": "https://sts.googleapis.com/v1/token",
        "service_account_impersonation_url": f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{SERVICE_ACCOUNT}:generateAccessToken",
        "credential_source": {
            "environment_id": "aws1",
            "region_url": "http://169.254.169.254/latest/meta-data/placement/availability-zone",
            "url": "http://169.254.169.254/latest/meta-data/iam/security-credentials",
            "regional_cred_verification_url": "https://sts.{region}.amazonaws.com?Action=GetCallerIdentity&Version=2011-06-15",
        },
    }


def verify_aws_identity(sts) -> None:
    ACCOUNT = required_env("MCDR_AWS_ACCOUNT_ID")
    ROLE = required_env("MCDR_AWS_ROLE_NAME")
    identity = sts.get_caller_identity()
    expected = rf"arn:aws:sts::{ACCOUNT}:assumed-role/{ROLE}/[^/]+"
    if identity.get("Account") != ACCOUNT or not re.fullmatch(expected, identity.get("Arn", "")):
        raise ValueError("Unexpected AWS workload role")


def run_probe(sts, credential_factory, request, firestore_factory) -> dict:
    verify_aws_identity(sts)
    credentials = credential_factory(credential_config(), scopes=["https://www.googleapis.com/auth/datastore"])
    credentials.refresh(request)
    client = firestore_factory(project=required_env("MCDR_GCP_PROJECT_ID"), database="(default)", credentials=credentials)
    try:
        # Point read only; absence is a successful permissions check.
        snapshot = client.collection("urls").document("testae15c31da77d").get()
        return {"aws_role": "verified", "google_credentials": "refreshed", "firestore_point_read": "ok", "document_exists": snapshot.exists, "document_id": "testae15c31da77d"}
    finally:
        client.close()


def validate_probe_request(event: object) -> None:
    # Caller authorization is enforced by Lambda Invoke IAM, not payload fields.
    if not isinstance(event, dict) or event != {"action": "identity_probe"}:
        raise ValueError("Invalid probe request")


def handler(event, context) -> dict:
    try:
        validate_probe_request(event)
        return run_probe(
            boto3.client("sts", region_name=os.environ.get("AWS_REGION", "eu-west-1")),
            google.auth.aws.Credentials.from_info,
            Request(),
            firestore.Client,
        )
    except Exception:
        # Exceptions from credential libraries can contain sensitive request details.
        raise RuntimeError("Read-only WIF probe failed") from None


def main() -> None:
    print(handler({"action": "identity_probe"}, None))


if __name__ == "__main__":
    main()
