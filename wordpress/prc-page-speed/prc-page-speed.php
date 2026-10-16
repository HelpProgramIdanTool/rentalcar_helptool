<?php
/**
 * Plugin Name: PRC Page Speed
 * Description: Homepage background preload and click-to-load YouTube, without changing stored pages.
 * Version: 1.0.0
 */
defined('ABSPATH') || exit;

function prc_speed_homepage() {
    return !is_admin() && is_front_page() && !is_preview()
        && !isset($_GET['et_fb']) && !isset($_GET['et_bfb']);
}

add_action('wp_head', function () {
    if (!prc_speed_homepage()) {
        return;
    }
    // Use the actual first Divi section's image, rather than keeping a second copy of its URL.
    $page = get_post(get_queried_object_id());
    if ($page && preg_match('/\[et_pb_section\b[^\]]*\bbackground_image="([^"]+)"/', $page->post_content, $match)) {
        $image = esc_url(html_entity_decode($match[1], ENT_QUOTES, 'UTF-8'));
        if ($image) {
            echo '<link rel="preload" as="image" fetchpriority="high" href="' . $image . '">' . "\n";
        }
    }
}, 1);

add_action('wp_enqueue_scripts', function () {
    if (prc_speed_homepage()) {
        wp_enqueue_style('prc-page-speed', plugins_url('video.css', __FILE__), array(), '1.0.0');
        wp_enqueue_script('prc-page-speed', plugins_url('video.js', __FILE__), array(), '1.0.0', true);
    }
});

function prc_speed_video_placeholder($html) {
    if (!prc_speed_homepage() || !is_string($html)) {
        return $html;
    }
    return preg_replace_callback('~<iframe\b[^>]*>\s*</iframe>~i', function ($match) {
        $tag = new WP_HTML_Tag_Processor($match[0]);
        if (!$tag->next_tag('iframe')) {
            return $match[0];
        }
        $src = $tag->get_attribute('src');
        if (!is_string($src)) {
            return $match[0];
        }
        $host = strtolower((string) wp_parse_url($src, PHP_URL_HOST));
        $path = (string) wp_parse_url($src, PHP_URL_PATH);
        if (!in_array($host, array('www.youtube.com', 'youtube.com', 'www.youtube-nocookie.com', 'youtube-nocookie.com'), true)
            || !preg_match('~^/embed/([a-zA-Z0-9_-]{11})$~', $path, $video)) {
            return $match[0];
        }
        $title = (string) $tag->get_attribute('title');
        $width = max(1, (int) $tag->get_attribute('width'));
        $height = max(1, (int) $tag->get_attribute('height'));
        if ($width === 1 || $height === 1) {
            $width = 16;
            $height = 9;
        }
        // A real link remains usable with JavaScript disabled. No player connects before a click.
        return '<div class="prc-video" style="aspect-ratio:' . $width . '/' . $height . '">'
            . '<a class="prc-video-link" href="https://www.youtube.com/watch?v=' . esc_attr($video[1]) . '"'
            . ' data-embed="' . esc_url($src) . '" aria-label="' . esc_attr($title) . '">'
            . '<img src="https://i.ytimg.com/vi/' . esc_attr($video[1]) . '/hqdefault.jpg"'
            . ' alt="' . esc_attr($title) . '" width="480" height="360" loading="lazy" decoding="async">'
            . '<span class="prc-video-play" aria-hidden="true">&#9654;</span></a></div>';
    }, $html);
}

add_filter('the_content', 'prc_speed_video_placeholder', 999);
add_filter('embed_oembed_html', 'prc_speed_video_placeholder', 999);
add_filter('oembed_result', 'prc_speed_video_placeholder', 999);
