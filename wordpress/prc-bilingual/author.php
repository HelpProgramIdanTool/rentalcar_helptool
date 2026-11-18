<?php
/** Shared, bilingual introduction using Idan's approved original portrait. */
defined('ABSPATH') || exit;

final class PRC_Bilingual_Author {
    public static function config() {
        $defaults=json_decode(file_get_contents(__DIR__.'/content/author.json'),true);
        foreach (['en','he'] as $language) {
            $defaults[$language]=array_merge($defaults[$language],(array)get_option('prc_author_'.$language,[]));
        }
        return $defaults;
    }

    public static function card($english,$compact=false) {
        $config=self::config();
        $copy=$config[$english ? 'en' : 'he'];
        $navigation=PRC_Bilingual_Form::navigation($english);
        $description=$copy[$compact ? 'form_description' : 'description'];
        return '<section class="prc-author-card'.($compact ? ' prc-author-card--compact' : '').'" lang="'.($english ? 'en' : 'he').'" dir="'.($english ? 'ltr' : 'rtl').'" aria-label="'.esc_attr($copy['name']).'">'.
            '<img class="prc-author-portrait" src="'.esc_url(plugins_url('assets/idan-portrait.jpg',__FILE__)).'" width="600" height="597" loading="lazy" decoding="async" alt="'.esc_attr($copy['alt']).'">'.
            '<div class="prc-author-copy"><p class="prc-author-name">'.esc_html($copy['name']).'</p>'.
            '<p class="prc-author-role">'.esc_html($copy['role']).'</p><p>'.esc_html($description).'</p>'.
            '<a href="'.esc_url(home_url($navigation['contact_path'])).'">'.esc_html($copy['contact_label']).'</a></div></section>';
    }

    public static function content($content) {
        if (is_admin() || is_feed() || !is_page() || !is_main_query() || !in_the_loop()) return $content;
        if (!PRC_Bilingual_Form::english_page() && !PRC_Bilingual_Form::hebrew_page()) return $content;
        $id=get_the_ID();
        $config=self::config();
        if (in_array($id,$config['excluded_pages'],true) || strpos($content,'prc-author-card')!==false) return $content;
        $card=self::card(PRC_Bilingual_Form::english_page(),in_array($id,$config['form_pages'],true));
        return in_array($id,$config['intro_pages'],true) ? $card.$content : $content.$card;
    }
}
add_filter('the_content',['PRC_Bilingual_Author','content'],30);

add_action('customize_register',function($customizer){
    $config=PRC_Bilingual_Author::config();
    foreach (['en','he'] as $language) {
        $section='prc_author_'.$language;
        $customizer->add_section($section,['title'=>'PRC — Idan ('.$language.')','priority'=>162]);
        foreach ($config[$language] as $key=>$value) {
            $setting=$section.'['.$key.']';
            $customizer->add_setting($setting,['type'=>'option','capability'=>'manage_options','default'=>$value,'sanitize_callback'=>'sanitize_text_field']);
            $customizer->add_control($setting,['section'=>$section,'label'=>ucfirst(str_replace('_',' ',$key)),'type'=>'textarea']);
        }
    }
});
