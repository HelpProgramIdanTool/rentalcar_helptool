<?php defined('ABSPATH') || exit; ?>
<footer class="prc-english-footer prc-site-footer" lang="<?php echo esc_attr($language); ?>" dir="<?php echo esc_attr($direction); ?>">
    <div class="prc-footer-inner">
        <section><h2><?php echo esc_html($navigation['brand']); ?></h2><p><?php echo esc_html($navigation['tagline']); ?></p></section>
        <nav aria-label="<?php echo esc_attr($navigation['footer_heading']); ?>"><h2><?php echo esc_html($navigation['footer_heading']); ?></h2><ul>
            <li><a href="<?php echo esc_url(home_url($navigation['guides_path'])); ?>"><?php echo esc_html($navigation['footer_guides_label']); ?></a></li>
            <li><a href="<?php echo esc_url(home_url($navigation['companies_path'])); ?>"><?php echo esc_html($navigation['footer_companies_label']); ?></a></li>
            <li><a href="<?php echo esc_url(home_url($navigation['privacy_path'])); ?>"><?php echo esc_html($navigation['footer_privacy_label']); ?></a></li>
        </ul></nav>
        <section><h2><?php echo esc_html($navigation['footer_contact_heading']); ?></h2>
            <p><a href="<?php echo esc_url('mailto:'.$navigation['contact_email']); ?>"><bdi dir="ltr"><?php echo esc_html($navigation['contact_email']); ?></bdi></a><br>
            <a href="<?php echo esc_url('tel:'.preg_replace('/[^+0-9]/','',$navigation['phone'])); ?>"><bdi dir="ltr"><?php echo esc_html($navigation['phone']); ?></bdi></a></p>
        </section>
    </div>
    <p class="prc-copyright">&copy; <?php echo esc_html(wp_date('Y')); ?> <bdi><?php echo esc_html($navigation['brand']); ?></bdi></p>
</footer>
