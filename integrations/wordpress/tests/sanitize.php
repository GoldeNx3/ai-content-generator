<?php
// Contract tests for stored SEO data: everything written to ce_seo is sanitized and the no-plugin <title> is plain text.
define('ABSPATH', __DIR__.'/');
$hooks=[];$meta=[];
function register_activation_hook($file,$fn) {}
function add_action($hook,$fn,$priority=10,$count=1) { global $hooks;$hooks[$hook][]=$fn; }
function add_filter($hook,$fn,$priority=10,$count=1) { global $hooks;$hooks[$hook][]=$fn; }
function remove_action($hook,$fn) {}
function register_post_meta($type,$key,$args) { global $meta;$meta[$key]=$args; }
function get_queried_object_id() { return 1; }
function get_post_meta($id,$key,$single) { global $seo;return $seo; }
function is_singular($type) { return true; }
function sanitize_text_field($value) { return trim(preg_replace('/\s+/',' ',preg_replace('/%[a-f0-9]{2}/i','',strip_tags((string) $value)))); }
function sanitize_textarea_field($value) { return trim(preg_replace('/%[a-f0-9]{2}/i','',strip_tags((string) $value))); }
if (!function_exists('wp_check_invalid_utf8')) { function wp_check_invalid_utf8($v) { return $v; } }
function esc_url_raw($url) { return preg_match('#^https?://#i',(string) $url) ? (string) $url : ''; }
function wp_strip_all_tags($value) { return trim(strip_tags(preg_replace('@<(script|style)[^>]*?>.*?</\\1>@si','',(string) $value))); }
function check($condition,$message) { if (!$condition) { throw new RuntimeException($message); } }
require getenv('CE_BRIDGE_FILE') ?: __DIR__.'/../content-engine-bridge/content-engine-bridge.php';

foreach ($hooks['init'] as $init) { $init(); }
$sanitize=$meta['ce_seo']['sanitize_callback'] ?? null;
check(is_callable($sanitize),'ce_seo must have a sanitize_callback');
$clean=$sanitize([
    'seo_title'=>'</title><script>alert(1)</script>Tytuł','meta_description'=>'<b>Opis</b>','canonical_url'=>'javascript:alert(1)',
    'featured_image_url'=>'https://example.test/a.png','tags'=>['<img src=x onerror=alert(1)>ok'],
    'faq'=>[['question'=>'<script>q</script>Pytanie?','answer'=>'<i>Odpowiedź</i>']],'robots_index'=>'1','author_id'=>'7',
]);
check($clean['seo_title']==='alert(1)Tytuł','seo_title stripped of tags: '.$clean['seo_title']);
check($clean['meta_description']==='Opis','meta_description stripped');
check($clean['canonical_url']==='','javascript: canonical dropped');
check($clean['featured_image_url']==='https://example.test/a.png','http(s) URL kept');
check($clean['tags']===['ok'],'tags stripped');
check($clean['faq'][0]===['question'=>'qPytanie?','answer'=>'Odpowiedź'],'FAQ stripped');
$multi=$sanitize(['faq'=>[['question'=>'Ile?','answer'=>"Linia 1\nLinia 2: 100%efektywny"]],'howto_steps'=>[['name'=>'Krok','text'=>"A\nB"]]]);
check($multi['faq'][0]['answer']==="Linia 1\nLinia 2: 100%efektywny",'FAQ answer keeps newlines and percent signs: '.json_encode($multi['faq'][0]['answer']));
check($multi['howto_steps'][0]['text']==="A\nB",'HowTo text keeps newlines');
check($clean['robots_index']===true && $clean['author_id']===7,'scalars cast');

$seo=['seo_title'=>'</title><script>alert(1)</script>','canonical_url'=>'https://example.test/a/','meta_description'=>'x'];
foreach ($hooks['wp'] as $wp) { $wp(); }
$title=end($hooks['pre_get_document_title'])('Domyślny');
check(!str_contains($title,'<'),'no-plugin <title> must be plain text: '.$title);
echo "PASS: ce_seo sanitized on write (text, URLs, lists, FAQ, scalars) and plain-text document title\n";
