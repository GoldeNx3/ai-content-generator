"""Explicit live contract check; creates a temporary draft then moves it to Trash.
Run in the configured API container: python -m tests.wordpress_bridge_live_check
"""
import asyncio
from uuid import uuid4
from app.core.config import get_settings
from app.services.wordpress.client import WordPressClient
from app.services.wordpress.preparation import wp_content_hash
from app.services.wordpress.errors import WordPressError

async def main():
    client=WordPressClient(get_settings());identity='acceptance:'+str(uuid4());operation=str(uuid4())
    body={'title':'Content Engine Bridge acceptance','slug':'ce-bridge-acceptance-'+str(uuid4())[:8],
          'content':'<h2>Approved test</h2><p>Temporary integration check.</p>','status':'draft'}
    post_id=None
    try:
        first,second=await asyncio.gather(client.create_post(body,identity=identity,operation=operation),client.create_post(body,identity=identity,operation=operation))
        post_id=first['id'];assert second['id']==post_id
        # Simulate the application losing both the response and local checkpoint.
        recovered=await client.create_post(body,identity=identity,operation=str(uuid4()))
        assert recovered['id']==post_id
        original=await client.get_post(post_id);expected=wp_content_hash(original)
        await client.update_post(post_id,{'content':'<p>Manual WordPress edit.</p>'})
        try:
            await client.update_post(post_id,{'content':body['content']},identity=identity,operation=str(uuid4()),expected_hash=expected)
        except WordPressError as exc:assert exc.code=='wordpress_conflict'
        else:raise AssertionError('Manual conflict was not blocked')
        manual=await client.get_post(post_id)
        assert manual['content']['raw']=='<p>Manual WordPress edit.</p>'
        restored=await client.update_post(post_id,{'content':body['content']},identity=identity,operation=str(uuid4()),expected_hash=wp_content_hash(manual))
        assert restored['id']==post_id
        await client.request('DELETE',f'wp/v2/posts/{post_id}',params={'force':'false'})
        trashed_id=post_id
        replacement_operation=str(uuid4())
        replacement=await client.create_post(body,identity=identity,operation=replacement_operation)
        post_id=replacement['id']
        assert post_id!=trashed_id and replacement['status']=='draft'
        assert (await client.get_post(trashed_id))['status']=='trash'
        assert (await client.create_post(body,identity=identity,operation=replacement_operation))['id']==post_id
        # Permanent deletion is restricted to this freshly created temporary test post.
        await client.request('DELETE',f'wp/v2/posts/{post_id}',params={'force':'true'})
        old_id=post_id;post_id=None
        recreate_operation=str(uuid4())
        recreated=await client.create_post(body,identity=identity,operation=recreate_operation)
        post_id=recreated['id'];assert post_id!=old_id
        again=await client.create_post(body,identity=identity,operation=recreate_operation)
        assert again['id']==post_id
        print('PASS: concurrency, recovery, conflict, new draft after trash, permanent deletion recreation + replay; final temporary WP post '+str(post_id))
    finally:
        if post_id:await client.request('DELETE',f'wp/v2/posts/{post_id}',params={'force':'false'})
        await client.close()

if __name__=='__main__':asyncio.run(main())
