<?php
defined('ABSPATH') || exit;
$navigation=PRC_Bilingual_Form::navigation();
?><!doctype html>
<html <?php language_attributes(); ?>>
<head>
    <meta charset="<?php bloginfo('charset'); ?>">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>
<a class="prc-skip-link" href="#main-content">Skip to content</a>
<header class="prc-english-header">
    <a class="prc-english-brand" href="<?php echo esc_url(home_url($navigation['home_path'])); ?>"><?php echo esc_html($navigation['brand']); ?></a>
    <?php echo PRC_Bilingual_Form::language_switcher(true); ?>
    <nav class="prc-english-nav" aria-label="Main navigation">
        <?php if (get_option('prc_english_menu_id')) : ?>
            <?php wp_nav_menu(['menu'=>(int)get_option('prc_english_menu_id'),'container'=>false,'menu_class'=>'prc-nav-list','fallback_cb'=>false,'depth'=>1]); ?>
        <?php else : ?>
            <ul class="prc-nav-list">
                <li><a href="<?php echo esc_url(home_url($navigation['home_path'])); ?>">Home</a></li>
                <li><a href="<?php echo esc_url(home_url($navigation['english_quote_path'])); ?>"><?php echo esc_html($navigation['quote_label']); ?></a></li>
            </ul>
        <?php endif; ?>
    </nav>
</header>
<main id="main-content" class="prc-request-page" lang="en" dir="ltr">
    <div class="prc-request-container">
        <?php while (have_posts()) : the_post(); ?>
            <article id="post-<?php the_ID(); ?>" <?php post_class(); ?>>
                <h1 class="entry-title"><?php the_title(); ?></h1>
                <div class="entry-content"><?php the_content(); ?></div>
            </article>
        <?php endwhile; ?>
    </div>
</main>
<footer class="prc-english-footer" lang="en" dir="ltr">
    <div class="prc-footer-inner">
        <section><h2><?php echo esc_html($navigation['brand']); ?></h2><p><?php echo esc_html($navigation['tagline']); ?></p></section>
        <nav aria-label="Footer navigation"><h2><?php echo esc_html($navigation['footer_heading']); ?></h2><ul>
            <li><a href="<?php echo esc_url(home_url($navigation['guides_path'])); ?>"><?php echo esc_html($navigation['footer_guides_label']); ?></a></li>
            <li><a href="<?php echo esc_url(home_url($navigation['companies_path'])); ?>"><?php echo esc_html($navigation['footer_companies_label']); ?></a></li>
            <li><a href="<?php echo esc_url(home_url($navigation['privacy_path'])); ?>"><?php echo esc_html($navigation['footer_privacy_label']); ?></a></li>
        </ul></nav>
        <section><h2><?php echo esc_html($navigation['footer_contact_heading']); ?></h2>
            <p><a href="<?php echo esc_url('mailto:'.$navigation['contact_email']); ?>"><?php echo esc_html($navigation['contact_email']); ?></a><br>
            <a href="<?php echo esc_url('tel:'.preg_replace('/[^+0-9]/','',$navigation['phone'])); ?>"><?php echo esc_html($navigation['phone']); ?></a></p>
        </section>
    </div>
    <p class="prc-copyright">&copy; <?php echo esc_html(wp_date('Y')); ?> <?php echo esc_html($navigation['brand']); ?></p>
</footer>
<?php wp_footer(); ?>
</body>
</html>
