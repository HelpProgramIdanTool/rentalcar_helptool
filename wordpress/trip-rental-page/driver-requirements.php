<?php
/* Shared collection/validation only. Supplier policy and prices live in Django. */
add_action('init', function () {
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST' || !isset($_POST['driver_requirements'])) return;
    $raw = wp_unslash($_POST['driver_requirements']);
    $data = is_string($raw) ? json_decode($raw, true) : null;
    $valid = is_array($data) && isset($data['exception']) && is_bool($data['exception']) && isset($data['drivers']) && is_array($data['drivers']);
    if ($valid) {
        $valid = count($data['drivers']) <= 9 && ($data['exception'] ? count($data['drivers']) > 0 : count($data['drivers']) === 0);
        foreach ($data['drivers'] as $row) {
            $age = $row['age'] ?? null; $months = $row['license_months'] ?? null;
            $valid = $valid && is_int($age) && is_int($months) && $age >= 16 && $age <= 100 && $months >= 0 && $months <= $age*12 && ($age < 24 || $months < 12);
        }
    }
    if (!$valid) wp_die('Please check driver age and licence experience / נא לבדוק גיל וותק רישיון', '', ['response'=>400]);
    // Both original handlers save notes before sending; retries retain the declaration.
    $notes = isset($_POST['notes']) && is_string($_POST['notes']) ? wp_unslash($_POST['notes']) : '';
    $notes = preg_replace('/^Driver requirements JSON:.*$/m', '', $notes);
    $_POST['notes'] = wp_slash(trim($notes) . "\nDriver requirements JSON: " . wp_json_encode($data));
}, 1);

add_action('wp_enqueue_scripts', function () {
    wp_enqueue_script('rental-driver-requirements', plugin_dir_url(__FILE__).'driver-requirements.js', [], '20261127-1', true);
});
