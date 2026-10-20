# Rola pliku: Trwała lista kandydatów jednej partii, także po utracie odpowiedzi.

import hashlib
from uuid import uuid4, uuid5

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.models.job import Job, JobBatch
from app.repositories.candidate_repository import CandidateRepository
from app.services.jobs.errors import JobConflict, JobInputError
from app.services.usage import ensure_budget


async def enqueue_batch(service, limit, key=None, *, workspace_id):
    session = service.session
    key = key or uuid4()
    # Workspace w hashu: ten sam klucz z innego workspace'u to konflikt, nie odczyt cudzej partii.
    request_hash = hashlib.sha256(f'classify-batch:{workspace_id}:{limit}'.encode()).hexdigest()
    batch = await session.get(JobBatch, key)
    if batch is None:
        # Nowa partia nie powstaje po wyczerpaniu budżetu (pojedyncze enqueue sprawdza go ponownie).
        await ensure_budget(session, workspace_id, service.settings)
        ids = await CandidateRepository(session).list_unclassified_ids(limit, workspace_id=workspace_id)
        # Dwie identyczne prośby mogą nadejść jednocześnie. Tylko jedna lista
        # wygrywa INSERT; druga prośba odczytuje zapisaną listę zwycięzcy.
        await session.execute(insert(JobBatch).values(id=key, workspace_id=workspace_id, request_hash=request_hash,
            candidate_ids=ids, skipped_ids=[]).on_conflict_do_nothing(index_elements=['id']))
        await session.commit()
        batch = await session.get(JobBatch, key, populate_existing=True)
    if batch.request_hash != request_hash or batch.workspace_id != workspace_id:
        raise JobConflict('idempotency_conflict')
    ids = list(batch.candidate_ids)
    result = {'job_ids': [], 'enqueued': 0, 'existing': 0, 'skipped_busy': 0, 'skipped_budget': 0}
    for index, candidate_id in enumerate(ids):
        # Blokada partii obejmuje decyzję enqueue ALBO skip. Nie wystarczy
        # sam odczyt listy: równoległe powtórzenie mogłoby ją już zmienić.
        batch = await session.scalar(select(JobBatch).where(JobBatch.id == key)
                                     .with_for_update().execution_options(populate_existing=True))
        if candidate_id in batch.skipped_ids:
            result['skipped_busy'] += 1
            await session.commit()
            continue
        child_key = uuid5(key, str(candidate_id))
        existed = await session.scalar(select(Job.id).where(Job.idempotency_key == child_key))
        try:
            job = await service.enqueue('classify', candidate_id, key=child_key)
            result['job_ids'].append(job.id)
            result['existing' if existed else 'enqueued'] += 1
        except JobInputError as exc:
            if exc.status_code != 402:
                raise
            # Budżet wyczerpany w trakcie partii: reszta nie trafia do kolejki (ponowienie partii spróbuje znowu).
            await session.rollback()
            result['skipped_budget'] = len(ids) - index
            break
        except JobConflict:
            await session.rollback()
            batch = await session.scalar(select(JobBatch).where(JobBatch.id == key)
                                         .with_for_update().execution_options(populate_existing=True))
            # rollback zwolnił blokadę. Inne żądanie mogło już zapisać
            # dziecko; istniejący job ma pierwszeństwo nad spóźnionym skip.
            child = await session.scalar(select(Job.id).where(Job.idempotency_key == child_key))
            if child:
                result['job_ids'].append(child)
                result['existing'] += 1
            else:
                batch.skipped_ids = sorted(set(batch.skipped_ids) | {candidate_id})
                result['skipped_busy'] += 1
            await session.commit()
    return result
