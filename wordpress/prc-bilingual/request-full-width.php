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
<header class="prc-english-header" dir="ltr">
    <a class="prc-english-brand" href="<?php echo esc_url(home_url($navigation['home_path'])); ?>"><?php echo esc_html($navigation['brand']); ?></a>
    <?php echo PRC_Bilingual_Form::language_switcher(true); ?>
    <nav class="prc-english-nav" aria-label="Main navigation" dir="ltr">
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
<?php echo PRC_Bilingual_Form::footer_html(true); ?>
<?php wp_footer(); ?>
</body>
</html>
