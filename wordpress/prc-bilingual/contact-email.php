<?php
defined('ABSPATH') || exit;

function prc_bilingual_contact_email($args) {
    $email=sanitize_email($args['email'] ?? '');
    if (!is_email($email)) return new WP_Error('invalid_email','A valid contact email is required.');
    $navigation=PRC_Bilingual_Form::navigation();
    $aliases=array_values(array_unique(array_filter(array_map('sanitize_email',(array)($args['old_emails'] ?? [])))));
    if (!empty($navigation['contact_email']) && $navigation['contact_email']!==$email) $aliases[]=$navigation['contact_email'];
    $aliases=array_values(array_filter(array_unique($aliases),function($old)use($email){return strcasecmp($old,$email)!==0;}));
    $apply=!empty($args['apply']);
    $changed=[];
    // Only public-site content and theme layouts; never request records or mail settings.
    $types=['page','post','et_header_layout','et_footer_layout','et_pb_layout'];
    $posts=get_posts(['post_type'=>$types,'post_status'=>['publish','draft','private','inherit'],
        'posts_per_page'=>-1,'suppress_filters'=>true,'lang'=>'']);
    foreach ($posts as $post) {
        $content=$aliases ? str_ireplace($aliases,$email,$post->post_content,$count) : $post->post_content;
        if (!$aliases || !$count) continue;
        $changed[]=['id'=>$post->ID,'type'=>$post->post_type,'matches'=>$count];
        if ($apply) {
            $result=wp_update_post(['ID'=>$post->ID,'post_content'=>wp_slash($content)],true);
            if (is_wp_error($result)) return $result;
        }
    }
    $theme=get_option('et_divi',[]);
    $theme_changed=false;
    if (!empty($theme['header_email']) && in_array($theme['header_email'],$aliases,true)) {
        $theme_changed=true;
        if ($apply) { $theme['header_email']=$email; update_option('et_divi',$theme); }
    }
    if ($apply) {
        $saved=(array)get_option('prc_bilingual_navigation',[]);
        $saved['contact_email']=$email;
        update_option('prc_bilingual_navigation',$saved,false);
    }
    return ['success'=>true,'applied'=>$apply,'contact_email'=>$email,
        'previous_contact_email'=>$navigation['contact_email'],'content_changes'=>$changed,
        'theme_header_changed'=>$theme_changed,'scanned_types'=>$types,'scanned_count'=>count($posts)];
}

add_action('wp_abilities_api_init',function(){
    wp_register_ability('prc-bilingual/contact-email',[
        'label'=>'Update public website contact email',
        'description'=>'Audit or update the shared public contact email and explicitly identified old contact addresses in page content and theme layouts. Keeps revisions. Does not change request records, SMTP, account or admin email settings.',
        'category'=>'prc','input_schema'=>['type'=>'object','required'=>['email'],'properties'=>[
            'email'=>['type'=>'string','format'=>'email'],
            'old_emails'=>['type'=>'array','items'=>['type'=>'string','format'=>'email']],
            'apply'=>['type'=>'boolean','default'=>false]]],
        'permission_callback'=>function(){return current_user_can('manage_options');},
        'execute_callback'=>'prc_bilingual_contact_email',
        'meta'=>['show_in_rest'=>true,'mcp'=>['public'=>true,'type'=>'tool'],
            'annotations'=>['readOnlyHint'=>false,'destructiveHint'=>false,'idempotentHint'=>true]],
    ]);
});
