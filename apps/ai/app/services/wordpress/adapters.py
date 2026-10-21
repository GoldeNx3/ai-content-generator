"""Interchangeable SEO integrations; the publisher knows no plugin meta names."""
import logging
logger=logging.getLogger(__name__)

class SEOAdapter:
    mapping={}
    def metadata(self, profile, capabilities):
        available=set(capabilities.get('meta_keys',[]));meta={};warnings=[]
        for name,key in self.mapping.items():
            if key not in available:
                warnings.append(f'SEO: REST nie udostępnia pola {name}. Zainstaluj lub zaktualizuj Content Engine Bridge.')
                continue
            value=profile.get(name)
            if name=='robots_index': value=0 if value else 1
            if name=='robots_follow': value=0 if value else 1
            if name=='focus_keyword' and isinstance(value,list):value=','.join(value)
            if value is not None:meta[key]=str(value) if isinstance(value,int) else value
        if 'ce_seo' in available:
            meta['ce_seo']={k:v for k,v in profile.items() if k not in ('title','slug','verified_internal_links','internal_links','featured_image_asset','verified_internal_links')}
        for warning in warnings:logger.warning(warning)
        return meta,warnings
    def verify(self, metadata, post):
        readable=post.get('meta',{})
        warnings=[]
        for key,value in metadata.items():
            if key=='ce_seo' or key not in readable:continue
            actual=readable[key]
            if key in ('_yoast_wpseo_meta-robots-noindex','_yoast_wpseo_meta-robots-nofollow') and str(value)=='0' and actual in ('',None,0):continue
            if str(actual)!=str(value):warnings.append(f'SEO: nie potwierdzono pola {key}.')
        return warnings

class YoastSEOAdapter(SEOAdapter):
    mapping={'seo_title':'_yoast_wpseo_title','meta_description':'_yoast_wpseo_metadesc','canonical_url':'_yoast_wpseo_canonical',
        'og_title':'_yoast_wpseo_opengraph-title','og_description':'_yoast_wpseo_opengraph-description',
        'twitter_title':'_yoast_wpseo_twitter-title','twitter_description':'_yoast_wpseo_twitter-description',
        'robots_index':'_yoast_wpseo_meta-robots-noindex','robots_follow':'_yoast_wpseo_meta-robots-nofollow',
        'focus_keyword':'_yoast_wpseo_focuskw'}

class RankMathSEOAdapter(SEOAdapter):
    mapping={'seo_title':'rank_math_title','meta_description':'rank_math_description','canonical_url':'rank_math_canonical_url',
        'og_title':'rank_math_facebook_title','og_description':'rank_math_facebook_description',
        'twitter_title':'rank_math_twitter_title','twitter_description':'rank_math_twitter_description','focus_keyword':'rank_math_focus_keyword'}
    def metadata(self,profile,capabilities):
        meta,warnings=super().metadata(profile,capabilities)
        if 'rank_math_robots' in capabilities.get('meta_keys',[]):
            meta['rank_math_robots']=['index' if profile['robots_index'] else 'noindex','follow' if profile['robots_follow'] else 'nofollow']
        else:warnings.append('SEO: REST nie udostępnia pola robots.')
        return meta,warnings

class NoSEOAdapter(SEOAdapter):
    def metadata(self,profile,capabilities):
        meta,warnings=super().metadata(profile,capabilities)
        if 'ce_seo' not in capabilities.get('meta_keys',[]):warnings.append('SEO: brak Bridge do renderowania metadanych.')
        return meta,warnings

def adapter_for(plugin):return {'yoast':YoastSEOAdapter,'rankmath':RankMathSEOAdapter,'none':NoSEOAdapter}[plugin]()
