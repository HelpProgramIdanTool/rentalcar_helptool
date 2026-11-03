<?php
// Run only through the private, authenticated temporary QA wrapper.
if (!defined('PRC_PRIVATE_QA')) exit;
define('DISABLE_WP_CRON', true);
require __DIR__ . '/wp-load.php';

$marker = 'PRC-QA-' . bin2hex(random_bytes(12));
$created = [];
$mail_count = 0;
$active = false;
class PRC_QA_Redirect extends RuntimeException {}
function prc_qa_assert($value, $message) {
    if (!$value) throw new RuntimeException($message);
}
add_filter('pre_wp_mail', function ($result, $atts) use (&$mail_count) {
    $mail_count++;
    return true; // Nothing from this QA request reaches SMTP.
}, PHP_INT_MAX, 2);
add_filter('wp_redirect', function ($location) use (&$active) {
    if ($active) throw new PRC_QA_Redirect($location);
    return $location;
}, PHP_INT_MAX, 1);
add_action('wp_after_insert_post', function ($id, $post, $update) use (&$created, $marker) {
    if (!$update && $post->post_type === 'prc_request' && strpos($post->post_title, $marker) !== false) {
        $created[] = (int) $id;
    }
}, 10, 3);

$handler = (new ReflectionClass('Poland_Car_Request_Form'))->newInstanceWithoutConstructor();
$post = [
    'poland_car_request_nonce' => wp_create_nonce('poland_car_request_submit'),
    'full_name' => $marker,
    'email' => 'qa@example.test',
    'phone' => '', 'driver_age' => 'yes',
    'pickup_city' => 'TEST', 'pickup_place' => 'TEST',
    'pickup_date' => wp_date('Y-m-d', time() + 30 * DAY_IN_SECONDS),
    'pickup_time' => '12:00',
    'dropoff_city' => 'TEST', 'dropoff_place' => 'TEST',
    'dropoff_date' => wp_date('Y-m-d', time() + 32 * DAY_IN_SECONDS),
    'dropoff_time' => '12:00',
    'passengers' => '2', 'luggage' => '1', 'transmission' => 'TEST',
    'abroad' => 'no', 'confirm' => 'כן',
    'car_group' => ['TEST-B', 'TEST-A'],
];
$run = function ($data) use ($handler, &$active) {
    $_POST = $data;
    $_SERVER['REQUEST_METHOD'] = 'POST';
    // QA must not consume a real visitor's rate-limit allowance.
    unset($_SERVER['REMOTE_ADDR']);
    $active = true;
    try {
        $handler->handle_submit();
        throw new RuntimeException('Expected redirect');
    } catch (PRC_QA_Redirect $e) {
        parse_str(parse_url($e->getMessage(), PHP_URL_QUERY), $query);
        return $query;
    } finally {
        $active = false;
    }
};

$report = [];
try {
    $a = $run($post);
    $b = $run($post);
    $post['car_group'] = array_reverse($post['car_group']);
    $c = $run($post);
    prc_qa_assert($a['prc_status'] === 'success', 'First request failed: ' . wp_json_encode($a));
    prc_qa_assert($a['prc_id'] === $b['prc_id'] && $a['prc_id'] === $c['prc_id'], 'Repeated request got a new number');
    prc_qa_assert(count($created) === 1 && $mail_count === 1, 'Repeated request created extra post or email');
    $post['notes'] = 'TEST changed customer wishes';
    $changed = $run($post);
    prc_qa_assert($changed['prc_id'] !== $a['prc_id'], 'Changed request was lost');
    prc_qa_assert(count($created) === 2 && $mail_count === 2, 'Changed request was not sent once');
    $post['email'] = 'invalid';
    $invalid = $run($post);
    prc_qa_assert($invalid['prc_status'] === 'error', 'Invalid data was accepted');
    prc_qa_assert(count($created) === 2 && $mail_count === 2, 'Invalid data created a post or email');
    if (!empty($invalid['prc_restore'])) delete_transient('prc_restore_' . $invalid['prc_restore']);
    $report = ['ok'=>true, 'repeat_requests'=>3, 'unique_request_created'=>1,
        'repeat_email_attempts'=>1, 'changed_request_accepted'=>true,
        'invalid_request_blocked'=>true, 'smtp_messages_sent'=>0];
} finally {
    foreach ($created as $id) {
        if (get_post_type($id) === 'prc_request' && get_post_meta($id, '_prc_full_name', true) === $marker) {
            wp_clear_scheduled_hook('prc_retry_request_email', [$id]);
            wp_delete_post($id, true);
        }
    }
}
$report['synthetic_posts_removed'] = count($created);
header('Content-Type: application/json');
echo wp_json_encode($report);
