<?php
// Permission contracts of the Bridge REST routes that do not go through the native WP controller.
define('ABSPATH', __DIR__.'/');
$hooks=[];$routes=[];$editable=[];
function register_activation_hook($file,$fn) {}
function add_action($hook,$fn,$priority=10,$count=1) { global $hooks;$hooks[$hook][]=$fn; }
function add_filter($hook,$fn,$priority=10,$count=1) { global $hooks;$hooks[$hook][]=$fn; }
function register_rest_route($namespace,$route,$args) { global $routes;$routes[$route]=$args; }
function current_user_can($cap,$id=null) { global $editable;return $cap==='edit_posts' || ($cap==='edit_post' && in_array($id,$editable,true)); }
function check($condition,$message) { if (!$condition) { throw new RuntimeException($message); } }
final class FakeRequest { public function __construct(private array $params) {} public function get_param($key) { return $this->params[$key] ?? null; } }
final class FakeWpdb { public $prefix='wp_'; public function prepare($sql,...$args) { return $sql; } public function get_row($sql) { return (object)['post_id'=>42]; } }
$wpdb=new FakeWpdb;
require getenv('CE_BRIDGE_FILE') ?: __DIR__.'/../content-engine-bridge/content-engine-bridge.php';
foreach ($hooks['rest_api_init'] as $init) { $init(); }

$operation=$routes['/operation']['callback'];
$foreign=$operation(new FakeRequest(['operation'=>'job:phase']));
check($foreign===['exists'=>false,'post_id'=>null],'operation lookup must not reveal a post the user cannot edit: '.json_encode($foreign));
$editable=[42];
check($operation(new FakeRequest(['operation'=>'job:phase']))===['exists'=>true,'post_id'=>42],'own operation is reported');
echo "PASS: operation lookup reveals post ids only to users who can edit them\n";
