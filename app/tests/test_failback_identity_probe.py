import os
from unittest.mock import Mock

import google.auth.aws
import pytest

from functions.failback_identity import probe


def test_external_account_configuration_is_parseable_and_keyless():
    config = probe.credential_config()
    creds = google.auth.aws.Credentials.from_info(config, scopes=["https://www.googleapis.com/auth/datastore"])
    assert creds is not None
    assert config["type"] == "external_account"
    assert "private_key" not in config
    assert "/workloadIdentityPools/mcdr-aws-failback/providers/aws-failback" in config["audience"]


def test_rejects_wrong_aws_role_before_google_credentials():
    sts = Mock()
    sts.get_caller_identity.return_value = {"Account": "123456789012", "Arn": f"arn:aws:sts::{os.environ['MCDR_AWS_ACCOUNT_ID']}:assumed-role/other/session"}
    factory = Mock()
    with pytest.raises(ValueError):
        probe.run_probe(sts, factory, Mock(), Mock())
    factory.assert_not_called()


def test_probe_refreshes_credentials_and_only_reads():
    sts = Mock()
    sts.get_caller_identity.return_value = {"Account": "123456789012", "Arn": f"arn:aws:sts::{os.environ['MCDR_AWS_ACCOUNT_ID']}:assumed-role/{os.environ['MCDR_AWS_ROLE_NAME']}/session"}
    credentials, client, request = Mock(), Mock(), Mock()
    client.collection.return_value.document.return_value.get.return_value.exists = False
    result = probe.run_probe(sts, Mock(return_value=credentials), request, Mock(return_value=client))
    assert result["firestore_point_read"] == "ok"
    credentials.refresh.assert_called_once_with(request)
    client.collection.return_value.document.assert_called_once_with("testae15c31da77d")
    client.collection.return_value.document.return_value.get.assert_called_once_with()
    client.close.assert_called_once_with()
    ref = client.collection.return_value.document.return_value
    ref.create.assert_not_called()
    ref.update.assert_not_called()
    ref.set.assert_not_called()
    ref.delete.assert_not_called()


def test_handler_hides_underlying_credential_error(monkeypatch):
    monkeypatch.setattr(probe.boto3, "client", Mock())
    monkeypatch.setattr(probe, "run_probe", Mock(side_effect=RuntimeError("sensitive details")))
    with pytest.raises(RuntimeError, match="^Read-only WIF probe failed$") as exc:
        probe.handler({"action": "identity_probe"}, None)
    assert exc.value.__cause__ is None


@pytest.mark.parametrize("value", [None, "", "REPLACE_PROJECT"])
def test_identity_config_fails_closed(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("MCDR_GCP_PROJECT_NUMBER", raising=False)
    else:
        monkeypatch.setenv("MCDR_GCP_PROJECT_NUMBER", value)
    with pytest.raises(ValueError):
        probe.credential_config()


@pytest.mark.parametrize("event", [None, {}, [], {"action": "other"},
    {"action": "identity_probe", "Records": []},
    {"action": "identity_probe", "authorized": True},
    {"action": "identity_probe", "document_id": "arbitrary"}])
def test_invalid_manual_probe_rejected_before_credentials(monkeypatch, event):
    factory = Mock()
    monkeypatch.setattr(probe, "run_probe", factory)
    with pytest.raises(RuntimeError, match="Read-only WIF probe failed"):
        probe.handler(event, None)
    factory.assert_not_called()


def test_failback_handler_dispatches_probe_without_processing_streams(monkeypatch):
    from functions.failback_identity import handler as module
    run, process = Mock(return_value={"firestore_point_read": "ok"}), Mock()
    monkeypatch.setattr(probe, "run_probe", run)
    monkeypatch.setattr(module, "process_batch", process)
    monkeypatch.setattr(probe.boto3, "client", Mock())
    assert module.handler({"action": "identity_probe"}, None) == {"firestore_point_read": "ok"}
    run.assert_called_once()
    process.assert_not_called()


@pytest.mark.parametrize("event", [None, {}, {"action": "other"},
    {"action": "identity_probe", "Records": []},
    {"action": "identity_probe", "authorized": True}])
def test_main_handler_rejects_malformed_probe(monkeypatch, event):
    from functions.failback_identity import handler as module
    run, process = Mock(), Mock()
    monkeypatch.setattr(probe, "run_probe", run)
    monkeypatch.setattr(module, "process_batch", process)
    with pytest.raises(RuntimeError, match="Failback batch failed"):
        module.handler(event, None)
    run.assert_not_called()
    process.assert_not_called()


def test_probe_errors_do_not_expose_details(monkeypatch, caplog, capsys):
    from functions.failback_identity import handler as module
    monkeypatch.setattr(probe.boto3, "client", Mock())
    monkeypatch.setattr(probe, "run_probe", Mock(side_effect=ValueError("SENSITIVE_SENTINEL")))
    with pytest.raises(RuntimeError) as exc:
        module.handler({"action": "identity_probe"}, None)
    assert exc.value.__cause__ is None
    assert "SENSITIVE_SENTINEL" not in str(exc.value) + caplog.text + capsys.readouterr().out


def test_stream_event_never_enters_probe(monkeypatch):
    from functions.failback_identity import handler as module
    run, client = Mock(), Mock()
    monkeypatch.setattr(probe, "run_probe", run)
    monkeypatch.setattr(module, "verify_aws_identity", Mock())
    monkeypatch.setattr(module.boto3, "client", Mock())
    monkeypatch.setattr(module.google.auth.aws.Credentials, "from_info", Mock())
    monkeypatch.setattr(module.firestore, "Client", Mock(return_value=client))
    assert module.handler({"Records": []}, None) == {"batchItemFailures": []}
    run.assert_not_called()
    client.close.assert_called_once()
