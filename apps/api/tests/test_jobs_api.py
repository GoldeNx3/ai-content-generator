# Rola pliku: HTTP kolejki, idempotency i odczyt po zakończeniu requestu.

from uuid import uuid4
from app.models import Candidate
from tests.test_classification import FakeProvider


async def test_jobs_api_returns_safe_status_and_history(client, session, source, execute_job):
    candidate = Candidate(source_id=source.id, external_url='https://example.com/api-job', title='Test')
    session.add(candidate)
    await session.commit()
    path = f'/api/candidates/{candidate.id}/classify'
    headers = {'Idempotency-Key': str(uuid4())}
    first = await client.post(path, headers=headers)
    assert first.status_code == 202
    job_id = first.json()['id']
    assert first.headers['location'] == f'/api/jobs/{job_id}'
    assert (await client.post(path, headers=headers)).json()['id'] == job_id
    assert (await client.post(path, headers={'Idempotency-Key': str(uuid4())})).status_code == 409
    state = (await client.get(f'/api/jobs/{job_id}')).json()
    assert not {'payload', 'lease_token', 'checkpoints', 'worker_id'} & state.keys()
    assert (await client.get(f'/api/candidates/{candidate.id}/jobs?status=active')).json()['total'] == 1
    assert (await client.delete(f'/api/sources/{source.id}')).status_code == 409
    assert (await client.post(f'/api/candidates/{candidate.id}/research/sources', json={'url':'https://example.com/manual'})).status_code == 409
    await execute_job({'classify': FakeProvider()})
    state = (await client.get(f'/api/jobs/{job_id}')).json()
    assert state['status'] == 'succeeded'
    assert state['result'] == {'type': 'candidate', 'id': candidate.id}
    assert (await client.get(f'/api/jobs/{job_id}/attempts')).json()[0]['outcome'] == 'succeeded'
    assert (await client.get(f'/api/candidates/{candidate.id}/jobs?status=active')).json()['total'] == 0
    assert (await client.post(f'/api/jobs/{job_id}/retry')).status_code == 409
    assert (await client.get(f'/api/jobs/{uuid4()}')).status_code == 404
    # Ta sama akcja także po sukcesie nie nalicza kolejnej generacji.
    assert (await client.post(path, headers=headers)).json()['id'] == job_id


async def test_request_hash_rejects_changed_options(client, session, source):
    candidate = Candidate(source_id=source.id, external_url='https://example.com/hash', title='Test')
    session.add(candidate)
    await session.commit()
    key = {'Idempotency-Key': str(uuid4())}
    path = f'/api/candidates/{candidate.id}/research'
    assert (await client.post(path, headers=key)).status_code == 202
    conflict = await client.post(path+'/retry', headers=key)
    assert conflict.status_code == 409
    assert conflict.json()['detail']['code'] == 'idempotency_conflict'


async def test_batch_key_is_bound_to_limit(client, session, source):
    candidate = Candidate(source_id=source.id, external_url='https://example.com/batch', title='Batch')
    session.add(candidate)
    await session.commit()
    key = {'Idempotency-Key': str(uuid4())}
    first = await client.post('/api/candidates/classify-pending?limit=1', headers=key)
    assert first.status_code == 202
    replay = await client.post('/api/candidates/classify-pending?limit=1', headers=key)
    assert replay.json()['job_ids'] == first.json()['job_ids']
    conflict = await client.post('/api/candidates/classify-pending?limit=2', headers=key)
    assert conflict.status_code == 409
    assert conflict.json()['detail']['code'] == 'idempotency_conflict'
    assert (await client.get('/api/jobs?status=active')).json()['total'] == 1


async def test_global_queue_filters_history_and_counts(client, session, source, execute_job):
    first = Candidate(source_id=source.id, external_url='https://example.com/global-one', title='Pierwszy temat')
    second = Candidate(source_id=source.id, external_url='https://example.com/global-two', title='Drugi temat')
    session.add_all([first, second])
    await session.commit()
    succeeded = (await client.post(f'/api/candidates/{first.id}/classify')).json()
    await execute_job({'classify': FakeProvider()})
    queued = (await client.post(f'/api/candidates/{second.id}/research')).json()
    stats = await client.get('/api/jobs/stats')
    assert stats.status_code == 200
    assert stats.json() == {'queued': 1, 'running': 0, 'retrying': 0, 'succeeded': 1, 'failed': 0, 'total': 2}
    history = await client.get('/api/jobs?status=all&page_size=1')
    assert history.status_code == 200
    assert history.json()['total'] == 2
    assert history.json()['items'][0]['candidate_title'] == 'Drugi temat'
    assert history.json()['items'][0]['id'] == queued['id']
    completed = (await client.get('/api/jobs?status=succeeded&kind=classify')).json()
    assert [job['id'] for job in completed['items']] == [succeeded['id']]
    assert not {'payload', 'lease_token', 'checkpoints'} & completed['items'][0].keys()
    assert (await client.get(f'/api/jobs?status=all&candidate_id={first.id}')).json()['total'] == 1
    assert (await client.get('/api/jobs?status=all&kind=write')).json()['total'] == 0
    assert (await client.get('/api/jobs?status=bogus')).status_code == 422
    assert (await client.get('/api/jobs?kind=bogus')).status_code == 422
