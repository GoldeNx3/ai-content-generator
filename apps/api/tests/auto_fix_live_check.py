"""Paid opt-in E2E on public SvelteKit evidence, creates test versions and internal approval."""
import asyncio,json,sys,time
import httpx

async def wait_job(client,job_id):
    deadline=time.monotonic()+1800;previous=None
    while time.monotonic()<deadline:
        job=(await client.get(f'/api/jobs/{job_id}')).json();state=(job['status'],job.get('stage'))
        if state!=previous: print('JOB',job_id,*state,flush=True);previous=state
        if job['status']=='succeeded': return job
        if job['status']=='failed': raise RuntimeError(json.dumps(job,ensure_ascii=False))
        await asyncio.sleep(2)
    raise TimeoutError(job_id)

async def main(base_id):
    async with httpx.AsyncClient(base_url='http://localhost:8000',timeout=30) as client:
        response=await client.get(f'/api/articles/{base_id}');response.raise_for_status();base=response.json()
        added='SvelteKit 3 zawiera wbudowany edytor graficzny do projektowania stron.'
        response=await client.patch(f'/api/articles/{base_id}',json={'content':base['content'].rstrip()+'\n\n'+added+'\n'})
        response.raise_for_status();source=response.json();print('SOURCE',source['id'],'version',source['version'],'parent',base_id,flush=True)
        started=time.monotonic();response=await client.post(f"/api/articles/{source['id']}/qa");response.raise_for_status()
        print('QA HTTP',response.status_code,'seconds',round(time.monotonic()-started,3),flush=True);await wait_job(client,response.json()['id'])
        qa=(await client.get(f"/api/articles/{source['id']}/qa")).json();print('SOURCE_QA',json.dumps(qa,ensure_ascii=False),flush=True)
        assert not qa['qa_passed'] and any(added in i['excerpt'] or i['excerpt'] in added for i in qa['issues'])
        started=time.monotonic();response=await client.post(f"/api/article-versions/{source['id']}/auto-fix");response.raise_for_status()
        print('FIX HTTP',response.status_code,'seconds',round(time.monotonic()-started,3),flush=True);job=await wait_job(client,response.json()['id'])
        fix=(await client.get(f"/api/article-fixes/{job['result_id']}")).json();print('FIX',json.dumps(fix,ensure_ascii=False),flush=True)
        result_id=fix['result_article_version_id'];assert result_id is not None
        qa=(await client.get(f'/api/articles/{result_id}/qa')).json();await wait_job(client,qa['job_id'])
        qa=(await client.get(f'/api/articles/{result_id}/qa')).json();print('RESULT_QA',json.dumps(qa,ensure_ascii=False),flush=True);assert qa['qa_passed']
        result=(await client.get(f'/api/articles/{result_id}')).json();old=(await client.get(f"/api/articles/{source['id']}")).json()
        assert old['content']==source['content'] and old['content_hash']==source['content_hash']
        assert result['parent_version_id']==source['id'] and result['status']=='ready_for_approval' and added not in result['content']
        response=await client.post(f'/api/article-versions/{result_id}/approve');response.raise_for_status();approved=response.json()
        assert approved['status']=='approved' and approved['approved_at']
        print('APPROVED',result_id,'version',approved['version'],'QA',qa['overall_score'],'fix_cost',fix['estimated_cost_usd'],'qa_cost',qa['estimated_cost_usd'],flush=True)
        print('NO_NEW_FACTS_REVIEW',json.dumps(fix['changes'],ensure_ascii=False),flush=True)

if __name__=='__main__': asyncio.run(main(int(sys.argv[1])))
