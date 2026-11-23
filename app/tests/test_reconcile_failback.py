import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

from google.api_core.exceptions import Conflict
from scripts import reconcile_failback as r


def item(id='one', origin='aws'):
    return {'id': id, 'original_url': 'https://example.com/', 'origin_cloud': origin,
            'version': 1, 'created_at': '2026-01-01T00:00:00Z'}


def snapshot(value=None):
    x=Mock(); x.exists=value is not None; x.to_dict.return_value=value; return x


def test_pagination_missing_matched_conflict_and_gcp_skip():
    table=Mock(); table.scan.side_effect=[{'Items':[item('one'),item('two')], 'LastEvaluatedKey':{'id':'two'}},
                                           {'Items':[item('three'),item('four','gcp')]}]
    collection=Mock(); refs={key: Mock() for key in ('one','two','three')}
    collection.document.side_effect=lambda key: refs[key]
    refs['one'].get.return_value=snapshot()
    same=item('two'); same['created_at']=datetime(2026,1,1,tzinfo=timezone.utc)
    refs['two'].get.return_value=snapshot(same)
    different=item('three'); different['original_url']='https://different.example/'
    refs['three'].get.return_value=snapshot(different)
    result=r.reconcile(table,collection,page_size=2)
    assert result['ids']['missing']==['one'] and result['ids']['matched']==['two']
    assert result['ids']['conflict']==['three'] and result['gcp_skipped']==1
    assert result['status']=='error' and result['scanned']==4
    assert table.scan.call_args_list[1].kwargs['ExclusiveStartKey']=={'id':'two'}
    for ref in refs.values(): ref.create.assert_not_called()


def test_invalid_origin_and_read_error_are_not_success():
    table=Mock(); table.scan.return_value={'Items':[item('bad','azure'), {'id':'missing'}]}
    result=r.reconcile(table,Mock()); assert result['counts']['error']==2 and result['status']=='error'
    table.scan.side_effect=RuntimeError('secret'); result=r.reconcile(table,Mock())
    assert result['status']=='error' and not result['complete'] and 'secret' not in str(result)


def test_apply_single_create_and_repeat_match():
    table=Mock(); table.get_item.return_value={'Item':item()}; collection=Mock(); ref=collection.document.return_value
    ref.get.return_value=snapshot(); result=r.reconcile(table,collection,item_id='one',apply=True)
    assert result['ids']['created']==['one']; ref.create.assert_called_once()
    ref.reset_mock(); ref.get.return_value=snapshot(item())
    result=r.reconcile(table,collection,item_id='one',apply=True)
    assert result['ids']['matched']==['one']; ref.create.assert_not_called()


def test_create_race_matching_and_conflict():
    table=Mock(); table.get_item.return_value={'Item':item()}; collection=Mock(); ref=collection.document.return_value
    ref.create.side_effect=Conflict('exists')
    ref.get.side_effect=[snapshot(),snapshot(item())]
    assert r.reconcile(table,collection,item_id='one',apply=True)['ids']['matched']==['one']
    different=item(); different['original_url']='https://different.example/'
    ref.get.side_effect=[snapshot(),snapshot(different)]
    assert r.reconcile(table,collection,item_id='one',apply=True)['ids']['conflict']==['one']


def test_firestore_error_and_scan_limit():
    table=Mock(); table.get_item.return_value={'Item':item()}; collection=Mock(); collection.document.side_effect=RuntimeError('credentials')
    result=r.reconcile(table,collection,item_id='one'); assert result['status']=='error' and result['ids']['error']==['one']
    table.scan.return_value={'Items':[item('one','gcp')], 'LastEvaluatedKey':{'id':'one'}}
    assert not r.reconcile(table,collection,max_items=1)['complete']


def test_cli_rejects_unscoped_apply_and_nonzero_errors(monkeypatch):
    import pytest
    with pytest.raises(SystemExit) as exc: r.main(['--apply'])
    assert exc.value.code==2
    session=Mock(); session.client.return_value.get_caller_identity.return_value={'Account':"123456789012"}
    session.resource.return_value.Table.return_value.get_item.return_value={}
    monkeypatch.setattr(r.boto3,'Session',lambda **kw:session)
    monkeypatch.setattr(r.firestore,'Client',lambda **kw:MagicMock())
    assert r.main(['--id','unknown'])==1


def test_gcp_skip_requires_valid_data():
    table=Mock(); table.scan.return_value={'Items':[item('valid','gcp'), {**item('bad','gcp'),'version':2}]}
    collection=Mock(); result=r.reconcile(table,collection)
    assert result['gcp_skipped']==1 and result['ids']['error']==['bad']
    collection.document.assert_not_called()


def test_apply_firestore_create_permission_denied_is_an_error():
    table=Mock(); table.get_item.return_value={'Item':item()}; collection=Mock(); ref=collection.document.return_value
    ref.get.return_value=snapshot()
    ref.create.side_effect=PermissionError('sensitive credential detail')
    result=r.reconcile(table,collection,item_id='one',apply=True)
    assert result['status']=='error' and result['ids']['error']==['one']
    assert 'sensitive' not in str(result)


def test_missing_configuration_rejected_before_clients(monkeypatch):
    monkeypatch.delenv("MCDR_AWS_ACCOUNT_ID", raising=False)
    with pytest.raises(SystemExit) as exc:
        r.main(["--id", "sample"])
    assert exc.value.code == 2


def test_placeholder_configuration_rejected(monkeypatch):
    monkeypatch.setenv("MCDR_GCP_PROJECT_ID", "REPLACE_PROJECT")
    with pytest.raises(SystemExit) as exc:
        r.main([])
    assert exc.value.code == 2
