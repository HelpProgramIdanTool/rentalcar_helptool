<?php
/**
 * Plugin Name: PRC Bilingual Form
 * Description: English presentation and saved client language for the existing PRC request form.
 * Version: 0.2.1
 */
defined('ABSPATH') || exit;

final class PRC_Bilingual_Form {
    public static function english_page() {
        return is_page() && in_array(get_page_template_slug(),['prc-request-full-width.php','prc-english-page.php'],true);
    }
    public static function hebrew_page() {
        return !is_admin() && !self::english_page() && function_exists('pll_current_language') && pll_current_language('slug')==='he';
    }
    public static function catalog() {
        static $catalog;
        if ($catalog === null) $catalog = json_decode(file_get_contents(__DIR__ . '/content/form-en.json'), true);
        return is_array($catalog) ? $catalog : [];
    }

    public static function english($atts = []) {
        if (isset($atts['language'])) return $atts['language'] === 'en';
        return function_exists('pll_current_language') && pll_current_language('slug') === 'en';
    }

    public static function navigation($english=true) {
        $defaults=json_decode(file_get_contents(__DIR__ . '/content/navigation.json'),true);
        $navigation=array_merge($defaults,(array)get_option('prc_bilingual_navigation',[]));
        if (!$english) {
            $hebrew=json_decode(file_get_contents(__DIR__.'/content/navigation-he.json'),true);
            $navigation=array_merge($navigation,$hebrew,(array)get_option('prc_bilingual_navigation_he',[]));
        }
        return $navigation;
    }

    public static function footer_html($english=true) {
        $navigation=self::navigation($english);
        $language=$english ? 'en' : 'he';
        $direction=$english ? 'ltr' : 'rtl';
        ob_start();
        include __DIR__.'/footer.php';
        return ob_get_clean();
    }

    public static function switcher_style($active) {
        return $active ? 'color:#fff!important;background-color:#163960!important;opacity:1!important;'
            : 'color:#163960!important;background-color:#fff!important;opacity:1!important;';
    }

    public static function language_switcher($english) {
        $navigation = self::navigation();
        $hebrew_url = home_url('/');
        $english_url = home_url($navigation['home_path']);
        if (function_exists('pll_get_post')) {
            $id = get_queried_object_id();
            $hebrew_id = pll_get_post($id,'he');
            $english_id = pll_get_post($id,'en');
            if ($hebrew_id) $hebrew_url = get_permalink($hebrew_id);
            if ($english_id) $english_url = get_permalink($english_id);
        } elseif (is_page()) {
            $page=get_post(get_queried_object_id());
            if ($page && has_shortcode($page->post_content,'poland_car_request_form')) {
                $hebrew_url=home_url($navigation['hebrew_quote_path']);
                $english_url=home_url($navigation['english_quote_path']);
            }
        }
        return '<nav class="prc-language-switcher" aria-label="Language">' .
            '<a lang="he" dir="rtl" hreflang="he" href="' . esc_url($hebrew_url) . '" style="'.esc_attr(self::switcher_style(!$english)).'"' . (!$english ? ' aria-current="page"' : '') . '>עברית</a>' .
            '<a lang="en" hreflang="en" href="' . esc_url($english_url) . '" style="'.esc_attr(self::switcher_style($english)).'"' . ($english ? ' aria-current="page"' : '') . '>English</a></nav>';
    }

    public static function text($value) {
        $key = preg_replace('/\s+/u', ' ', trim($value));
        $catalog = self::catalog();
        if (!isset($catalog[$key])) {
            // A paragraph can contain a translated sentence followed by a dynamic address.
            foreach ($catalog as $source => $translated) {
                if (strlen($source) > 60 && strpos($key, $source . ' ') === 0) {
                    return $translated . ' ' . substr($key, strlen($source) + 1);
                }
            }
            return $value;
        }
        preg_match('/^(\s*).*?(\s*)$/us', $value, $spaces);
        return $spaces[1] . $catalog[$key] . $spaces[2];
    }

    public static function render($output, $tag, $atts) {
        if ($tag !== 'poland_car_request_form') return $output;
        if (!self::english((array) $atts)) return $output;
        if (!class_exists('DOMDocument')) {
            return '<p role="alert">The English form is temporarily unavailable. Please contact us for a quotation.</p>';
        }
        $document = new DOMDocument('1.0', 'UTF-8');
        $previous = libxml_use_internal_errors(true);
        $document->loadHTML('<?xml encoding="UTF-8"><div id="prc-translation-root">' . $output . '</div>', LIBXML_HTML_NOIMPLIED | LIBXML_HTML_NODEFDTD | LIBXML_NONET);
        libxml_clear_errors();
        libxml_use_internal_errors($previous);
        $xpath = new DOMXPath($document);
        // Translate text and accessible labels, never submitted values or executable code.
        foreach ($xpath->query('//text()[not(ancestor::script) and not(ancestor::style) and not(ancestor::textarea)]') as $node) {
            if ($node->parentNode->nodeName === 'option' && !$node->parentNode->hasAttribute('value')) {
                $node->parentNode->setAttribute('value', $node->parentNode->textContent);
            }
            $node->nodeValue = self::text($node->nodeValue);
        }
        foreach (['placeholder', 'aria-label', 'title'] as $attribute) {
            foreach ($xpath->query('//*[@' . $attribute . ']') as $node) {
                $node->setAttribute($attribute, self::text($node->getAttribute($attribute)));
            }
        }
        foreach ($xpath->query('//a[@href]') as $link) {
            if ($link->getAttribute('href')===home_url('/privacy-policy/')) {
                $link->setAttribute('href',home_url(self::navigation()['privacy_path']));
            }
        }
        foreach ($xpath->query('//*[contains(concat(" ", normalize-space(@class), " "), " prc-form-wrap ")]') as $wrapper) {
            $wrapper->setAttribute('lang', 'en');
            $wrapper->setAttribute('dir', 'ltr');
        }
        foreach ($xpath->query('//form[@id="prcRequestForm"]') as $form) {
            foreach (['prc_client_language' => 'en', 'prc_request_page' => (string) get_the_ID()] as $name => $value) {
                $input = $document->createElement('input');
                $input->setAttribute('type', 'hidden');
                $input->setAttribute('name', $name);
                $input->setAttribute('value', $value);
                $form->appendChild($input);
            }
        }
        foreach (['pickup','dropoff'] as $side) {
            $date = $document->getElementById('prc_' . $side . '_date_display');
            if ($date) {
                $date->removeAttribute('readonly');
                $date->setAttribute('placeholder','DD.MM.YYYY');
                $date->setAttribute('inputmode','numeric');
                $date->setAttribute('maxlength','10');
                $date->setAttribute('pattern','[0-9]{2}\\.[0-9]{2}\\.[0-9]{4}');
            }
            $time = $document->getElementById('prc_' . $side . '_time_display');
            if (!$time) continue;
            $select = $document->createElement('select');
            $select->setAttribute('id','prc_' . $side . '_half_hour');
            $select->setAttribute('class','prc-half-hour');
            $select->setAttribute('required','required');
            $select->setAttribute('aria-label',$side === 'pickup' ? 'Collection time' : 'Return time');
            $option = $document->createElement('option','Choose time');
            $option->setAttribute('value','');
            $select->appendChild($option);
            for ($minutes = 0; $minutes < 1440; $minutes += 30) {
                $value = sprintf('%02d:%02d',intdiv($minutes,60),$minutes % 60);
                $option = $document->createElement('option',$value);
                $option->setAttribute('value',$value);
                $select->appendChild($option);
            }
            $time->parentNode->appendChild($select);
        }
        wp_enqueue_style('prc-bilingual', plugin_dir_url(__FILE__) . 'form.css', [], '0.2.1');
        wp_add_inline_script('poland-car-request-form', 'window.PRCFormEnglish=' . wp_json_encode(self::catalog()) . ';', 'before');
        wp_add_inline_script('poland-car-request-form', file_get_contents(__DIR__ . '/form.js'), 'before');
        wp_add_inline_script('poland-car-request-form', file_get_contents(__DIR__ . '/pickers.js'), 'after');
        $result = '';
        $root = $document->getElementById('prc-translation-root');
        foreach ($root->childNodes as $node) $result .= $document->saveHTML($node);
        return $result;
    }

    public static function save_language($meta_id, $post_id, $key, $value) {
        if ($key !== '_prc_request_id' || get_post_type($post_id) !== 'prc_request') return;
        $english = isset($_POST['prc_client_language']) && $_POST['prc_client_language'] === 'en';
        add_post_meta($post_id, '_prc_client_language', $english ? 'English' : 'Hebrew', true);
    }

    public static function email_language($mail) {
        // Match only this handler's own request reference, never another WordPress email.
        if (!preg_match('/^מספר פנייה: ([^\r\n]+)\Rקישור לבקשה במערכת: (https?:\/\/[^\s]+)/u', $mail['message'], $match)) return $mail;
        $url = html_entity_decode($match[2], ENT_QUOTES, 'UTF-8');
        if (wp_parse_url($url, PHP_URL_HOST) !== wp_parse_url(home_url(), PHP_URL_HOST)) return $mail;
        parse_str((string) wp_parse_url($url, PHP_URL_QUERY), $query);
        $id = isset($query['post']) ? absint($query['post']) : 0;
        if (!$id || get_post_type($id) !== 'prc_request' || get_post_meta($id, '_prc_request_id', true) !== trim($match[1])) return $mail;
        $language = get_post_meta($id, '_prc_client_language', true) === 'English' ? 'English' : 'Hebrew';
        $mail['message'] = 'Client language: ' . $language . "\n" . $mail['message'];
        return $mail;
    }

    public static function redirect($location, $status) {
        if (!isset($_POST['prc_client_language']) || $_POST['prc_client_language'] !== 'en' ||
            !isset($_POST['action']) || $_POST['action'] !== 'poland_car_request_submit') return $location;
        parse_str((string) wp_parse_url($location, PHP_URL_QUERY), $query);
        if (!isset($query['prc_status']) || wp_parse_url($location, PHP_URL_HOST) !== wp_parse_url(home_url(), PHP_URL_HOST)) return $location;
        $id = isset($_POST['prc_request_page']) ? absint($_POST['prc_request_page']) : 0;
        $page = $id ? get_post($id) : null;
        if (!$page || $page->post_type !== 'page' || $page->post_status !== 'publish' ||
            !has_shortcode($page->post_content, 'poland_car_request_form')) return $location;
        if (function_exists('pll_get_post_language') && pll_get_post_language($id, 'slug') !== 'en') return $location;
        return add_query_arg($query, get_permalink($id)) . '#prcStatusMessage';
    }

    public static function health() {
        if (!class_exists('DOMDocument')) return new WP_Error('missing_dom', 'PHP DOM is required.');
        $checks = [];
        $html = '<div class="prc-form-wrap" lang="he" dir="rtl"><form id="prcRequestForm"><label>שם ושם משפחה</label><input name="driver_age" value="כן"><select><option>שדה תעופה</option></select><p>לא חושב עדיין</p></form></div>';
        $html = str_replace('</form>', '<input id="prc_pickup_date_display" readonly><div class="prc-time-control"><input id="prc_pickup_time_display"></div><a href="'.esc_url(home_url('/privacy-policy/')).'">מדיניות הפרטיות</a></form>', $html);
        $translated = self::render($html, 'poland_car_request_form', ['language'=>'en']);
        $checks['server_translation'] = strpos($translated, 'Full name') !== false && strpos($translated, 'lang="en"') !== false;
        $checks['submitted_values_preserved'] = strpos($translated, 'value="כן"') !== false && strpos($translated, 'value="שדה תעופה"') !== false;
        $checks['language_field'] = strpos($translated, 'name="prc_client_language" value="en"') !== false;
        $checks['hebrew_unchanged'] = self::render($html, 'poland_car_request_form', ['language'=>'he']) === $html;
        $checks['inline_spaces'] = self::text(' מדיניות הפרטיות ') === ' Privacy Policy ';
        $checks['dynamic_footer_translation'] = self::text('הטופס שומר כל בקשה במערכת ושולח התראה למייל: TEST-DESTINATION') ===
            self::catalog()['הטופס שומר כל בקשה במערכת ושולח התראה למייל:'] . ' TEST-DESTINATION';
        $checks['dot_date_placeholder'] = strpos($translated, 'placeholder="DD.MM.YYYY"') !== false;
        $checks['english_privacy_link'] = strpos($translated, 'href="'.esc_url(home_url(self::navigation()['privacy_path'])).'"') !== false;
        $hebrew_footer=self::footer_html(false);
        $english_footer=self::footer_html(true);
        $tags=function($html){
            $document=new DOMDocument();
            $previous=libxml_use_internal_errors(true);
            $document->loadHTML('<?xml encoding="UTF-8">'.$html,LIBXML_NONET);
            libxml_clear_errors();
            libxml_use_internal_errors($previous);
            $names=[];
            foreach ($document->getElementsByTagName('*') as $node) $names[]=$node->nodeName;
            return $names;
        };
        $checks['shared_footer_structure']=$tags($hebrew_footer)===$tags($english_footer);
        $checks['hebrew_footer_rtl']=strpos($hebrew_footer,'lang="he" dir="rtl"')!==false;
        $checks['active_hebrew_switcher_colors']=strpos(self::language_switcher(false),
            'style="color:#fff!important;background-color:#163960!important;opacity:1!important;" aria-current="page">עברית')!==false;
        preg_match('/<select id="prc_pickup_half_hour"[^>]*>(.*?)<\/select>/s', $translated, $time_select);
        $checks['half_hour_options'] = isset($time_select[1]) && substr_count($time_select[1], '<option') === 49 &&
            strpos($time_select[1], 'value="00:30"') !== false && strpos($time_select[1], 'value="23:30"') !== false &&
            strpos($time_select[1], 'value="00:15"') === false;
        $before = $_POST;
        $post_id = 0;
        try {
            $_POST = ['prc_client_language'=>'en'];
            $request_id = 'PRC-BILINGUAL-QA-' . wp_generate_uuid4();
            $post_id = wp_insert_post(['post_type'=>'prc_request','post_status'=>'private',
                'post_title'=>$request_id,'meta_input'=>['_prc_request_id'=>$request_id]], true);
            if (is_wp_error($post_id)) return $post_id;
            $checks['language_saved'] = get_post_meta($post_id, '_prc_client_language', true) === 'English';
            $_POST = []; // A later retry must read saved language, not a browser field.
            $body = 'מספר פנייה: ' . $request_id . "\nקישור לבקשה במערכת: " . admin_url('post.php?post=' . $post_id . '&action=edit');
            $mail = self::email_language(['message'=>$body]);
            $checks['retry_language'] = strpos($mail['message'], "Client language: English\n") === 0;
            $unrelated = ['message'=>'TEST UNRELATED MAIL'];
            $checks['unrelated_mail_unchanged'] = self::email_language($unrelated) === $unrelated;
        } finally {
            $_POST = $before;
            if ($post_id && !is_wp_error($post_id)) wp_delete_post($post_id, true);
        }
        return ['success'=>!in_array(false, $checks, true), 'checks'=>$checks, 'mail_sent'=>false];
    }
}

add_filter('do_shortcode_tag', ['PRC_Bilingual_Form', 'render'], 20, 3);
add_action('added_post_meta', ['PRC_Bilingual_Form', 'save_language'], 10, 4);
add_filter('wp_mail', ['PRC_Bilingual_Form', 'email_language']);
add_filter('wp_redirect', ['PRC_Bilingual_Form', 'redirect'], 10, 2);

add_filter('theme_page_templates', function ($templates) {
    $templates['prc-request-full-width.php'] = 'PRC English request — no sidebar';
    $templates['prc-english-page.php'] = 'PRC English page — no sidebar';
    return $templates;
});
add_filter('template_include', function ($template) {
    return PRC_Bilingual_Form::english_page()
        ? __DIR__ . '/request-full-width.php' : $template;
});
add_filter('language_attributes', function ($attributes) {
    return PRC_Bilingual_Form::english_page()
        ? 'lang="en" dir="ltr"' : $attributes;
});
add_filter('body_class', function ($classes) {
    if (PRC_Bilingual_Form::english_page()) $classes[] = 'prc-english-page';
    if (PRC_Bilingual_Form::hebrew_page()) $classes[] = 'prc-hebrew-page';
    return $classes;
});
add_action('wp_enqueue_scripts',function(){
    if (PRC_Bilingual_Form::english_page() || (is_page() && function_exists('pll_current_language'))) {
        wp_enqueue_style('prc-bilingual',plugin_dir_url(__FILE__).'form.css',[],'0.2.1');
    }
});
add_filter('wp_nav_menu_args',function($args){
    if (!PRC_Bilingual_Form::hebrew_page()) return $args;
    $menu=wp_get_nav_menu_object($args['menu'] ?? 0);
    if (!$menu || (function_exists('pll_get_term_language') && pll_get_term_language($menu->term_id,'slug')==='en')) {
        $locations=get_nav_menu_locations();
        if (!empty($locations['primary-menu'])) $args['menu']=$locations['primary-menu'];
    }
    return $args;
});
add_action('get_footer',function(){
    static $printed=false;
    if (!$printed && PRC_Bilingual_Form::hebrew_page()) {
        $printed=true;
        echo PRC_Bilingual_Form::footer_html(false);
    }
});
add_filter('wp_nav_menu_items',function($items){
    if (is_admin() || PRC_Bilingual_Form::english_page()) return $items;
    // Replace the old English-only menu shortcut with the paired language selector.
    $items=preg_replace('~<li\b[^>]*>\s*<a\b[^>]*href=["\x27][^"\x27]*/english/["\x27][^>]*>\s*En\s*</a>\s*</li>~i','',$items);
    return $items.'<li class="prc-language-menu">'.PRC_Bilingual_Form::language_switcher(false).'</li>';
});
add_filter('the_content',function($content){
    return PRC_Bilingual_Form::english_page()
        ? preg_replace('~(<table\b.*?</table>)~is','<div class="prc-table-scroll">$1</div>',$content) : $content;
},30);
add_filter('aioseo_facebook_tags',function($tags){
    if (PRC_Bilingual_Form::english_page()) {
        $tags['og:locale']='en_GB';
        $tags['og:site_name']=PRC_Bilingual_Form::navigation()['brand'];
    }
    return $tags;
});
add_filter('aioseo_schema_output',function($graphs){
    if (!PRC_Bilingual_Form::english_page()) return $graphs;
    $navigation=PRC_Bilingual_Form::navigation();
    foreach ($graphs as &$graph) {
        if (isset($graph['inLanguage'])) $graph['inLanguage']='en';
        if (in_array($graph['@type'] ?? '',['Organization','WebSite'],true)) {
            $graph['description']=$navigation['tagline'];
        }
        if (($graph['@type'] ?? '')==='BreadcrumbList') {
            if (empty($graph['itemListElement'])) continue;
            foreach ($graph['itemListElement'] as &$item) {
                if (($item['position'] ?? 0)===1 && isset($item['item'])) {
                    $item['item']=home_url($navigation['home_path']);
                    $item['name']='Home';
                }
            }
            unset($item);
        }
    }
    unset($graph);
    return $graphs;
});
require_once __DIR__.'/stage-one.php';
add_action('init',function(){
    if (get_option('prc_bilingual_navigation',null)===null) {
        add_option('prc_bilingual_navigation',json_decode(file_get_contents(__DIR__.'/content/navigation.json'),true),'',false);
    }
    if (get_option('prc_bilingual_navigation_he',null)===null) {
        add_option('prc_bilingual_navigation_he',json_decode(file_get_contents(__DIR__.'/content/navigation-he.json'),true),'',false);
    }
});
add_action('customize_register',function($customizer){
    $customizer->add_section('prc_english_site',['title'=>'PRC — English site','priority'=>160]);
    $labels=['brand'=>'Site name','tagline'=>'Footer description','contact_email'=>'Contact email','phone'=>'Phone',
        'footer_heading'=>'Footer links heading','footer_contact_heading'=>'Footer contact heading',
        'footer_privacy_label'=>'Privacy link label','footer_guides_label'=>'Guides link label',
        'footer_companies_label'=>'Company comparison link label'];
    $navigation=PRC_Bilingual_Form::navigation();
    foreach ($labels as $key=>$label) {
        $setting='prc_bilingual_navigation['.$key.']';
        $customizer->add_setting($setting,['type'=>'option','capability'=>'manage_options','default'=>$navigation[$key],
            'sanitize_callback'=>$key==='contact_email' ? 'sanitize_email' : 'sanitize_text_field']);
        $customizer->add_control($setting,['section'=>'prc_english_site','label'=>$label,'type'=>$key==='contact_email' ? 'email' : 'text']);
    }
    $customizer->add_section('prc_hebrew_site',['title'=>'PRC — עברית','priority'=>161]);
    $hebrew=PRC_Bilingual_Form::navigation(false);
    foreach ($labels as $key=>$label) {
        if (in_array($key,['brand','contact_email','phone'],true)) continue;
        $setting='prc_bilingual_navigation_he['.$key.']';
        $customizer->add_setting($setting,['type'=>'option','capability'=>'manage_options','default'=>$hebrew[$key],
            'sanitize_callback'=>'sanitize_text_field']);
        $customizer->add_control($setting,['section'=>'prc_hebrew_site','label'=>$label,'type'=>'text']);
    }
});

add_action('wp_abilities_api_categories_init', function () {
    wp_register_ability_category('prc', ['label'=>'PRC rental forms','description'=>'Rental form checks']);
});
add_action('wp_abilities_api_init', function () {
    wp_register_ability('prc-bilingual/health', [
        'label'=>'Check bilingual rental form',
        'description'=>'Admin-only checks of English rendering and saved language. Creates and removes one synthetic private request; sends no mail.',
        'category'=>'prc',
        'input_schema'=>['type'=>'object'],
        'permission_callback'=>function () { return current_user_can('manage_options'); },
        'execute_callback'=>['PRC_Bilingual_Form','health'],
        'meta'=>['show_in_rest'=>true,'mcp'=>['public'=>true,'type'=>'tool'],
            'annotations'=>['readOnlyHint'=>false,'destructiveHint'=>false,'idempotentHint'=>true]],
    ]);
});
