<?php
defined('ABSPATH') || exit;
get_header();
?>
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
<?php get_footer(); ?>
