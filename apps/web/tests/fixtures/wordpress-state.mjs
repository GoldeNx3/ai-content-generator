export function wordpressState(qaOk = false) {
  return {
    remote_status: null, publication: null, qa_ok: qaOk, categories: ['Technologia'],
    checks: [], conflict: null, newer_approved_version_id: null, wordpress_admin_url: null,
    profile: {
      title: 'Artykuł testowy', slug: 'artykul-testowy', seo_title: 'Artykuł testowy',
      meta_description: 'Opis artykułu', excerpt: 'Zajawka', canonical_url: null,
      focus_keyword: 'technologia', secondary_keywords: [], og_title: '', og_description: '',
      twitter_title: '', twitter_description: '', robots_index: true, robots_follow: true,
      schema_type: 'Article', category: 'Technologia', tags: [], author_id: null,
      featured_image_url: null, featured_image_asset: null,
    },
  };
}
