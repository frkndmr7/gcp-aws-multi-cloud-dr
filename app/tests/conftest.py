

import pytest

@pytest.fixture(autouse=True)
def failback_test_configuration(monkeypatch):
    values = {
        "MCDR_AWS_ACCOUNT_ID": "123456789012",
        "MCDR_AWS_ROLE_NAME": "mcdr-gcp-aws-failback-lambda",
        "MCDR_GCP_PROJECT_ID": "unit-test-project",
        "MCDR_GCP_PROJECT_NUMBER": "123456789012",
        "MCDR_WIF_POOL": "mcdr-aws-failback",
        "MCDR_WIF_PROVIDER": "aws-failback",
        "MCDR_GCP_SERVICE_ACCOUNT": "failback@unit-test-project.iam.gserviceaccount.com",
        "MCDR_AWS_REGION": "eu-west-1",
        "MCDR_TABLE_NAME": "unit-test-urls",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
