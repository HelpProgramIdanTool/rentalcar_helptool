<?php
/**
 * Plugin Name: PRC Submit Guard
 * Description: Prevents repeated browser submissions of the rental request form.
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
    wp_enqueue_script('prc-submit-guard', plugins_url('submit-guard.js', __FILE__), array('poland-car-request-form'), '1.0.0', true);
});
