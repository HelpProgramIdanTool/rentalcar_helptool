<?php
/**
 * Plugin Name: Trip2Poland Rental Page
 * Description: Responsive Hebrew rental car request form with request storage, Gmail delivery, automatic retries, failed-email recovery and strict rental date validation.
 * Version: 1.6.2
 * Author: Idan / ChatGPT
 * Text Domain: poland-car-request-form
 */

if (!defined('ABSPATH')) {
    exit;
}

require_once __DIR__ . '/request-dedup.php';

final class Trip_Car_Request_Form {

    const VERSION = '1.6.2';
    const SHORTCODE = 'trip_car_request_form';
    const NONCE_ACTION = 'trip_car_request_submit';
    const NONCE_FIELD = 'trip_car_request_nonce';
    private function recipient() {
        if (!class_exists('CPCFF_MAIN')) return '';
        $form = CPCFF_MAIN::instance()->get_form(18);
        if (!$form) return '';
        $raw = $form->get_option('fp_destination_emails', '');
        $emails = array_filter(array_map('sanitize_email', preg_split('/[,;\s]+/', $raw)));
        return implode(',', $emails);
    }
    const POST_TYPE = 'trip_request';
    const RATE_LIMIT_MAX = 10;
    const RATE_LIMIT_WINDOW = 15 * MINUTE_IN_SECONDS;
    const MAX_EMAIL_ATTEMPTS = 3;

    private $last_mail_error = '';

    public function __construct() {
        add_action('wp_enqueue_scripts', function () { if (is_page(85)) $this->page_assets(); });
        add_shortcode(self::SHORTCODE, [$this, 'render_shortcode']);


        add_action('admin_post_trip_car_request_submit', [$this, 'handle_submit']);
        add_action('admin_post_nopriv_trip_car_request_submit', [$this, 'handle_submit']);

        add_action('init', [$this, 'register_request_post_type']);
        add_filter('manage_' . self::POST_TYPE . '_posts_columns', [$this, 'admin_columns']);
        add_action('manage_' . self::POST_TYPE . '_posts_custom_column', [$this, 'admin_column_content'], 10, 2);
        add_filter('post_row_actions', [$this, 'request_row_actions'], 10, 2);
        add_action('add_meta_boxes_' . self::POST_TYPE, [$this, 'add_request_meta_box']);

        add_action('wp_mail_failed', [$this, 'capture_mail_error']);
        add_action('trip_retry_request_email', [$this, 'retry_request_email'], 10, 1);
        add_action('admin_post_trip_resend_request', [$this, 'handle_manual_resend']);
        add_action('admin_post_trip_resend_all_failed', [$this, 'handle_resend_all_failed']);
        add_action('admin_notices', [$this, 'admin_notices']);
    }

    public function register_request_post_type() {
        $labels = [
            'name'               => 'Car Requests',
            'singular_name'      => 'Car Request',
            'menu_name'          => 'Car Requests',
            'add_new'            => 'Add Request',
            'add_new_item'       => 'Add Request',
            'edit_item'          => 'View Request',
            'new_item'           => 'New Request',
            'view_item'          => 'View Request',
            'search_items'       => 'Search Requests',
            'not_found'          => 'No requests found',
            'not_found_in_trash' => 'No requests found in Trash',
        ];

        register_post_type(self::POST_TYPE, [
            'labels'              => $labels,
            'public'              => false,
            'show_ui'             => true,
            'show_in_menu'        => true,
            'show_in_rest'        => false,
            'menu_icon'           => 'dashicons-car',
            'supports'            => ['title'],
            'capability_type'     => 'post',
            'map_meta_cap'        => true,
            'has_archive'         => false,
            'rewrite'             => false,
            'exclude_from_search' => true,
        ]);
    }

    public function page_assets() {
        $base = set_url_scheme(plugin_dir_url(__FILE__), 'https');
        wp_enqueue_style('trip-page', $base . 'page.css', [], '7.2');
        wp_enqueue_script('trip-validation', $base . 'validation.js', [], '7.2', true);
        wp_enqueue_script('trip-page', $base . 'page.js', ['trip-validation'], '7.2', true);
        wp_add_inline_script('trip-page', 'const TRIP_CONFIG=' . wp_json_encode([
            'nonce'=>wp_create_nonce(self::NONCE_ACTION), 'started'=>time(),
            'restore'=>$this->get_restore_data_from_request(), 'action'=>set_url_scheme(admin_url('admin-post.php'), 'https')]) . ';', 'before');
    }

    public function render_shortcode($atts = []) {
        $base = set_url_scheme(plugin_dir_url(__FILE__), 'https');
        $html = file_get_contents(__DIR__ . '/page.html');
        $html = str_replace('trip-assets/', esc_url($base), $html);
        $message = '';
        $receipt = !empty($_GET['trip_receipt']) ? get_transient('trip_receipt_' . sanitize_key(wp_unslash($_GET['trip_receipt']))) : false;
        if (is_array($receipt)) {
            $sent = $receipt['mail_status'] === 'sent';
            $title = $sent ? 'הבקשה נשלחה בהצלחה' : 'הבקשה התקבלה ונשמרה';
            $detail = $sent ? 'הפרטים נשמרו והודעת הדוא״ל נשלחה אלינו. תודה! נחזור אליכם עם הצעה.' : 'הפרטים נשמרו. משלוח הדוא״ל מתעכב והמערכת תנסה שוב. אין צורך לשלוח את הטופס שוב.';
            return '<section id="tripStatusMessage" class="trip-receipt" role="status" tabindex="-1" dir="rtl"><h1>' . esc_html($title) . '</h1><p>' . esc_html($detail) . '</p><p>מספר פנייה: <strong>' . esc_html($receipt['id']) . '</strong></p><a href="' . esc_url(home_url('/rent-a-car-in-poland/')) . '">חזרה לעמוד השכרת הרכב</a></section>';
        }
        if (isset($_GET['trip_status']) && $_GET['trip_status'] === 'error') {
            $code = isset($_GET['trip_error']) ? sanitize_key(wp_unslash($_GET['trip_error'])) : '';
            $message = '<div id="tripStatusMessage" class="trip-form-error" role="alert" tabindex="-1" dir="rtl">' . esc_html($this->front_error_message($code)) . '</div>';
        }
        return $message . $html;
    }

    public function handle_submit() {
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            wp_safe_redirect(home_url('/'));
            exit;
        }

        if (
            !isset($_POST[self::NONCE_FIELD]) ||
            !wp_verify_nonce(
                sanitize_text_field(wp_unslash($_POST[self::NONCE_FIELD])),
                self::NONCE_ACTION
            )
        ) {
            $this->redirect_with_status('error', '', 'security');
        }

        if ($this->is_probable_bot()) {
            $this->redirect_with_status('success');
        }

        if (!$this->recipient()) { $this->redirect_with_status('error', '', 'recipient'); }
        $data = $this->collect_data();

        if ($this->is_rate_limited()) {
            $restore_token = $this->store_restore_data($data);
            $this->redirect_with_status('error', '', 'rate_limited', $restore_token);
        }

        $validation = $this->validate_and_normalize_data($data);

        if (is_wp_error($validation)) {
            $restore_token = $this->store_restore_data($data);
            $this->redirect_with_status('error', '', $validation->get_error_code(), $restore_token);
        }

        $data = $validation;
        $result = Trip_Request_Dedup::save($data, function ($fingerprint) use ($data) {
            return $this->save_request($this->generate_request_id(), $data, $fingerprint);
        });

        if (is_wp_error($result) || !$result) {
            $restore_token = $this->store_restore_data($data);
            $this->redirect_with_status('error', '', 'save_failed', $restore_token);
        }

        $post_id = $result['post_id'];
        $request_id = get_post_meta($post_id, '_trip_request_id', true);
        if ($result['created']) {
            $this->send_request_email($post_id);
        }
        $this->redirect_with_status('success', $request_id, '', '', get_post_meta($post_id, '_trip_email_status', true));
    }

    private function validate_and_normalize_data(array $data) {
        if (empty($data['full_name']) || empty($data['email']) || !is_email($data['email'])) {
            return new WP_Error('contact', 'Invalid contact data.');
        }

        $required = [
            'driver_age',
            'pickup_city',
            'pickup_place',
            'pickup_date',
            'pickup_time',
            'dropoff_city',
            'dropoff_place',
            'dropoff_date',
            'dropoff_time',
            'passengers',
            'transmission',
            'abroad',
            'confirm',
        ];

        foreach ($required as $key) {
            if (!isset($data[$key]) || $data[$key] === '') {
                return new WP_Error('required', 'Required field missing.');
            }
        }

        $pickup = $this->make_datetime($data['pickup_date'], $data['pickup_time']);
        $dropoff = $this->make_datetime($data['dropoff_date'], $data['dropoff_time']);

        if (!$pickup || !$dropoff) {
            return new WP_Error('datetime', 'Invalid date/time.');
        }

        $now = new DateTimeImmutable('now', new DateTimeZone('Europe/Warsaw'));

        if ($pickup <= $now) {
            return new WP_Error('pickup_past', 'Pickup is in the past.');
        }

        if ($dropoff <= $pickup) {
            return new WP_Error('dropoff_before_pickup', 'Drop-off must be after pickup.');
        }

        $passengers = (int) $data['passengers'];
        if ($passengers < 1 || $passengers > 9) {
            return new WP_Error('passengers', 'Invalid passenger count.');
        }

        if ($data['luggage'] !== '') {
            $luggage = (int) $data['luggage'];
            if ($luggage < 0) {
                return new WP_Error('luggage', 'Invalid luggage count.');
            }
        }

        if ($data['child_seat_count'] !== '') {
            $seat_count = (int) $data['child_seat_count'];
            if ($seat_count < 0) {
                return new WP_Error('child_seats', 'Invalid child seat count.');
            }
        }

        if ($data['confirm'] !== 'כן') {
            return new WP_Error('confirm', 'Confirmation missing.');
        }

        $data['pickup_date'] = $pickup->format('Y-m-d');
        $data['dropoff_date'] = $dropoff->format('Y-m-d');
        $data['pickup_time'] = $pickup->format('H:i');
        $data['dropoff_time'] = $dropoff->format('H:i');
        $data['rental_days'] = (string) $this->calculate_rental_days($pickup, $dropoff);

        return $data;
    }

    private function make_datetime($date, $time) {
        $date = trim((string) $date);
        $time = trim((string) $time);

        if (!preg_match('/^(?:[01]\d|2[0-3]):[0-5]\d$/', $time)) {
            return false;
        }

        $format = '';
        if (preg_match('/^\d{2}\/\d{2}\/\d{4}$/', $date)) {
            $format = '!d/m/Y H:i';
        } elseif (preg_match('/^\d{4}-\d{2}-\d{2}$/', $date)) {
            /* Legacy/restore compatibility. */
            $format = '!Y-m-d H:i';
        } else {
            return false;
        }

        $dt = DateTimeImmutable::createFromFormat($format, $date . ' ' . $time, new DateTimeZone('Europe/Warsaw'));
        $errors = DateTimeImmutable::getLastErrors();

        if ($dt === false) {
            return false;
        }

        if (is_array($errors) && ($errors['warning_count'] > 0 || $errors['error_count'] > 0)) {
            return false;
        }

        $expected = (strpos($format, 'd/m/Y') !== false)
            ? $dt->format('d/m/Y H:i')
            : $dt->format('Y-m-d H:i');

        if ($expected !== $date . ' ' . $time) {
            return false;
        }

        return $dt;
    }

    private function format_date_for_display($date) {
        if (!is_string($date) || $date === '') {
            return '';
        }

        if (preg_match('/^\d{4}-\d{2}-\d{2}$/', $date)) {
            $dt = DateTimeImmutable::createFromFormat('!Y-m-d', $date, new DateTimeZone('Europe/Warsaw'));
            $errors = DateTimeImmutable::getLastErrors();
            if ($dt && (!is_array($errors) || ($errors['warning_count'] === 0 && $errors['error_count'] === 0))) {
                return $dt->format('d/m/Y');
            }
        }

        if (preg_match('/^\d{2}\/\d{2}\/\d{4}$/', $date)) {
            return $date;
        }

        return $date;
    }

    private function calculate_rental_days(DateTimeImmutable $pickup, DateTimeImmutable $dropoff) {
        /*
         * Rental days are based on local wall-clock time, not DST-adjusted elapsed seconds.
         * This keeps 10:00 -> next day 10:00 equal to exactly 1 rental day even across
         * daylight-saving transitions.
         */
        $utc = new DateTimeZone('UTC');
        $pickup_wall = DateTimeImmutable::createFromFormat(
            '!Y-m-d H:i',
            $pickup->format('Y-m-d H:i'),
            $utc
        );
        $dropoff_wall = DateTimeImmutable::createFromFormat(
            '!Y-m-d H:i',
            $dropoff->format('Y-m-d H:i'),
            $utc
        );

        if (!$pickup_wall || !$dropoff_wall || $dropoff_wall <= $pickup_wall) {
            return 0;
        }

        $seconds = $dropoff_wall->getTimestamp() - $pickup_wall->getTimestamp();
        return max(1, (int) ceil($seconds / DAY_IN_SECONDS));
    }

    private function store_restore_data(array $data) {
        $token = strtolower(wp_generate_password(24, false, false));

        set_transient(
            'trip_restore_' . $token,
            $data,
            30 * MINUTE_IN_SECONDS
        );

        return $token;
    }

    private function get_restore_data_from_request() {
        if (empty($_GET['trip_restore'])) {
            return [];
        }

        $token = sanitize_key(wp_unslash($_GET['trip_restore']));

        if ($token === '') {
            return [];
        }

        $data = get_transient('trip_restore_' . $token);

        return is_array($data) ? $data : [];
    }

    private function front_error_message($code) {
        $messages = [
            'security'              => 'אירעה שגיאת אבטחה בטופס. נא לרענן את הדף ולנסות שוב.',
            'rate_limited'          => 'נשלחו יותר מדי בקשות בזמן קצר. נא להמתין מספר דקות ולנסות שוב.',
            'contact'               => 'נא לבדוק את השם ואת כתובת הדוא״ל ולנסות שוב.',
            'required'              => 'חסרים פרטים חובה בטופס. נא לעבור על השדות ולנסות שוב.',
            'datetime'              => 'אחד מתאריכי או משעות ההשכרה אינו תקין.',
            'pickup_past'           => 'מועד קבלת הרכב כבר עבר. יש לבחור תאריך ושעה עתידיים.',
            'dropoff_before_pickup' => 'מועד החזרת הרכב חייב להיות לאחר מועד קבלת הרכב.',
            'passengers'            => 'מספר הנוסעים חייב להיות בין 1 ל-9.',
            'luggage'               => 'מספר המזוודות אינו תקין.',
            'child_seats'           => 'מספר כיסאות הילדים / הבוסטרים אינו תקין.',
            'confirm'               => 'יש לאשר את נכונות הפרטים לפני שליחת הבקשה.',
            'save_failed'           => 'אירעה תקלה בשמירת הבקשה. נא לנסות שוב או ליצור איתנו קשר ישירות.',
        ];

        return isset($messages[$code])
            ? $messages[$code]
            : 'אירעה תקלה בשליחת הטופס. נא לבדוק את הפרטים ולנסות שוב.';
    }

    private function send_request_email($post_id) {
        $post_id = (int) $post_id;

        if (get_post_type($post_id) !== self::POST_TYPE) {
            return false;
        }

        $data = $this->get_saved_request_data($post_id);
        $request_id = get_post_meta($post_id, '_trip_request_id', true);

        if (empty($request_id)) {
            $request_id = 'TRIP-' . $post_id;
        }

        $attempts = (int) get_post_meta($post_id, '_trip_email_attempts', true);
        $attempts++;

        update_post_meta($post_id, '_trip_email_attempts', $attempts);
        update_post_meta($post_id, '_trip_email_last_attempt', current_time('mysql'));

        $this->last_mail_error = '';

        $subject = '[' . $request_id . '] בקשה חדשה להצעת מחיר להשכרת רכב בפולין';
        $body = $this->build_email_body($data, $request_id, $post_id);
        $headers = ['Content-Type: text/plain; charset=UTF-8'];

        if (!empty($data['email']) && is_email($data['email'])) {
            $headers[] = 'Reply-To: ' . $this->safe_reply_name($data['full_name']) . ' <' . $data['email'] . '>';
        }

        $sent = wp_mail($this->recipient(), $subject, $body, $headers);

        if ($sent) {
            update_post_meta($post_id, '_trip_email_status', 'sent');
            update_post_meta($post_id, '_trip_email_sent_at', current_time('mysql'));
            delete_post_meta($post_id, '_trip_email_error');
            wp_clear_scheduled_hook('trip_retry_request_email', [$post_id]);
            return true;
        }

        update_post_meta($post_id, '_trip_email_status', 'failed');
        update_post_meta(
            $post_id,
            '_trip_email_error',
            $this->last_mail_error !== '' ? $this->last_mail_error : 'wp_mail() returned false.'
        );

        if ($attempts < self::MAX_EMAIL_ATTEMPTS) {
            $this->schedule_retry($post_id, $attempts);
        }

        return false;
    }

    private function schedule_retry($post_id, $attempts) {
        if ((int) $attempts === 1) {
            $delay = 10 * MINUTE_IN_SECONDS;
        } elseif ((int) $attempts === 2) {
            $delay = 30 * MINUTE_IN_SECONDS;
        } else {
            return;
        }

        if (wp_next_scheduled('trip_retry_request_email', [(int) $post_id])) {
            return;
        }

        wp_schedule_single_event(
            time() + $delay,
            'trip_retry_request_email',
            [(int) $post_id]
        );
    }

    public function retry_request_email($post_id) {
        $post_id = (int) $post_id;

        if (get_post_type($post_id) !== self::POST_TYPE) {
            return;
        }

        $status = get_post_meta($post_id, '_trip_email_status', true);
        if ($status === 'sent') {
            return;
        }

        $attempts = (int) get_post_meta($post_id, '_trip_email_attempts', true);
        if ($attempts >= self::MAX_EMAIL_ATTEMPTS) {
            return;
        }

        $this->send_request_email($post_id);
    }

    public function handle_manual_resend() {
        if (!current_user_can('edit_posts')) {
            wp_die('You are not allowed to resend emails.');
        }

        $post_id = isset($_GET['post_id']) ? (int) $_GET['post_id'] : 0;

        if (!$post_id || get_post_type($post_id) !== self::POST_TYPE) {
            wp_die('Invalid request.');
        }

        check_admin_referer('trip_resend_request_' . $post_id);

        wp_clear_scheduled_hook('trip_retry_request_email', [$post_id]);
        update_post_meta($post_id, '_trip_email_attempts', 0);

        $sent = $this->send_request_email($post_id);

        $redirect = add_query_arg(
            [
                'post_type' => self::POST_TYPE,
                'trip_resend_single' => $sent ? 'sent' : 'failed',
            ],
            admin_url('edit.php')
        );

        wp_safe_redirect($redirect);
        exit;
    }

    public function handle_resend_all_failed() {
        if (!current_user_can('edit_posts')) {
            wp_die('You are not allowed to resend emails.');
        }

        check_admin_referer('trip_resend_all_failed');

        $failed_ids = get_posts([
            'post_type'      => self::POST_TYPE,
            'post_status'    => 'publish',
            'posts_per_page' => -1,
            'fields'         => 'ids',
            'orderby'        => 'date',
            'order'          => 'ASC',
            'meta_query'     => [
                [
                    'key'   => '_trip_email_status',
                    'value' => 'failed',
                ],
            ],
        ]);

        $sent_count = 0;
        $failed_count = 0;

        foreach ($failed_ids as $post_id) {
            $post_id = (int) $post_id;
            wp_clear_scheduled_hook('trip_retry_request_email', [$post_id]);
            update_post_meta($post_id, '_trip_email_attempts', 0);

            if ($this->send_request_email($post_id)) {
                $sent_count++;
            } else {
                $failed_count++;
            }
        }

        $redirect = add_query_arg(
            [
                'post_type'       => self::POST_TYPE,
                'trip_bulk_sent'   => $sent_count,
                'trip_bulk_failed' => $failed_count,
            ],
            admin_url('edit.php')
        );

        wp_safe_redirect($redirect);
        exit;
    }

    public function admin_notices() {
        if (!is_admin()) {
            return;
        }

        $screen = get_current_screen();

        if (!$screen || $screen->post_type !== self::POST_TYPE) {
            return;
        }

        $failed_query = new WP_Query([
            'post_type'      => self::POST_TYPE,
            'post_status'    => 'publish',
            'posts_per_page' => 1,
            'fields'         => 'ids',
            'meta_query'     => [
                [
                    'key'   => '_trip_email_status',
                    'value' => 'failed',
                ],
            ],
        ]);

        $failed_total = (int) $failed_query->found_posts;
        wp_reset_postdata();

        if ($failed_total > 0) {
            $bulk_url = wp_nonce_url(
                add_query_arg(
                    ['action' => 'trip_resend_all_failed'],
                    admin_url('admin-post.php')
                ),
                'trip_resend_all_failed'
            );
            ?>
            <div class="notice notice-warning">
                <p>
                    <strong>Email recovery:</strong>
                    <?php echo esc_html($failed_total); ?> request(s) currently have <strong>FAILED</strong> email status.
                    &nbsp;
                    <a class="button button-primary" href="<?php echo esc_url($bulk_url); ?>">Resend all failed emails</a>
                </p>
            </div>
            <?php
        }

        if (isset($_GET['trip_resend_single'])) {
            $result = sanitize_text_field(wp_unslash($_GET['trip_resend_single']));
            ?>
            <div class="notice <?php echo $result === 'sent' ? 'notice-success' : 'notice-error'; ?> is-dismissible">
                <p>
                    <?php echo $result === 'sent'
                        ? 'Request email was resent successfully.'
                        : 'Email resend failed. Automatic retry has been scheduled.'; ?>
                </p>
            </div>
            <?php
        }

        if (isset($_GET['trip_bulk_sent'], $_GET['trip_bulk_failed'])) {
            $sent = (int) $_GET['trip_bulk_sent'];
            $failed = (int) $_GET['trip_bulk_failed'];
            ?>
            <div class="notice notice-info is-dismissible">
                <p>
                    Bulk resend finished.
                    <strong>Sent: <?php echo esc_html($sent); ?></strong>
                    &nbsp;|&nbsp;
                    <strong>Failed: <?php echo esc_html($failed); ?></strong>
                    <?php if ($failed > 0) : ?> — failed requests were scheduled for automatic retry.<?php endif; ?>
                </p>
            </div>
            <?php
        }
    }

    public function request_row_actions($actions, $post) {
        if ($post->post_type !== self::POST_TYPE) {
            return $actions;
        }

        unset($actions['inline hide-if-no-js']);
        unset($actions['view']);

        $status = get_post_meta($post->ID, '_trip_email_status', true);

        if ($status === 'failed') {
            $url = wp_nonce_url(
                add_query_arg(
                    [
                        'action'  => 'trip_resend_request',
                        'post_id' => $post->ID,
                    ],
                    admin_url('admin-post.php')
                ),
                'trip_resend_request_' . $post->ID
            );

            $actions['trip_resend'] = '<a href="' . esc_url($url) . '">Resend Email</a>';
        }

        return $actions;
    }

    private function is_probable_bot() {
        $honeypot = isset($_POST['website'])
            ? trim((string) wp_unslash($_POST['website']))
            : '';

        $started = isset($_POST['form_started'])
            ? (int) $_POST['form_started']
            : 0;

        $elapsed = $started > 0 ? time() - $started : 999;

        return (
            $honeypot !== '' &&
            $elapsed >= 0 &&
            $elapsed < 3
        );
    }

    private function is_rate_limited() {
        $ip = $this->client_ip();

        if ($ip === '') {
            return false;
        }

        $key = 'trip_rl_' . md5($ip);
        $state = get_transient($key);

        if (!is_array($state) || empty($state['started']) || !isset($state['count'])) {
            set_transient(
                $key,
                [
                    'started' => time(),
                    'count'   => 1,
                ],
                self::RATE_LIMIT_WINDOW
            );
            return false;
        }

        $state['count'] = (int) $state['count'] + 1;
        $remaining = max(
            1,
            self::RATE_LIMIT_WINDOW - (time() - (int) $state['started'])
        );

        set_transient($key, $state, $remaining);

        return $state['count'] > self::RATE_LIMIT_MAX;
    }

    private function client_ip() {
        if (empty($_SERVER['REMOTE_ADDR'])) {
            return '';
        }

        return sanitize_text_field(wp_unslash($_SERVER['REMOTE_ADDR']));
    }

    private function generate_request_id() {
        return 'TRIP-' . wp_date('ymd-His') . '-' . wp_rand(1000, 9999);
    }

    private function save_request($request_id, array $data, $fingerprint = '') {
        $post_id = wp_insert_post(
            [
                'post_type'   => self::POST_TYPE,
                'post_status' => 'publish',
                'post_title'  => $request_id . ' — ' . $data['full_name'],
                'meta_input' => ['_trip_submission_fingerprint' => $fingerprint],
            ],
            true
        );

        if (is_wp_error($post_id)) {
            return $post_id;
        }

        update_post_meta($post_id, '_trip_request_id', $request_id);
        update_post_meta($post_id, '_trip_received_at', current_time('mysql'));
        update_post_meta($post_id, '_trip_email_status', 'pending');
        update_post_meta($post_id, '_trip_email_attempts', 0);
        update_post_meta($post_id, '_trip_user_agent', $this->user_agent());
        update_post_meta($post_id, '_trip_ip_hash', $this->ip_hash());

        foreach ($data as $key => $value) {
            update_post_meta($post_id, '_trip_' . $key, $value);
        }

        return $post_id;
    }

    private function get_saved_request_data($post_id) {
        $keys = [
            'full_name',
            'phone',
            'email',
            'driver_age',
            'pickup_city',
            'pickup_place',
            'pickup_date',
            'pickup_time',
            'dropoff_city',
            'dropoff_place',
            'dropoff_date',
            'dropoff_time',
            'location_notes',
            'rental_days',
            'passengers',
            'luggage',
            'transmission',
            'car_group',
            'abroad',
            'abroad_countries',
            'child_seats',
            'child_seat_count',
            'gps',
            'snow_chains',
            'priorities',
            'notes',
            'confirm',
        ];

        $data = [];

        foreach ($keys as $key) {
            $data[$key] = get_post_meta($post_id, '_trip_' . $key, true);
        }

        return $data;
    }

    private function ip_hash() {
        $ip = $this->client_ip();

        if ($ip === '') {
            return '';
        }

        return hash_hmac('sha256', $ip, wp_salt('auth'));
    }

    private function user_agent() {
        if (empty($_SERVER['HTTP_USER_AGENT'])) {
            return '';
        }

        return sanitize_text_field(wp_unslash($_SERVER['HTTP_USER_AGENT']));
    }

    public function capture_mail_error($wp_error) {
        if (is_wp_error($wp_error)) {
            $this->last_mail_error = $wp_error->get_error_message();
        }
    }

    private function collect_data() {
        return [
            'trip_ui'          => $this->textarea('trip_ui'),
            'full_name'        => $this->text('full_name'),
            'phone'            => $this->text('phone'),
            'email'            => $this->email('email'),
            'driver_age'       => $this->text('driver_age'),
            'pickup_city'      => $this->text('pickup_city'),
            'pickup_place'     => $this->text('pickup_place'),
            'pickup_date'      => $this->text('pickup_date'),
            'pickup_time'      => $this->text('pickup_time'),
            'dropoff_city'     => $this->text('dropoff_city'),
            'dropoff_place'    => $this->text('dropoff_place'),
            'dropoff_date'     => $this->text('dropoff_date'),
            'dropoff_time'     => $this->text('dropoff_time'),
            'location_notes'   => $this->textarea('location_notes'),
            'rental_days'      => '',
            'passengers'       => $this->text('passengers'),
            'luggage'          => $this->text('luggage'),
            'transmission'     => $this->text('transmission'),
            'car_group'        => $this->text_array('car_group'),
            'abroad'           => $this->text('abroad'),
            'abroad_countries' => $this->text('abroad_countries'),
            'child_seats'      => $this->text('child_seats'),
            'child_seat_count' => $this->text('child_seat_count'),
            'gps'              => $this->text('gps'),
            'snow_chains'      => $this->text('snow_chains'),
            'priorities'       => $this->text_array('priorities'),
            'notes'            => $this->textarea('notes'),
            'confirm'          => $this->text('confirm'),
        ];
    }

    private function build_email_body(array $d, $request_id, $post_id) {
        $car_groups = !empty($d['car_group'])
            ? "\n- " . implode("\n- ", (array) $d['car_group'])
            : 'לא נבחר';

        $priorities = !empty($d['priorities'])
            ? implode(', ', (array) $d['priorities'])
            : 'לא צוין';

        $admin_url = admin_url('post.php?post=' . (int) $post_id . '&action=edit');

        return
            "מספר פנייה: {$request_id}\n" .
            "קישור לבקשה במערכת: {$admin_url}\n\n" .

            "פרטי לקוח:\n" .
            "שם: {$d['full_name']}\n" .
            "טלפון / וואטסאפ: {$d['phone']}\n" .
            "דוא״ל: {$d['email']}\n" .
            "כל נהג מעל גיל 24 ועם לפחות שנה רישיון: {$d['driver_age']}\n\n" .

            "קבלת הרכב:\n" .
            "עיר: {$d['pickup_city']}\n" .
            "מקום: {$d['pickup_place']}\n" .
            "תאריך: " . $this->format_date_for_display($d['pickup_date']) . "\n" .
            "שעה: {$d['pickup_time']}\n\n" .

            "החזרת הרכב:\n" .
            "עיר: {$d['dropoff_city']}\n" .
            "מקום: {$d['dropoff_place']}\n" .
            "תאריך: " . $this->format_date_for_display($d['dropoff_date']) . "\n" .
            "שעה: {$d['dropoff_time']}\n\n" .

            "מספר ימי שכירות משוער:\n" .
            "{$d['rental_days']}\n\n" .

            "הערות לגבי מקום קבלה / החזרה:\n" .
            "{$d['location_notes']}\n\n" .

            "נוסעים ורכב:\n" .
            "מספר נוסעים כולל הנהג: {$d['passengers']}\n" .
            "מספר מזוודות משוער: {$d['luggage']}\n" .
            "תיבת הילוכים: {$d['transmission']}\n" .
            "קבוצות רכב שנבחרו: {$car_groups}\n\n" .

            "יציאה מחוץ לפולין:\n" .
            "{$d['abroad']}\n" .
            "מדינות: {$d['abroad_countries']}\n\n" .

            "תוספות:\n" .
            "כיסאות / בוסטרים: {$d['child_seats']}\n" .
            "מספר כיסאות / בוסטרים: {$d['child_seat_count']}\n" .
            "GPS: {$d['gps']}\n" .
            "שרשראות שלג: {$d['snow_chains']}\n\n" .

            "מה חשוב ללקוח:\n" .
            "{$priorities}\n\n" .

            "הערות הלקוח:\n" .
            "{$d['notes']}\n\n" .

            "הערת מערכת:\n" .
            "מספר ימי השכירות חושב בצד השרת לפי תאריך ושעת הקבלה וההחזרה. " .
            "הבקשה נשמרה במערכת WordPress לפני ניסיון שליחת המייל. " .
            "שליחת הטופס אינה הזמנה סופית. " .
            "יש לבדוק זמינות, מחיר, תנאי ביטוח, פיקדון ואישור יציאה מחוץ לפולין מול חברת ההשכרה.\n";
    }

    private function safe_reply_name($name) {
        $name = str_replace(["\r", "\n", '"'], ['', '', ''], $name);
        return trim($name);
    }

    private function text($key) {
        if (!isset($_POST[$key])) {
            return '';
        }

        return sanitize_text_field(wp_unslash($_POST[$key]));
    }

    private function email($key) {
        if (!isset($_POST[$key])) {
            return '';
        }

        return sanitize_email(wp_unslash($_POST[$key]));
    }

    private function textarea($key) {
        if (!isset($_POST[$key])) {
            return '';
        }

        return sanitize_textarea_field(wp_unslash($_POST[$key]));
    }

    private function text_array($key) {
        if (!isset($_POST[$key]) || !is_array($_POST[$key])) {
            return [];
        }

        return array_values(
            array_filter(
                array_map(
                    static function ($item) {
                        return sanitize_text_field(wp_unslash($item));
                    },
                    $_POST[$key]
                )
            )
        );
    }

    private function redirect_with_status($status, $request_id = '', $error_code = '', $restore_token = '', $mail_status = '') {
        $url = set_url_scheme(home_url('/rent-a-car-in-poland/'), 'https');
        $args = ['trip_status' => $status];
        if ($status === 'success' && $request_id !== '') {
            $receipt_token = strtolower(wp_generate_password(32, false, false));
            set_transient('trip_receipt_' . $receipt_token, ['id'=>$request_id, 'mail_status'=>$mail_status], HOUR_IN_SECONDS);
            $args['trip_receipt'] = $receipt_token;
        }

        if ($request_id !== '') {
            $args['trip_id'] = $request_id;
        }

        if ($error_code !== '') {
            $args['trip_error'] = $error_code;
        }

        if ($restore_token !== '') {
            $args['trip_restore'] = $restore_token;
        }

        $url = add_query_arg($args, $url);
        $url .= '#tripStatusMessage';

        wp_safe_redirect($url, 303);
        exit;
    }

    public function admin_columns($columns) {
        return [
            'cb'               => isset($columns['cb']) ? $columns['cb'] : '<input type="checkbox" />',
            'title'            => 'Request',
            'trip_customer'     => 'Customer',
            'trip_route'        => 'Route',
            'trip_rental_dates' => 'Rental dates',
            'trip_email_status' => 'Email',
            'trip_attempts'     => 'Attempts',
            'date'             => 'Received',
        ];
    }

    public function admin_column_content($column, $post_id) {
        switch ($column) {
            case 'trip_customer':
                $name = get_post_meta($post_id, '_trip_full_name', true);
                $email = get_post_meta($post_id, '_trip_email', true);
                $phone = get_post_meta($post_id, '_trip_phone', true);

                echo '<strong>' . esc_html($name) . '</strong><br>';

                if ($email) {
                    echo '<a href="mailto:' . esc_attr($email) . '">' . esc_html($email) . '</a><br>';
                }

                if ($phone) {
                    echo esc_html($phone);
                }
                break;

            case 'trip_route':
                $pickup = get_post_meta($post_id, '_trip_pickup_city', true);
                $dropoff = get_post_meta($post_id, '_trip_dropoff_city', true);
                echo esc_html($pickup . ' → ' . $dropoff);
                break;

            case 'trip_rental_dates':
                $pickup_date = get_post_meta($post_id, '_trip_pickup_date', true);
                $dropoff_date = get_post_meta($post_id, '_trip_dropoff_date', true);
                echo esc_html($this->format_date_for_display($pickup_date) . ' → ' . $this->format_date_for_display($dropoff_date));
                break;

            case 'trip_email_status':
                $status = get_post_meta($post_id, '_trip_email_status', true);

                if ($status === 'sent') {
                    echo '<strong style="color:#1d7a32;">SENT</strong>';
                } elseif ($status === 'failed') {
                    echo '<strong style="color:#b32d2e;">FAILED</strong>';
                } else {
                    echo '<strong>PENDING</strong>';
                }
                break;

            case 'trip_attempts':
                echo esc_html((int) get_post_meta($post_id, '_trip_email_attempts', true));
                break;
        }
    }

    public function add_request_meta_box() {
        add_meta_box(
            'trip_request_details',
            'Request details',
            [$this, 'render_request_meta_box'],
            self::POST_TYPE,
            'normal',
            'high'
        );
    }

    public function render_request_meta_box($post) {
        $fields = [
            'request_id'         => 'Request ID',
            'received_at'        => 'Received at',
            'email_status'       => 'Email status',
            'email_attempts'     => 'Email attempts',
            'email_last_attempt' => 'Last email attempt',
            'email_sent_at'      => 'Email sent at',
            'email_error'        => 'Email error',
            'full_name'          => 'Full name',
            'phone'              => 'Phone / WhatsApp',
            'email'              => 'Email',
            'driver_age'         => 'Driver age / experience',
            'pickup_city'        => 'Pickup city',
            'pickup_place'       => 'Pickup place',
            'pickup_date'        => 'Pickup date',
            'pickup_time'        => 'Pickup time',
            'dropoff_city'       => 'Drop-off city',
            'dropoff_place'      => 'Drop-off place',
            'dropoff_date'       => 'Drop-off date',
            'dropoff_time'       => 'Drop-off time',
            'location_notes'     => 'Location notes',
            'rental_days'        => 'Estimated rental days',
            'passengers'         => 'Passengers',
            'luggage'            => 'Luggage',
            'transmission'       => 'Transmission',
            'car_group'          => 'Car groups',
            'abroad'             => 'Leaving Poland',
            'abroad_countries'   => 'Countries',
            'child_seats'        => 'Child seats',
            'child_seat_count'   => 'Seat count',
            'gps'                => 'GPS',
            'snow_chains'        => 'Snow chains',
            'priorities'         => 'Priorities',
            'notes'              => 'Customer notes',
            'confirm'            => 'Confirmed',
        ];

        echo '<table class="widefat striped" style="max-width:1100px;"><tbody>';

        foreach ($fields as $key => $label) {
            $value = get_post_meta($post->ID, '_trip_' . $key, true);

            if (is_array($value)) {
                $value = implode(', ', $value);
            }

            if ($key === 'pickup_date' || $key === 'dropoff_date') {
                $value = $this->format_date_for_display((string) $value);
            }

            echo '<tr>';
            echo '<th style="width:220px;">' . esc_html($label) . '</th>';
            echo '<td style="white-space:pre-wrap;">' . esc_html((string) $value) . '</td>';
            echo '</tr>';
        }

        echo '</tbody></table>';
    }
}

$trip_rental_instance = new Trip_Car_Request_Form();
add_action('template_redirect', function () {
    if (is_page(85)) {
        if (!defined('DONOTCACHEPAGE')) define('DONOTCACHEPAGE', true);
        nocache_headers();
    }
});
add_action('wp_print_footer_scripts', function () {
    if (is_page(85)) wp_dequeue_script('smoothscroll');
}, 0);
add_action('wp_abilities_api_init', function () use ($trip_rental_instance) {
    wp_register_ability('trip-rental/health', [
        'label'=>'Trip rental readiness', 'description'=>'Read-only configuration and validation checks, without sending email or saving customer data.',
        'category'=>'site',
        'input_schema'=>['type'=>'object'], 'output_schema'=>['type'=>'object'],
        'permission_callback'=>function(){return current_user_can('manage_options');},
        'execute_callback'=>function() use ($trip_rental_instance) {
            $recipient = new ReflectionMethod($trip_rental_instance, 'recipient');
            $recipient->setAccessible(true);
            $validate = new ReflectionMethod($trip_rental_instance, 'validate_and_normalize_data');
            $validate->setAccessible(true);
            $data=['full_name'=>'TEST-NAME','email'=>'test@example.invalid','driver_age'=>'לא צוין','pickup_city'=>'Warszawa','pickup_place'=>'AIRPORT','pickup_date'=>'2090-01-01','pickup_time'=>'10:00','dropoff_city'=>'Kraków','dropoff_place'=>'AIRPORT','dropoff_date'=>'2090-01-02','dropoff_time'=>'10:00','passengers'=>'2','luggage'=>'1','transmission'=>'אוטומטית','abroad'=>'לא','confirm'=>'כן','child_seat_count'=>''];
            $good=$validate->invoke($trip_rental_instance,$data);
            $bad=$data;$bad['dropoff_date']='2089-12-31';
            $past=$data;$past['pickup_date']='2000-01-01';
            $saved_get = $_GET;
            $test_token = 'test' . strtolower(wp_generate_password(24, false, false));
            $receipt_checks = [];
            try {
                $_GET = ['trip_receipt'=>$test_token];
                foreach (['sent', 'failed'] as $test_status) {
                    set_transient('trip_receipt_' . $test_token, ['id'=>'TEST-RECEIPT', 'mail_status'=>$test_status], MINUTE_IN_SECONDS);
                    $rendered = $trip_rental_instance->render_shortcode();
                    $receipt_checks[$test_status] = strpos($rendered, $test_status === 'sent' ? 'הבקשה נשלחה בהצלחה' : 'משלוח הדוא״ל מתעכב') !== false && strpos($rendered, 'id="rental"') === false;
                }
            } finally {
                $_GET = $saved_get;
                delete_transient('trip_receipt_' . $test_token);
            }
            return ['recipient_configured'=>(bool)$recipient->invoke($trip_rental_instance),
                'receipt_checks'=>$receipt_checks,
                'valid_dates'=>!is_wp_error($good), 'reversed_dates_rejected'=>is_wp_error($validate->invoke($trip_rental_instance,$bad)),
                'past_dates_rejected'=>is_wp_error($validate->invoke($trip_rental_instance,$past)),
                'rental_days'=>is_wp_error($good)?null:$good['rental_days'],
                'spring_gap_rejected'=>is_wp_error($validate->invoke($trip_rental_instance,array_merge($data,['pickup_date'=>'2027-03-28','pickup_time'=>'02:30','dropoff_date'=>'2027-03-29']))),
                'timezone'=>'Europe/Warsaw', 'shortcode'=>shortcode_exists('trip_car_request_form')];
        },
        'meta'=>['show_in_rest'=>true,'mcp'=>['public'=>true,'type'=>'tool'], 'annotations'=>['readonly'=>true,'destructive'=>false]]
    ]);
});
