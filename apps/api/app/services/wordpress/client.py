"""WordPress transport. The durable worker owns retries, not this client."""
from urllib.parse import urlsplit
import httpx
from app.services.wordpress.errors import WordPressError

class WordPressClient:
    def __init__(self, settings, http=None):
        self.settings=settings
        self.base=settings.wordpress_url.rstrip('/')
        self.transport_base=(settings.wordpress_api_url or self.base).rstrip('/')
        self.http=http or httpx.AsyncClient(timeout=settings.wordpress_timeout_seconds,follow_redirects=False)
        self.owns_http=http is None
    async def close(self):
        if self.owns_http: await self.http.aclose()
    def configured(self):
        parsed=urlsplit(self.base)
        if parsed.scheme not in ('http','https') or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise WordPressError('wordpress_invalid_url')
        if not self.settings.wordpress_username or not self.settings.wordpress_app_password:
            raise WordPressError('wordpress_not_configured')
    async def request(self, method, path, **kwargs):
        # Public host preserves WP routing/permalinks with Docker's internal transport.
        headers={'Host':urlsplit(self.base).netloc} if self.transport_base!=self.base else {}
        headers.update(kwargs.pop('headers',{}))
        try:
            response=await self.http.request(method,self.transport_base+'/wp-json/'+path,
                auth=(self.settings.wordpress_username,self.settings.wordpress_app_password),headers=headers,**kwargs)
        except (httpx.TimeoutException,httpx.NetworkError) as exc:
            raise WordPressError('wordpress_timeout' if isinstance(exc,httpx.TimeoutException) else 'wordpress_connection',True) from None
        if response.status_code>=300:
            delay=None
            try: delay=float(response.headers.get('Retry-After',''))
            except ValueError: pass
            details=None
            if response.status_code==409:
                try: details=response.json().get('data',{})
                except ValueError: pass
            raise WordPressError(f'wordpress_http_{response.status_code}',response.status_code==429 or response.status_code>=500,delay,details)
        try: return response.json()
        except ValueError: raise WordPressError('wordpress_invalid_json') from None
    async def create_post(self, payload, *, identity=None, operation=None):
        if identity:
            return await self.request('POST','content-engine/v1/posts',json={'identity':identity,'operation':operation,'post':payload})
        return await self.request('POST','wp/v2/posts',json=payload)
    async def update_post(self, post_id, payload, *, identity=None, operation=None, expected_hash=None):
        if identity:
            return await self.request('POST',f'content-engine/v1/posts/{post_id}',json={
                'identity':identity,'operation':operation,'expected_hash':expected_hash,'post':payload})
        return await self.request('POST',f'wp/v2/posts/{post_id}',json=payload)
    async def get_post(self, post_id): return await self.request('GET',f'wp/v2/posts/{post_id}',params={'context':'edit'})
    async def create_category(self, name): return await self.request('POST','wp/v2/categories',json={'name':name})
    async def find_category(self, name): return await self.find_term('categories',name)
    async def create_tag(self, name): return await self.request('POST','wp/v2/tags',json={'name':name})
    async def find_tag(self, name): return await self.find_term('tags',name)
    async def find_term(self, kind, name):
        rows=await self.request('GET',f'wp/v2/{kind}',params={'search':name,'per_page':100})
        return next((row for row in rows if row['name'].casefold()==name.casefold()),None)
    async def upload_media(self, data, filename, mime):
        return await self.request('POST','content-engine/v1/media',content=data,headers={'Content-Type':mime,'Content-Disposition':f'attachment; filename="{filename}"'})
    async def get_user(self, user_id): return await self.request('GET',f'wp/v2/users/{user_id}',params={'context':'edit'})
    async def operation(self, key): return await self.request('GET','content-engine/v1/operation',params={'operation':key})
    async def capabilities(self): return await self.request('GET','content-engine/v1/capabilities')
    async def test_connection(self):
        self.configured()
        user=await self.get_user('me')
        await self.request('GET','wp/v2/posts',params={'context':'edit','per_page':1})
        caps=await self.capabilities()
        return {'ok':True,'url':self.base,'user_id':user['id'],'capabilities':caps}
