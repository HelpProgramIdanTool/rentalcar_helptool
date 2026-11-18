<?php
/** Admin-only, narrowly scoped setup and rollback for the bilingual page foundation. */
defined('ABSPATH') || exit;

final class PRC_Bilingual_Stage_One {
    public static function config() {
        return json_decode(file_get_contents(__DIR__ . '/content/stage-one.json'),true);
    }

    public static function backup() {
        $existing=get_option('prc_bilingual_stage_one_backup');
        if ($existing) return ['success'=>true,'created'=>false,'snapshot'=>$existing];
        $config=self::config();
        $ids=array_values(array_unique(array_merge($config['english_pages'],$config['hebrew_pages'])));
        $snapshot=['created_at'=>gmdate('c'),'pages'=>[],'menus'=>[],
            'options'=>['polylang'=>get_option('polylang',null),
                'pll_language_from_content_available'=>get_option('pll_language_from_content_available',null),
                'page_on_front'=>get_option('page_on_front'),'show_on_front'=>get_option('show_on_front')],
            'nav_menu_locations'=>get_theme_mod('nav_menu_locations',[])];
        foreach ($ids as $id) {
            $post=get_post($id);
            if (!$post || $post->post_type!=='page') return new WP_Error('invalid_page','Expected page missing: '.$id);
            $snapshot['pages'][$id]=['post'=>array_intersect_key((array)$post,array_flip([
                'ID','post_title','post_content','post_excerpt','post_status','post_name','post_parent'])),
                'template'=>get_page_template_slug($id),'layout'=>get_post_meta($id,'_et_pb_page_layout',true)];
        }
        foreach (wp_get_nav_menus() as $menu) {
            $snapshot['menus'][]=['menu'=>(array)$menu,'items'=>array_map(function($item){
                return array_intersect_key((array)$item,array_flip(['ID','title','url','object_id','object','type','menu_item_parent','menu_order']));
            },wp_get_nav_menu_items($menu->term_id) ?: [])];
        }
        global $wpdb;
        $table=$wpdb->prefix.'aioseo_posts';
        if ($wpdb->get_var($wpdb->prepare('SHOW TABLES LIKE %s',$table))===$table) {
            $in=implode(',',array_map('absint',$ids));
            $snapshot['seo']=$wpdb->get_results("SELECT post_id,title,description,canonical_url,og_title,og_description,twitter_title,twitter_description,robots_default,robots_noindex FROM {$table} WHERE post_id IN ({$in})",ARRAY_A);
        }
        if (!add_option('prc_bilingual_stage_one_backup',$snapshot,'',false)) return new WP_Error('backup_failed','Could not save rollback snapshot.');
        return ['success'=>true,'created'=>true,'snapshot'=>$snapshot];
    }

    public static function configure() {
        if (!get_option('prc_bilingual_stage_one_backup')) return new WP_Error('backup_required','Save the stage-one backup first.');
        if (!function_exists('PLL') || !function_exists('pll_set_post_language')) return new WP_Error('polylang_required','Activate the installed Polylang plugin first.');
        $config=self::config();
        // This supported compatibility setting preserves every existing content URL.
        update_option('pll_language_from_content_available','yes',false);
        foreach (['force_lang'=>0,'hide_default'=>true,'rewrite'=>true,'redirect_lang'=>false,'browser'=>false,'media_support'=>false] as $key=>$value) {
            $error=PLL()->options->set($key,$value);
            if (is_wp_error($error) && $error->has_errors()) return $error;
        }
        foreach ([['name'=>'עברית','slug'=>'he','locale'=>'he_IL','rtl'=>true,'flag'=>'il'],
                  ['name'=>'English','slug'=>'en','locale'=>'en_GB','rtl'=>false,'flag'=>'gb']] as $language) {
            if (PLL()->model->get_language($language['slug'])) continue;
            $result=PLL()->model->add_language($language+['no_default_cat'=>true]);
            if (is_wp_error($result)) return $result;
        }
        $error=PLL()->options->set('default_lang','he');
        if (is_wp_error($error) && $error->has_errors()) return $error;
        foreach ($config['hebrew_pages'] as $id) {
            $language=pll_get_post_language($id,'slug');
            if ($language && $language!=='he') return new WP_Error('existing_language','Unexpected language on Hebrew page '.$id);
            pll_set_post_language($id,'he');
        }
        foreach ($config['english_pages'] as $id) pll_set_post_language($id,'en');
        foreach ($config['pairs'] as $pair) pll_save_post_translations(['he'=>$pair['he'],'en'=>$pair['en']]);
        // Preserve the current theme menus as Hebrew; custom English chrome is shared by English pages.
        foreach (wp_get_nav_menus() as $menu) {
            if (!pll_get_term_language($menu->term_id,'slug')) pll_set_term_language($menu->term_id,'he');
        }
        $menu_id=(int)get_option('prc_english_menu_id');
        if (!$menu_id || !wp_get_nav_menu_object($menu_id)) {
            $menu_id=wp_create_nav_menu('English — Poland Rent a Car');
            if (is_wp_error($menu_id)) return $menu_id;
            update_option('prc_english_menu_id',$menu_id,false);
        }
        pll_set_term_language($menu_id,'en');
        $existing=wp_get_nav_menu_items($menu_id) ?: [];
        foreach ($config['menu'] as $index=>$entry) {
            $item_id=0;
            foreach ($existing as $item) if ((int)$item->object_id===$entry['page']) $item_id=(int)$item->ID;
            $result=wp_update_nav_menu_item($menu_id,$item_id,[
                'menu-item-title'=>$entry['title'],'menu-item-object'=>'page',
                'menu-item-object-id'=>$entry['page'],'menu-item-type'=>'post_type',
                'menu-item-status'=>'publish','menu-item-position'=>$index+1]);
            if (is_wp_error($result)) return $result;
        }
        PLL()->options->save();
        PLL()->model->clean_languages_cache();
        flush_rewrite_rules(false);
        return self::state();
    }

    public static function state() {
        $config=self::config();
        $pages=[];
        foreach (array_merge($config['english_pages'],$config['hebrew_pages']) as $id) {
            $post=get_post($id);
            $pages[]=['id'=>$id,'status'=>$post ? $post->post_status : null,
                'language'=>function_exists('pll_get_post_language') ? pll_get_post_language($id,'slug') : '',
                'url'=>get_permalink($id),'template'=>get_page_template_slug($id)];
        }
        $options=get_option('polylang',[]);
        return ['success'=>true,'polylang_active'=>function_exists('PLL'),'backup_saved'=>(bool)get_option('prc_bilingual_stage_one_backup'),
            'english_menu_id'=>(int)get_option('prc_english_menu_id'),
            'options'=>array_intersect_key($options,array_flip(['force_lang','hide_default','default_lang','browser'])),
            'pages'=>$pages];
    }

    public static function activate_guides() {
        if (!function_exists('pll_set_post_language')) return new WP_Error('polylang_required','Polylang is required.');
        $guides=json_decode(file_get_contents(__DIR__.'/content/first-guides.json'),true);
        $menu_id=(int)get_option('prc_english_menu_id');
        if (!$menu_id || !wp_get_nav_menu_object($menu_id)) return new WP_Error('menu_required','English menu is required.');
        // Validate the entire batch before touching languages, pairs or navigation.
        foreach ($guides as $guide) {
            $post=get_post($guide['id']);
            if (!$post || $post->post_type!=='page' || $post->post_name!==$guide['slug'] || (int)$post->post_parent!==25371)
                return new WP_Error('invalid_guide','Unexpected guide page.');
            $paired=pll_get_post($guide['hebrew_page'],'en');
            if ($paired && (int)$paired!==(int)$guide['id']) return new WP_Error('pair_conflict','Existing translation must not be replaced.');
        }
        $snapshot=get_option('prc_first_guides_backup');
        if (!$snapshot) {
            add_option('prc_first_guides_backup',[
                'created_at'=>gmdate('c'),'menu'=>wp_get_nav_menu_items($menu_id),
                'navigation'=>get_option('prc_bilingual_navigation',[])
            ],'',false);
        }
        foreach ($guides as $guide) {
            pll_set_post_language($guide['id'],'en');
            pll_save_post_translations(['he'=>$guide['hebrew_page'],'en'=>$guide['id']]);
        }
        $existing=wp_get_nav_menu_items($menu_id) ?: [];
        foreach (self::config()['menu'] as $index=>$entry) {
            $item_id=0;
            foreach ($existing as $item) if ((int)$item->object_id===(int)$entry['page']) $item_id=(int)$item->ID;
            $result=wp_update_nav_menu_item($menu_id,$item_id,[
                'menu-item-title'=>$entry['title'],'menu-item-object'=>'page','menu-item-object-id'=>$entry['page'],
                'menu-item-type'=>'post_type','menu-item-status'=>'publish','menu-item-position'=>$index+1]);
            if (is_wp_error($result)) return $result;
        }
        $navigation=(array)get_option('prc_bilingual_navigation',[]);
        $defaults=json_decode(file_get_contents(__DIR__.'/content/navigation.json'),true);
        $navigation['tagline']=$defaults['tagline'];
        update_option('prc_bilingual_navigation',$navigation,false);
        return ['success'=>true,'guides'=>array_column($guides,'id'),'menu'=>$menu_id];
    }
}

add_action('wp_abilities_api_init',function(){
    foreach (['backup'=>'Save a rollback snapshot of public page content, selected language settings and menus; returns the protected snapshot.',
              'configure'=>'Configure approved Hebrew/English page languages and translation pairs while preserving existing addresses; requires a saved backup.',
              'state'=>'Read bilingual page language, address and publication state.',
              'activate_guides'=>'Link the three approved English guides to their Hebrew originals and add direct English menu links; preserves other language settings and saves a menu snapshot.'] as $method=>$description) {
        wp_register_ability('prc-bilingual/stage-one-'.str_replace('_','-',$method),[
            'label'=>'Bilingual foundation: '.$method,'description'=>$description,'category'=>'prc',
            'input_schema'=>['type'=>'object'],
            'permission_callback'=>function(){return current_user_can('manage_options');},
            'execute_callback'=>['PRC_Bilingual_Stage_One',$method],
            'meta'=>['show_in_rest'=>true,'mcp'=>['public'=>true,'type'=>'tool'],
                'annotations'=>['readOnlyHint'=>$method==='state','destructiveHint'=>false,'idempotentHint'=>true]],
        ]);
    }
});
