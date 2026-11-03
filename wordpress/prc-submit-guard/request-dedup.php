<?php
defined('ABSPATH') || exit;

final class PRC_Request_Dedup {
    const WINDOW_SECONDS = 600;

    public static function fingerprint(array $data) {
        ksort($data);
        foreach ($data as $key => &$value) {
            if (is_array($value)) {
                sort($value, SORT_STRING);
            } elseif ($key === 'email') {
                $value = strtolower(trim($value));
            }
        }
        unset($value);
        return hash('sha256', wp_json_encode($data));
    }

    public static function save(array $data, callable $create) {
        global $wpdb;
        $fingerprint = self::fingerprint($data);
        // A database lock serializes simultaneous requests, including separate tabs.
        $lock = 'prc_' . substr(hash('sha256', $wpdb->prefix . $fingerprint), 0, 56);
        if ((string) $wpdb->get_var($wpdb->prepare('SELECT GET_LOCK(%s, %d)', $lock, 10)) !== '1') {
            return new WP_Error('save_failed', 'Request storage is busy. Please retry.');
        }
        try {
            $ids = get_posts([
                'post_type' => 'prc_request',
                'post_status' => 'publish',
                'posts_per_page' => 1,
                'fields' => 'ids',
                'meta_key' => '_prc_submission_fingerprint',
                'meta_value' => $fingerprint,
                'date_query' => [[
                    'after' => wp_date('Y-m-d H:i:s', time() - self::WINDOW_SECONDS),
                    'inclusive' => true,
                ]],
            ]);
            if ($ids) return ['post_id' => (int) $ids[0], 'created' => false];
            $post_id = $create($fingerprint);
            if (is_wp_error($post_id) || !$post_id) return $post_id;
            return ['post_id' => (int) $post_id, 'created' => true];
        } finally {
            $wpdb->get_var($wpdb->prepare('SELECT RELEASE_LOCK(%s)', $lock));
        }
    }
}
