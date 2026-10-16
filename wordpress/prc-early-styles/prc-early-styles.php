<?php
/**
 * Plugin Name: PRC Early Styles
 * Description: Moves the existing homepage Divi layout styles into the document head without modifying their contents.
 * Version: 1.0.0
 */
defined('ABSPATH') || exit;

function prc_early_styles_move($html) {
    // Change only a complete HTML document, with exactly one matching Divi layout style.
    $pattern = '~<style\b[^>]*\bid=["\']et-builder-module-design-[^"\']+-deferred-[^"\']+-cached-inline-styles["\'][^>]*>.*?</style>~is';
    if (stripos($html, '</head>') === false || stripos($html, '</body>') === false
        || preg_match_all($pattern, $html, $matches, PREG_OFFSET_CAPTURE) !== 1) {
        return $html;
    }
    $style = $matches[0][0][0];
    $offset = $matches[0][0][1];
    $head_end = stripos($html, '</head>');
    if ($offset < $head_end) {
        return $html;
    }
    // Keep the exact style element, including its ID and all media queries.
    $without_style = substr($html, 0, $offset) . substr($html, $offset + strlen($style));
    return substr($without_style, 0, $head_end) . $style
        . substr($without_style, $head_end);
}

add_action('template_redirect', function () {
    if (is_admin() || !is_front_page() || is_preview() || is_feed()
        || isset($_GET['et_fb']) || isset($_GET['et_bfb']) || is_user_logged_in()) {
        return;
    }
    ob_start('prc_early_styles_move');
}, 0);
