<?php
/** Reversible site-wide header/footer presentation; original Divi layouts remain stored. */
defined('ABSPATH') || exit;

final class Trip_Site_Shell {
    const VERSION = '1.0.1';
    private static $header_printed = false;
    private static $footer_printed = false;

    public static function config() {
        $defaults = json_decode(file_get_contents(__DIR__.'/site-shell.json'), true);
        return array_merge($defaults, (array)get_option('trip_site_shell', []));
    }

    public static function enabled() {
        return !is_admin() && !is_feed() && !is_embed() &&
            wp_parse_url(home_url(), PHP_URL_HOST) === 'trip2poland.co.il' &&
            !isset($_GET['et_fb']) && !empty(self::config()['enabled']);
    }

    public static function items($id) {
        return array_values(array_filter(wp_get_nav_menu_items((int)$id) ?: [], function($item) {
            return $item->post_status === 'publish';
        }));
    }

    public static function links($items, $parent = 0, $depth = 0, $prefix = 'trip-nav') {
        if ($depth > 5) return '';
        $html = '';
        foreach ($items as $item) {
            if ((int)$item->menu_item_parent !== (int)$parent) continue;
            $children = self::links($items, $item->ID, $depth + 1, $prefix);
            $submenu = $prefix.'-children-'.$item->ID;
            $active = untrailingslashit($item->url) === untrailingslashit(get_permalink()) ? ' aria-current="page"' : '';
            $html .= '<li class="trip-nav-item'.($children ? ' trip-has-children' : '').'">';
            $html .= '<div class="trip-nav-link"><a href="'.esc_url($item->url).'"'.$active.'>'.esc_html($item->title).'</a>';
            if ($children) $html .= '<button type="button" class="trip-submenu-toggle" aria-expanded="false" aria-controls="'.esc_attr($submenu).'" aria-label="'.esc_attr('פתיחת תפריט: '.$item->title).'">⌄</button>';
            $html .= '</div>';
            if ($children) $html .= '<ul id="'.esc_attr($submenu).'" class="trip-submenu">'.$children.'</ul>';
            $html .= '</li>';
        }
        return $html;
    }

    private static function flat_links($items, $roots_only = false) {
        $html = ''; $seen = [];
        foreach ($items as $item) {
            if (($roots_only && (int)$item->menu_item_parent) || isset($seen[$item->url])) continue;
            $seen[$item->url] = true;
            $html .= '<li><a href="'.esc_url($item->url).'">'.esc_html($item->title).'</a></li>';
        }
        return $html;
    }

    public static function header() {
        if (!self::enabled() || self::$header_printed) return;
        self::$header_printed = true;
        $c = self::config();
        ?>
        <header class="trip-shell trip-shell-header" id="trip-shell-header" lang="he" dir="rtl">
          <div class="trip-contact-strip"><div class="trip-shell-inner">
            <span class="trip-tagline"><?php echo esc_html($c['tagline']); ?></span>
            <div class="trip-contact-links"><a dir="ltr" href="tel:<?php echo esc_attr($c['phone']); ?>"><?php echo esc_html($c['phone_display']); ?></a><a dir="ltr" href="mailto:<?php echo esc_attr($c['email']); ?>"><?php echo esc_html($c['email']); ?></a></div>
          </div></div>
          <div class="trip-main-bar trip-shell-inner">
            <a class="trip-brand" href="<?php echo esc_url(home_url('/')); ?>" aria-label="<?php echo esc_attr($c['brand'].' — עמוד הבית'); ?>"><img src="<?php echo esc_url(home_url($c['logo_path'])); ?>" width="376" height="141" alt="<?php echo esc_attr($c['brand']); ?>"></a>
            <button class="trip-menu-toggle" type="button" aria-expanded="false" aria-controls="trip-primary-navigation"><span aria-hidden="true">☰</span> <?php echo esc_html($c['menu_label']); ?></button>
            <nav id="trip-primary-navigation" class="trip-primary-navigation" aria-label="ניווט ראשי"><ul class="trip-primary-list"><?php echo self::links(self::items($c['primary_menu'])); ?></ul></nav>
            <a class="trip-contact-button" href="<?php echo esc_url(home_url($c['contact_path'])); ?>"><?php echo esc_html($c['contact_label']); ?></a>
          </div>
          <nav class="trip-services-strip" aria-label="<?php echo esc_attr($c['services_label']); ?>"><ul class="trip-shell-inner"><?php echo self::flat_links(self::items($c['services_menu']), true); ?></ul></nav>
        </header>
        <?php
    }

    public static function footer() {
        if (!self::enabled() || self::$footer_printed) return;
        self::$footer_printed = true;
        $c = self::config();
        ?>
        <footer class="trip-shell trip-shell-footer" id="trip-shell-footer" lang="he" dir="rtl"><div class="trip-shell-inner trip-footer-grid">
          <div class="trip-footer-brand"><a class="trip-brand" href="<?php echo esc_url(home_url('/')); ?>"><img src="<?php echo esc_url(home_url($c['logo_path'])); ?>" width="376" height="141" alt="<?php echo esc_attr($c['brand']); ?>" loading="lazy"></a><p><?php echo esc_html($c['description']); ?></p></div>
          <nav aria-label="שירותים בתחתית האתר"><h2><?php echo esc_html($c['services_label']); ?></h2><ul><?php echo self::flat_links(self::items($c['services_menu']), true); ?></ul></nav>
          <nav aria-label="מידע וטיולים בתחתית האתר"><h2><?php echo esc_html($c['discover_label']); ?></h2><ul><?php echo self::flat_links(self::items($c['primary_menu']), true); ?></ul></nav>
          <div class="trip-footer-contact"><h2><?php echo esc_html($c['follow_label']); ?></h2><a dir="ltr" href="tel:<?php echo esc_attr($c['phone']); ?>"><?php echo esc_html($c['phone_display']); ?></a><a dir="ltr" href="mailto:<?php echo esc_attr($c['email']); ?>"><?php echo esc_html($c['email']); ?></a><a class="trip-whatsapp" href="<?php echo esc_url('https://wa.me/'.preg_replace('/\D/', '', $c['phone'])); ?>">WhatsApp</a><div class="trip-social-links"><?php foreach ($c['social'] as $social) : ?><a href="<?php echo esc_url($social['url']); ?>" target="_blank" rel="noopener"><?php echo esc_html($social['label']); ?></a><?php endforeach; ?></div></div>
        </div><div class="trip-shell-inner trip-footer-bottom"><span dir="ltr">© <?php echo esc_html(wp_date('Y').' '.$c['brand']); ?></span><a href="<?php echo esc_url(home_url($c['contact_path'])); ?>"><?php echo esc_html($c['contact_label']); ?></a></div></footer>
        <?php
    }
}

add_filter('body_class', function($classes) {
    if (Trip_Site_Shell::enabled()) $classes[] = 'trip-shell-theme';
    return $classes;
});
add_action('wp_enqueue_scripts', function() {
    if (!Trip_Site_Shell::enabled()) return;
    wp_enqueue_style('trip-site-shell', plugins_url('site-shell.css', __FILE__), [], Trip_Site_Shell::VERSION);
    wp_enqueue_script('trip-site-shell', plugins_url('site-shell.js', __FILE__), [], Trip_Site_Shell::VERSION, true);
}, 30);
// Divi renders wp_body_open during a discarded layout buffer on this site.
// Emit once with the footer; site-shell.js moves the header above page-container.
add_action('get_footer', ['Trip_Site_Shell', 'footer']);
add_action('wp_footer', function() {
    Trip_Site_Shell::header(); // Fallback for templates missing wp_body_open.
    Trip_Site_Shell::footer();
}, 5);
add_action('init', function() {
    if (!Trip_Site_Shell::enabled() || get_option('trip_site_shell_version') === Trip_Site_Shell::VERSION) return;
    add_option('trip_site_shell_original_menus', get_theme_mod('nav_menu_locations'), '', false);
    update_option('trip_site_shell_version', Trip_Site_Shell::VERSION, false);
    do_action('litespeed_purge_all');
});
add_action('customize_register', function($customizer) {
    $customizer->add_section('trip_site_shell', ['title'=>'Trip2Poland — שורת ניווט ופרטי קשר','priority'=>165]);
    foreach (['brand','tagline','description','phone_display','phone','email'] as $key) {
        $customizer->add_setting('trip_site_shell['.$key.']', ['type'=>'option','capability'=>'manage_options',
            'default'=>Trip_Site_Shell::config()[$key], 'sanitize_callback'=>$key === 'email' ? 'sanitize_email' : 'sanitize_text_field']);
        $customizer->add_control('trip_site_shell['.$key.']', ['section'=>'trip_site_shell','label'=>$key,'type'=>'text']);
    }
});
