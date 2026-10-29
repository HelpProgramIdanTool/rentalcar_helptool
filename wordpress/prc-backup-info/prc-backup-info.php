<?php
/**
 * Plugin Name: PRC Backup Information
 * Description: Public information, privacy and terms for RentalCar Backups.
 * Version: 1.0.0
 */
defined('ABSPATH') || exit;

function prc_backup_documents() {
    return array(
        'rentalcar-backups' => array('RentalCar Backups', 'about.html'),
        'rentalcar-backups-privacy' => array('RentalCar Backups — Privacy Policy', 'privacy.html'),
        'rentalcar-backups-terms' => array('RentalCar Backups — Terms of Use', 'terms.html'),
    );
}

function prc_backup_create_pages() {
    if (get_option('prc_backup_info_created') === '1.0.0') {
        return;
    }
    $complete = true;
    foreach (prc_backup_documents() as $slug => $document) {
        $existing = get_page_by_path($slug, OBJECT, 'page');
        if ($existing) {
            // Never overwrite unrelated pages or an operator's edits.
            if (get_post_meta($existing->ID, '_prc_backup_info', true) !== $document[1]) {
                $complete = false;
            }
            continue;
        }
        $id = wp_insert_post(array(
            'post_type' => 'page', 'post_status' => 'publish',
            'post_title' => $document[0], 'post_name' => $slug,
            'post_content' => file_get_contents(__DIR__ . '/' . $document[1]),
            'comment_status' => 'closed', 'ping_status' => 'closed',
            'meta_input' => array('_prc_backup_info' => $document[1]),
        ), true);
        if (is_wp_error($id) || !$id) {
            $complete = false;
        }
    }
    if ($complete) {
        update_option('prc_backup_info_created', '1.0.0', false);
    }
}
register_activation_hook(__FILE__, 'prc_backup_create_pages');
add_action('init', 'prc_backup_create_pages');

add_action('template_redirect', function () {
    if (!is_page() || is_preview()) {
        return;
    }
    $post = get_queried_object();
    $documents = prc_backup_documents();
    if (!$post || !isset($documents[$post->post_name])) {
        return;
    }
    $document = $documents[$post->post_name];
    if (get_post_meta($post->ID, '_prc_backup_info', true) !== $document[1]) {
        return;
    }
    // Standalone public documents: no theme scripts, login or backup access.
    status_header(200);
    header('Content-Type: text/html; charset=UTF-8');
    header('X-Content-Type-Options: nosniff');
    header("Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'");
    echo '<!doctype html><html lang="en" dir="ltr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">';
    echo '<title>' . esc_html($document[0]) . '</title>';
    echo '<style>body{margin:0;background:#f5f7fa;color:#17283d;font:18px/1.65 system-ui,sans-serif}main{max-width:850px;margin:36px auto;padding:32px;background:white;border-radius:14px}a{color:#1454ac}nav{display:flex;flex-wrap:wrap;gap:18px}h1{line-height:1.2}h2{margin-top:32px;font-size:1.25em}.date{color:#536171;font-size:.9em}@media(max-width:650px){main{margin:0;padding:24px;border-radius:0}}</style></head><body><main>';
    echo '<nav aria-label="Backup information"><a href="/rentalcar-backups/">About</a><a href="/rentalcar-backups-privacy/">Privacy policy</a><a href="/rentalcar-backups-terms/">Terms of use</a></nav>';
    echo '<article>' . $post->post_content . '</article>';
    echo '<footer><p><a href="https://poland-rent-car.com/">Poland Rent a Car</a> · <a href="mailto:idan.poland@gmail.com">Contact the operator</a></p></footer></main></body></html>';
    exit;
}, 0);
