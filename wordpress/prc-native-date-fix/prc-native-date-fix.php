<?php
/**
 * Plugin Name: PRC Native Date Fix
 * Description: Uses directly interactive native date inputs in the rental request form.
 * Version: 1.0.0
 */
defined('ABSPATH') || exit;
add_action('wp_enqueue_scripts', function () {
    if (!is_singular() || is_preview() || isset($_GET['et_fb'])) {
        return;
    }
    $post = get_post();
    if (!$post || !has_shortcode($post->post_content, 'poland_car_request_form')) {
        return;
    }
    wp_enqueue_style('prc-native-date-fix', plugins_url('dates.css', __FILE__), array('poland-car-request-form'), '1.0.0');
    wp_enqueue_script('prc-native-date-fix', plugins_url('dates.js', __FILE__), array('poland-car-request-form'), '1.0.0', true);
});
