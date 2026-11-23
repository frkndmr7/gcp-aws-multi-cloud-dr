import json
import hashlib
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from google.events.cloud import firestore
from functions.gcp_publisher import main
from functions.aws_replication.consumer import validate_message


def sample(origin="gcp"):
    doc = firestore.DocumentEventData()
    doc.value.name = 'projects/project-1/databases/(default)/documents/urls/abc123'
    doc.value._pb.fields['id'].string_value = 'abc123'
    doc.value._pb.fields['original_url'].string_value = 'https://example.com/'
    doc.value._pb.fields['origin_cloud'].string_value = origin
    doc.value._pb.fields['version'].integer_value = 1
    doc.value._pb.fields['created_at'].timestamp_value.FromDatetime(datetime(2026, 1, 1, tzinfo=timezone.utc))
    return doc._pb.SerializeToString()


def headers():
    return {'ce-id':'id-1', 'ce-source':'source-1', 'ce-type':main.EVENT_TYPE}


def test_protobuf_to_consumer_and_stable_id():
    result = main.transform(headers(), sample(), 'project-1')
    assert result == main.transform(headers(), sample(), 'project-1')
    assert validate_message(json.dumps(result)) == result['record']


def test_wrong_event_and_path_fail():
    with pytest.raises(ValueError):
        main.transform({**headers(), 'ce-type':'updated'}, sample(), 'project-1')
    with pytest.raises(ValueError):
        main.transform(headers(), sample(), 'other-project')


def test_federation_uses_short_lived_credentials(monkeypatch):
    clients = []
    sts = Mock()
    sts.assume_role_with_web_identity.return_value = {'Credentials': {'AccessKeyId':'a', 'SecretAccessKey':'b', 'SessionToken':'c'}}
    sqs = Mock()
    def client(name, **kwargs):
        clients.append((name, kwargs))
        return sts if name == 'sts' else sqs
    monkeypatch.setattr(main.google.oauth2.id_token, 'fetch_id_token', lambda request, audience: 'mock-token')
    monkeypatch.setattr(main.boto3, 'client', client)
    assert main.make_sqs_client('arn:test', 'sts.amazonaws.com', 'eu-west-1') is sqs
    assert sts.assume_role_with_web_identity.call_args.kwargs['WebIdentityToken'] == 'mock-token'
    assert clients[1][1]['aws_session_token'] == 'c'


def test_fail_closed_and_send_failure(monkeypatch):
    client = TestClient(main.app)
    monkeypatch.delenv('PUBLISHER_ENABLED', raising=False)
    assert client.post('/', content=sample(), headers=headers()).status_code == 503
    monkeypatch.setenv('PUBLISHER_ENABLED', 'true')
    for k,v in {'GCP_PROJECT_ID':'project-1','AWS_ROLE_ARN':'arn:test','AWS_TOKEN_AUDIENCE':'sts.amazonaws.com','AWS_REGION':'eu-west-1','SQS_QUEUE_URL':'test'}.items():
        monkeypatch.setenv(k,v)
    fake = Mock()
    fake.send_message.side_effect = RuntimeError('temporary')
    monkeypatch.setattr(main, 'make_sqs_client', lambda *args: fake)
    assert client.post('/', content=sample(), headers={**headers(), 'content-type':'application/protobuf'}).status_code == 503
    fake.send_message.side_effect = None
    assert client.post('/', content=sample(), headers={**headers(), 'content-type':'application/protobuf'}).status_code == 200
    assert fake.send_message.call_count == 2


def test_federation_failure_prevents_send(monkeypatch):
    monkeypatch.setenv('PUBLISHER_ENABLED', 'true')
    for k,v in {'GCP_PROJECT_ID':'project-1','AWS_ROLE_ARN':'arn:test','AWS_TOKEN_AUDIENCE':'sts.amazonaws.com','AWS_REGION':'eu-west-1','SQS_QUEUE_URL':'test'}.items():
        monkeypatch.setenv(k,v)
    send = Mock()
    monkeypatch.setattr(main, 'publish', send)
    def failed(*args):
        raise RuntimeError('STS unavailable')
    monkeypatch.setattr(main, 'make_sqs_client', failed)
    response = TestClient(main.app).post('/', content=sample(), headers={**headers(), 'content-type':'application/protobuf'})
    assert response.status_code == 503
    send.assert_not_called()


def test_aws_events_are_acknowledged_without_federation_or_sqs(monkeypatch):
    monkeypatch.setenv("PUBLISHER_ENABLED", "true")
    monkeypatch.setenv("GCP_PROJECT_ID", "project-1")
    federation, send = Mock(), Mock()
    monkeypatch.setattr(main, "make_sqs_client", federation)
    monkeypatch.setattr(main, "publish", send)
    event_headers = {**headers(), "ce-source": "//firestore.googleapis.com/projects/project-1/databases/(default)", "content-type": "application/protobuf"}
    client = TestClient(main.app)
    for _ in range(2):
        response = client.post("/", content=sample("aws"), headers=event_headers)
        assert response.status_code == 200
        assert response.json() == {"status": "ignored"}
    federation.assert_not_called()
    send.assert_not_called()


@pytest.mark.parametrize("origin", ["", "azure", "AWS"])
def test_invalid_origin_fails_closed(monkeypatch, origin):
    monkeypatch.setenv("PUBLISHER_ENABLED", "true")
    monkeypatch.setenv("GCP_PROJECT_ID", "project-1")
    federation = Mock()
    monkeypatch.setattr(main, "make_sqs_client", federation)
    response = TestClient(main.app).post("/", content=sample(origin), headers={**headers(), "content-type": "application/protobuf"})
    assert response.status_code == 503
    federation.assert_not_called()


def test_aws_event_rejects_invalid_source_and_malformed_record(monkeypatch):
    monkeypatch.setenv("PUBLISHER_ENABLED", "true")
    monkeypatch.setenv("GCP_PROJECT_ID", "project-1")
    federation = Mock()
    monkeypatch.setattr(main, "make_sqs_client", federation)
    client = TestClient(main.app)
    h = {**headers(), "ce-source": "//firestore.googleapis.com/projects/project-1/databases/(default)", "content-type": "application/protobuf"}
    assert client.post("/", content=sample("aws"), headers={**h, "ce-source": "unexpected"}).status_code == 503
    assert client.post("/", content=b"\xff", headers=h).status_code == 503
    doc = firestore.DocumentEventData()
    doc._pb.ParseFromString(sample("aws"))
    del doc.value._pb.fields["original_url"]
    assert client.post("/", content=doc._pb.SerializeToString(), headers=h).status_code == 503
    doc._pb.ParseFromString(sample("aws"))
    doc.value._pb.fields["original_url"].string_value = "not-a-url"
    assert client.post("/", content=doc._pb.SerializeToString(), headers=h).status_code == 503
    doc._pb.ParseFromString(sample("aws"))
    del doc.value._pb.fields["created_at"]
    assert client.post("/", content=doc._pb.SerializeToString(), headers=h).status_code == 503
    federation.assert_not_called()


def test_structured_success_logs_and_no_sensitive_fields(monkeypatch, capsys):
    monkeypatch.setenv("PUBLISHER_ENABLED", "true")
    for key, value in {"GCP_PROJECT_ID": "project-1", "AWS_ROLE_ARN": "arn:test", "AWS_TOKEN_AUDIENCE": "sts.amazonaws.com", "AWS_REGION": "eu-west-1", "SQS_QUEUE_URL": "test"}.items():
        monkeypatch.setenv(key, value)
    federation, send = Mock(), Mock()
    monkeypatch.setattr(main, "make_sqs_client", federation)
    monkeypatch.setattr(main, "publish", send)
    h = {**headers(), "ce-source": "//firestore.googleapis.com/projects/project-1/databases/(default)", "content-type": "application/protobuf"}
    client = TestClient(main.app)
    assert client.post("/", content=sample("aws"), headers=h).status_code == 200
    assert json.loads(capsys.readouterr().out) == {"severity": "INFO", "action": "skip_replication", "document_id": "abc123", "origin_cloud": "aws", "cloud_event_id_sha256": hashlib.sha256(b"id-1").hexdigest()}
    federation.assert_not_called()
    send.assert_not_called()
    assert client.post("/", content=sample("gcp"), headers=h).status_code == 200
    assert json.loads(capsys.readouterr().out) == {"severity": "INFO", "action": "sent_to_sqs", "document_id": "abc123", "origin_cloud": "gcp", "cloud_event_id_sha256": hashlib.sha256(b"id-1").hexdigest()}
    send.assert_called_once()
    send.side_effect = RuntimeError("failure")
    assert client.post("/", content=sample("gcp"), headers=h).status_code == 503
    assert capsys.readouterr().out == ""
    assert client.post("/", content=sample("azure"), headers=h).status_code == 503
    assert capsys.readouterr().out == ""


def test_logging_failure_does_not_retry_successful_send(monkeypatch):
    monkeypatch.setenv('PUBLISHER_ENABLED', 'true')
    for key, value in {'GCP_PROJECT_ID':'project-1','AWS_ROLE_ARN':'arn:test','AWS_TOKEN_AUDIENCE':'sts.amazonaws.com','AWS_REGION':'eu-west-1','SQS_QUEUE_URL':'test'}.items():
        monkeypatch.setenv(key, value)
    send = Mock()
    monkeypatch.setattr(main, 'make_sqs_client', Mock())
    monkeypatch.setattr(main, 'publish', send)
    monkeypatch.setattr(main, 'print', Mock(side_effect=OSError('log unavailable')), raising=False)
    response = TestClient(main.app).post('/', content=sample(), headers={**headers(), 'content-type':'application/protobuf'})
    assert response.status_code == 200
    send.assert_called_once()
