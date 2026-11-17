<?php
defined('ABSPATH') || exit;
get_header();
?>
<main id="main-content" class="prc-request-page" lang="en" dir="ltr">
    <?php $navigation = PRC_Bilingual_Form::navigation(); ?>
    <header class="prc-english-header">
        <a class="prc-english-brand" href="<?php echo esc_url(home_url($navigation['home_path'])); ?>"><?php echo esc_html($navigation['brand']); ?></a>
        <nav class="prc-english-nav" aria-label="Main navigation">
            <a href="#prcRequestForm"><?php echo esc_html($navigation['quote_label']); ?></a>
            <a href="<?php echo esc_url('mailto:' . $navigation['contact_email']); ?>"><?php echo esc_html($navigation['contact_label']); ?></a>
        </nav>
        <?php echo PRC_Bilingual_Form::language_switcher(true); ?>
    </header>
    <div class="prc-request-container">
        <?php while (have_posts()) : the_post(); ?>
            <article id="post-<?php the_ID(); ?>" <?php post_class(); ?>>
                <h1 class="entry-title"><?php the_title(); ?></h1>
                <div class="entry-content"><?php the_content(); ?></div>
            </article>
        <?php endwhile; ?>
    </div>
</main>
<?php get_footer(); ?>
