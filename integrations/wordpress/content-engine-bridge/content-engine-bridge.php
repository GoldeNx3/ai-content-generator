<?php
/**
 * Plugin Name: Content Engine Bridge
 * Description: Approved content integration, REST SEO fields and durable idempotency.
 * Version: 1.0.0
 */
if (!defined('ABSPATH')) { exit; }

function ce_bridge_tables() {
    global $wpdb;
    require_once ABSPATH . 'wp-admin/includes/upgrade.php';
    $charset = $wpdb->get_charset_collate();
    dbDelta("CREATE TABLE {$wpdb->prefix}ce_publications (
        identity varchar(191) NOT NULL,
        post_id bigint(20) unsigned NOT NULL,
        PRIMARY KEY (identity),
        UNIQUE KEY post_id (post_id)
    ) ENGINE=InnoDB $charset;");
    dbDelta("CREATE TABLE {$wpdb->prefix}ce_operations (
        operation varchar(191) NOT NULL,
        identity varchar(191) NOT NULL,
        payload_hash char(64) NOT NULL,
        post_id bigint(20) unsigned NOT NULL,
        PRIMARY KEY (operation)
    ) ENGINE=InnoDB $charset;");
}
register_activation_hook(__FILE__, 'ce_bridge_tables');

function ce_bridge_plugin() {
    if (defined('WPSEO_VERSION')) { return 'yoast'; }
    if (defined('RANK_MATH_VERSION')) { return 'rankmath'; }
    return 'none';
}
function ce_bridge_meta_keys() {
    $keys = ['ce_seo'];
    if (ce_bridge_plugin() === 'yoast') {
        $keys = array_merge($keys, ['_yoast_wpseo_title', '_yoast_wpseo_metadesc', '_yoast_wpseo_canonical',
            '_yoast_wpseo_opengraph-title', '_yoast_wpseo_opengraph-description', '_yoast_wpseo_twitter-title',
            '_yoast_wpseo_twitter-description', '_yoast_wpseo_meta-robots-noindex', '_yoast_wpseo_meta-robots-nofollow', '_yoast_wpseo_focuskw']);
    } elseif (ce_bridge_plugin() === 'rankmath') {
        $keys = array_merge($keys, ['rank_math_title','rank_math_description','rank_math_canonical_url',
            'rank_math_facebook_title','rank_math_facebook_description','rank_math_twitter_title',
            'rank_math_twitter_description','rank_math_focus_keyword','rank_math_robots']);
    }
    return $keys;
}
function ce_bridge_allowed() { return current_user_can('edit_posts'); }
function ce_bridge_auth_meta($allowed, $key, $post_id) {
    return $post_id ? current_user_can('edit_post', $post_id) : current_user_can('edit_posts');
}
function ce_bridge_schema() {
    $properties=[];
    foreach (['seo_title','meta_description','canonical_url','og_title','og_description','twitter_title','twitter_description','focus_keyword','schema_type','excerpt','category','featured_image_url'] as $key) {
        $properties[$key]=['type'=>['string','null']];
    }
    foreach (['robots_index','robots_follow','include_sources','category_override'] as $key) { $properties[$key]=['type'=>'boolean']; }
    foreach (['tags','secondary_keywords'] as $key) { $properties[$key]=['type'=>'array','items'=>['type'=>'string']]; }
    foreach (['faq','howto_steps'] as $key) { $properties[$key]=['type'=>'array','items'=>['type'=>'object','additionalProperties'=>['type'=>'string']]]; }
    $properties['author_id']=['type'=>['integer','null']];
    $properties['version_id']=['type'=>'integer'];
    return ['type'=>'object','properties'=>$properties,'additionalProperties'=>false];
}
add_action('init', function () {
    foreach (ce_bridge_meta_keys() as $key) {
        $type=$key==='ce_seo' ? 'object' : ($key==='rank_math_robots' ? 'array' : 'string');
        $rest=true;
        if ($type==='object') { $rest=['schema'=>ce_bridge_schema()]; }
        if ($type==='array') { $rest=['schema'=>['type'=>'array','items'=>['type'=>'string']]]; }
        register_post_meta('post', $key, ['single'=>true,'type'=>$type,'show_in_rest'=>$rest,
            'auth_callback'=>'ce_bridge_auth_meta', 'sanitize_callback'=>$type==='string' ? 'sanitize_text_field' : null]);
    }
});
function ce_bridge_permalink($post) {
    if ($post->post_status==='draft' || $post->post_status==='pending' || $post->post_status==='auto-draft') {
        require_once ABSPATH . 'wp-admin/includes/post.php';
        [$url,$slug]=get_sample_permalink($post->ID,$post->post_title,$post->post_name);
        return str_replace(['%postname%','%pagename%'], $slug, $url);
    }
    return get_permalink($post);
}
add_filter('rest_prepare_post', function ($response,$post) {
    if (current_user_can('edit_post',$post->ID)) { $response->data['ce_permalink']=ce_bridge_permalink($post); }
    return $response;
},10,2);
function ce_bridge_read($id) {
    clean_post_cache($id);
    $request=new WP_REST_Request('GET', '/wp/v2/posts/' . $id);
    $request->set_param('context','edit');
    return rest_do_request($request);
}
function ce_bridge_hash($post) {
    return hash('sha256',str_replace(["\r\n","\r"],"\n",$post->post_content));
}
function ce_bridge_mutate($request) {
    global $wpdb;
    $identity=(string)$request->get_param('identity');
    $operation=(string)$request->get_param('operation');
    $payload=$request->get_param('post');
    $requested_id=(int)$request->get_param('id');
    if (!$identity || strlen($identity)>191 || !$operation || strlen($operation)>191 || !is_array($payload)) {
        return new WP_Error('ce_invalid_request','Identity, operation and post are required.',['status'=>400]);
    }
    // A durable mapping and core posts must participate in the same atomic transaction.
    foreach ([$wpdb->posts,$wpdb->postmeta,$wpdb->prefix.'ce_publications',$wpdb->prefix.'ce_operations'] as $table) {
        $engine=$wpdb->get_var($wpdb->prepare('SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s',$table));
        if (strtoupper((string)$engine)!=='INNODB') { return new WP_Error('ce_storage_not_atomic','InnoDB storage is required.',['status'=>503]); }
    }
    $lock='ce_'.substr(hash('sha256',$identity),0,50);
    if ((int)$wpdb->get_var($wpdb->prepare('SELECT GET_LOCK(%s,5)',$lock))!==1) {
        return new WP_Error('ce_busy','Publication is busy.',['status'=>429]);
    }
    $hash=hash('sha256',wp_json_encode($payload));
    $touched=0;
    $wpdb->query('START TRANSACTION');
    try {
        $done=$wpdb->get_row($wpdb->prepare("SELECT * FROM {$wpdb->prefix}ce_operations WHERE operation=%s FOR UPDATE",$operation));
        if ($done) {
            if ($done->identity!==$identity || $done->payload_hash!==$hash) {
                throw new Exception('idempotency_conflict');
            }
            if (!current_user_can('edit_post',$done->post_id)) { throw new Exception('forbidden'); }
            $wpdb->query('COMMIT');
            return ce_bridge_read($done->post_id);
        }
        $mapped=(int)$wpdb->get_var($wpdb->prepare("SELECT post_id FROM {$wpdb->prefix}ce_publications WHERE identity=%s FOR UPDATE",$identity));
        if ($mapped && !get_post($mapped)) {
            if ($requested_id) { throw new Exception('missing'); }
            $wpdb->delete($wpdb->prefix.'ce_operations',['identity'=>$identity]);
            $wpdb->delete($wpdb->prefix.'ce_publications',['identity'=>$identity]);
            $mapped=0;
        }
        if ($requested_id && $mapped!==$requested_id) { throw new Exception('identity_conflict'); }
        $id=$mapped ?: $requested_id;
        if ($id) {
            // Core REST/wp-admin writes must wait for this row lock as well.
            $locked=$wpdb->get_row($wpdb->prepare("SELECT * FROM {$wpdb->posts} WHERE ID=%d FOR UPDATE",$id));
            clean_post_cache($id);
            $post=$locked ? new WP_Post($locked) : null;
            if (!$post) { throw new Exception('missing'); }
            if ($post->post_status==='trash' && ($payload['status'] ?? '')!=='draft') { throw new Exception('missing'); }
            if (!current_user_can('edit_post',$id)) { throw new Exception('forbidden'); }
            $expected=$request->get_param('expected_hash');
            // A new operation may recover a create whose local DB checkpoint was lost.
            // Recover the mapping without overwriting manually changed content.
            if (!$requested_id && !$expected && isset($payload['content'])) {
                $expected=hash('sha256',str_replace(["\r\n","\r"],"\n",$payload['content']));
                if (hash_equals(ce_bridge_hash($post),$expected)) {
                    if (!$wpdb->insert($wpdb->prefix.'ce_operations',['operation'=>$operation,'identity'=>$identity,'payload_hash'=>$hash,'post_id'=>$id])) { throw new Exception('database_write'); }
                    $wpdb->query('COMMIT');return ce_bridge_read($id);
                }
            }
            if (!$expected) { throw new Exception('expected_hash_required'); }
            if (!hash_equals(ce_bridge_hash($post),$expected)) {
                $wpdb->query('ROLLBACK');
                return new WP_Error('ce_content_conflict','WordPress content changed.',['status'=>409,'current_hash'=>ce_bridge_hash($post),'post_id'=>$id]);
            }
        } elseif (($payload['status'] ?? 'draft')!=='draft') { throw new Exception('draft_required'); }
        if ($id && $post->post_status==='trash') {
            if (!wp_untrash_post($id)) { throw new Exception('restore_failed'); }
        }
        // Delegate field validation, permissions and saving to the native WP REST controller.
        $native=new WP_REST_Request('POST',$id ? '/wp/v2/posts/'.$id : '/wp/v2/posts');
        foreach ($payload as $key=>$value) { $native->set_param($key,$value); }
        $response=rest_do_request($native);
        if ($response->get_status()>=400) { $wpdb->query('ROLLBACK'); if ($id) { clean_post_cache($id); } return $response; }
        $touched=(int)$response->get_data()['id'];
        if (!$mapped && !$wpdb->insert($wpdb->prefix.'ce_publications',['identity'=>$identity,'post_id'=>$touched])) { throw new Exception('database_write'); }
        if (!$wpdb->insert($wpdb->prefix.'ce_operations',['operation'=>$operation,'identity'=>$identity,'payload_hash'=>$hash,'post_id'=>$touched])) { throw new Exception('database_write'); }
        if ($wpdb->query('COMMIT')===false) { throw new Exception('database_write'); }
        return ce_bridge_read($touched);
    } catch (Throwable $error) {
        $wpdb->query('ROLLBACK');
        if ($touched) { clean_post_cache($touched); }
        $code=$error->getMessage();
        $status=['forbidden'=>403,'missing'=>404,'idempotency_conflict'=>409,'identity_conflict'=>409,'expected_hash_required'=>400,'draft_required'=>400][$code] ?? 500;
        return new WP_Error('ce_'.$code,'Publication operation failed.',['status'=>$status]);
    } finally { $wpdb->get_var($wpdb->prepare('SELECT RELEASE_LOCK(%s)',$lock)); }
}
add_action('rest_api_init', function () {
    register_rest_route('content-engine/v1','/capabilities',['methods'=>'GET','permission_callback'=>'ce_bridge_allowed','callback'=>function () {
        return ['bridge_version'=>'1.0.0','seo_plugin'=>ce_bridge_plugin(),'meta_keys'=>ce_bridge_meta_keys(),
            'timezone'=>wp_timezone_string(),'can_edit'=>current_user_can('edit_posts'),
            'can_publish'=>current_user_can('publish_posts'),'author_id'=>get_current_user_id()];
    }]);
    foreach (['/posts','/posts/(?P<id>\d+)'] as $route) {
        register_rest_route('content-engine/v1',$route,['methods'=>'POST','permission_callback'=>'ce_bridge_allowed','callback'=>'ce_bridge_mutate']);
    }
    register_rest_route('content-engine/v1','/operation',['methods'=>'GET','permission_callback'=>'ce_bridge_allowed','callback'=>function ($request) {
        global $wpdb;
        $row=$wpdb->get_row($wpdb->prepare("SELECT post_id FROM {$wpdb->prefix}ce_operations WHERE operation=%s",(string)$request->get_param('operation')));
        return ['exists'=>$row && current_user_can('edit_post',$row->post_id),'post_id'=>$row ? (int)$row->post_id : null];
    }]);
    register_rest_route('content-engine/v1','/resolve' ,['methods'=>'GET','permission_callback'=>'ce_bridge_allowed','callback'=>function ($request) {
        $url=esc_url_raw($request->get_param('url'));
        if (wp_parse_url($url,PHP_URL_HOST)!==wp_parse_url(home_url(),PHP_URL_HOST)) { return ['exists'=>false]; }
        $id=url_to_postid($url);$post=$id ? get_post($id) : null;
        return ['exists'=>$post && $post->post_status==='publish','id'=>$id];
    }]);
});

// SEO output has exactly one owner. Filters use version-scoped data, avoiding stale indexables.
function ce_bridge_seo($id=0) { return get_post_meta($id ?: get_queried_object_id(),'ce_seo',true) ?: []; }
foreach (['wpseo_title'=>'seo_title','wpseo_metadesc'=>'meta_description','wpseo_canonical'=>'canonical_url',
    'wpseo_opengraph_title'=>'og_title','wpseo_opengraph_desc'=>'og_description',
    'wpseo_twitter_title'=>'twitter_title','wpseo_twitter_description'=>'twitter_description',
    'rank_math/frontend/title'=>'seo_title','rank_math/frontend/description'=>'meta_description',
    'rank_math/frontend/canonical'=>'canonical_url'] as $hook=>$key) {
    add_filter($hook,function ($value) use ($key) { $seo=ce_bridge_seo();return !empty($seo[$key]) ? $seo[$key] : $value; },99);
}
add_filter('wpseo_robots_array',function ($robots) {
    $seo=ce_bridge_seo();
    if ($seo) {
        // Never override a site's global noindex setting.
        $robots['index']=!empty($seo['robots_index']) && get_option('blog_public') ? 'index' : 'noindex';
        $robots['follow']=!empty($seo['robots_follow']) ? 'follow' : 'nofollow';
    }
    return $robots;
},99);
function ce_bridge_article_schema($data,$id=0) {
    $seo=ce_bridge_seo($id);
    if (!$seo) { return $data; }
    $post=get_post($id ?: get_queried_object_id());
    if ($post && $post->post_status!=='publish') { unset($data['datePublished']); }
    $type=$seo['schema_type'] ?? 'Article';
    if (in_array($type,['Article','NewsArticle','TechArticle'],true)) { $data['@type']=$type; }
    if ($type==='HowTo' && !empty($seo['howto_steps'])) {
        $data['@type']='HowTo';$data['name']=$seo['seo_title'];
        $data['step']=array_map(function ($s) { return ['@type'=>'HowToStep','name'=>$s['name'] ?? $s['text'],'text'=>$s['text']]; },$seo['howto_steps']);
    }
    return $data;
}
add_filter('wpseo_schema_article','ce_bridge_article_schema',99);
add_filter('wpseo_schema_webpage',function ($data) {
    $seo=ce_bridge_seo();
    $post=get_post(get_queried_object_id());
    if ($post && $post->post_status!=='publish') { unset($data['datePublished']); }
    if (!empty($seo['faq'])) {
        $data['@type']=['WebPage','FAQPage'];
        $data['mainEntity']=array_map(function ($f) { return ['@type'=>'Question','name'=>$f['question'],'acceptedAnswer'=>['@type'=>'Answer','text'=>$f['answer']]]; },$seo['faq']);
    }
    return $data;
},99);
add_filter('rank_math/json_ld',function ($graph) {
    foreach ($graph as $key=>$node) {
        if (is_array($node) && in_array($node['@type'] ?? '',['Article','NewsArticle','BlogPosting','TechArticle'],true)) { $graph[$key]=ce_bridge_article_schema($node); }
    }
    $seo=ce_bridge_seo();
    if (!empty($seo['faq'])) {
        foreach ($graph as $key=>$node) { if (is_array($node) && in_array($node['@type'] ?? '',['FAQPage'],true)) { unset($graph[$key]); } }
        $graph['ce_faq']=['@type'=>'FAQPage','@id'=>$seo['canonical_url'].'#faq','mainEntity'=>ce_bridge_faq_entities($seo['faq'])];
    }
    return $graph;
},99);
function ce_bridge_faq_entities($faq) {
    return array_map(function ($f) { return ['@type'=>'Question','name'=>$f['question'],'acceptedAnswer'=>['@type'=>'Answer','text'=>$f['answer']]]; },$faq);
}
// No-plugin fallback applies only to engine-managed posts, never in parallel with a SEO plugin.
add_action('wp',function () {
    if (ce_bridge_plugin()==='none' && is_singular('post') && ce_bridge_seo()) {
        remove_action('wp_head','rel_canonical');remove_action('wp_head','wp_robots');
        add_filter('pre_get_document_title',function ($title) { return ce_bridge_seo()['seo_title'] ?? $title; });
        add_action('wp_head',function () {
            $seo=ce_bridge_seo();
            echo '<meta name="description" content="'.esc_attr($seo['meta_description']).'">';
            echo '<link rel="canonical" href="'.esc_url($seo['canonical_url']).'">';
            echo '<meta name="robots" content="'.(!empty($seo['robots_index']) && get_option('blog_public') ? 'index' : 'noindex').', '.(!empty($seo['robots_follow']) ? 'follow' : 'nofollow').'">';
            foreach (['og:title'=>'og_title','og:description'=>'og_description','twitter:title'=>'twitter_title','twitter:description'=>'twitter_description'] as $name=>$key) {
                echo '<meta '.(str_starts_with($name,'og:') ? 'property' : 'name').'="'.esc_attr($name).'" content="'.esc_attr($seo[$key] ?? '').'">';
            }
            $image=get_the_post_thumbnail_url(get_queried_object_id(),'full');
            if ($image) { echo '<meta property="og:image" content="'.esc_url($image).'">'; }
            $schema=ce_bridge_article_schema(['@context'=>'https://schema.org','@type'=>'Article','headline'=>get_the_title(),'url'=>$seo['canonical_url']]);
            if (!empty($seo['faq'])) {
                $schema=['@context'=>'https://schema.org','@graph'=>[$schema,['@type'=>'FAQPage','@id'=>$seo['canonical_url'].'#faq','mainEntity'=>ce_bridge_faq_entities($seo['faq'])]]];
            }
            echo '<script type="application/ld+json">'.wp_json_encode($schema,JSON_HEX_TAG|JSON_HEX_AMP|JSON_HEX_APOS|JSON_HEX_QUOT).'</script>';
        });
    }
});

// Uploads also need remote idempotency: a lost media response must not upload again.
add_action('rest_api_init',function () {
    register_rest_route('content-engine/v1','/media',['methods'=>'POST','permission_callback'=>'ce_bridge_allowed','callback'=>function ($request) {
        global $wpdb;
        if (!current_user_can('upload_files')) { return new WP_Error('ce_forbidden','Upload forbidden.',['status'=>403]); }
        $body=$request->get_body();$identity='media:'.hash('sha256',$body);$lock='ce_'.substr(hash('sha256',$identity),0,50);
        if ((int)$wpdb->get_var($wpdb->prepare('SELECT GET_LOCK(%s,5)',$lock))!==1) { return new WP_Error('ce_busy','Upload busy.',['status'=>429]); }
        $wpdb->query('START TRANSACTION');$touched=0;
        try {
            $id=(int)$wpdb->get_var($wpdb->prepare("SELECT post_id FROM {$wpdb->prefix}ce_publications WHERE identity=%s FOR UPDATE",$identity));
            if ($id) {
                if (!current_user_can('edit_post',$id)) { $wpdb->query('ROLLBACK');return new WP_Error('ce_forbidden','Upload forbidden.',['status'=>403]); }
                $wpdb->query('COMMIT');
                $read=new WP_REST_Request('GET','/wp/v2/media/'.$id);$read->set_param('context','edit');return rest_do_request($read);
            }
            $native=new WP_REST_Request('POST','/wp/v2/media');$native->set_body($body);
            $native->set_header('Content-Type',$request->get_header('Content-Type'));
            $native->set_header('Content-Disposition',$request->get_header('Content-Disposition'));
            $response=rest_do_request($native);
            if ($response->get_status()>=400) { $wpdb->query('ROLLBACK');return $response; }
            $touched=(int)$response->get_data()['id'];
            if (!$wpdb->insert($wpdb->prefix.'ce_publications',['identity'=>$identity,'post_id'=>$touched])) { throw new Exception('database_write'); }
            $wpdb->query('COMMIT');return $response;
        } catch (Throwable $e) { $wpdb->query('ROLLBACK');if ($touched) { clean_post_cache($touched); }return new WP_Error('ce_upload_failed','Upload failed.',['status'=>500]); }
        finally { $wpdb->get_var($wpdb->prepare('SELECT RELEASE_LOCK(%s)',$lock)); }
    }]);
});
