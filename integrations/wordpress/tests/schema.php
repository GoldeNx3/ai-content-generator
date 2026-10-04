<?php
// Pure contract tests for the bridge's schema filters, independent of an installed SEO plugin.
define('ABSPATH', __DIR__.'/');
$hooks=[];
function register_activation_hook($file,$fn) {}
function add_action($hook,$fn,$priority=10,$count=1) { global $hooks;$hooks[$hook][]=$fn; }
function add_filter($hook,$fn,$priority=10,$count=1) { global $hooks;$hooks[$hook][]=$fn; }
function get_queried_object_id() { return 1; }
function get_post_meta($id,$key,$single) { global $seo;return $seo; }
function get_post($id) { global $post_status;return (object)['post_status'=>$post_status]; }
function check($condition,$message) { if (!$condition) { throw new RuntimeException($message); } }
require getenv('CE_BRIDGE_FILE') ?: __DIR__.'/../content-engine-bridge/content-engine-bridge.php';
$seo=['schema_type'=>'NewsArticle','canonical_url'=>'https://example.test/article/','seo_title'=>'Title'];
$post_status='draft';
$article=ce_bridge_article_schema(['@type'=>'Article','datePublished'=>'0000-00-00']);
check($article['@type']==='NewsArticle' && !isset($article['datePublished']),'Draft must not have an invented publish date');
$post_status='publish';
$seo['schema_type']='HowTo';$seo['howto_steps']=[['name'=>'Step','text'=>'Actual step']];
check(ce_bridge_article_schema(['@type'=>'Article'])['step'][0]['@type']==='HowToStep','HowTo steps');
$seo['schema_type']='FAQPage';$seo['faq']=[['question'=>'Real question?','answer'=>'Real answer.']];
$entities=ce_bridge_faq_entities($seo['faq']);
check($entities[0]['acceptedAnswer']['text']==='Real answer.','FAQ answer shape');
$yoast=$hooks['wpseo_schema_webpage'][0](['@type'=>'WebPage']);
check($yoast['@type']===['WebPage','FAQPage'] && count($yoast['mainEntity'])===1,'Yoast FAQ uses existing page');
$rank=$hooks['rank_math/json_ld'][0](['article'=>['@type'=>'Article']]);
check($rank['ce_faq']['@type']==='FAQPage' && count($rank['ce_faq']['mainEntity'])===1,'RankMath FAQ');
echo "PASS: Article/NewsArticle/HowTo/FAQ graph contracts and draft dates\n";
