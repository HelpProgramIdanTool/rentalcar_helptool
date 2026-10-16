(function () {
  'use strict';
  document.addEventListener('click', function (event) {
    var link = event.target.closest('.prc-video-link');
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    var url = new URL(link.dataset.embed);
    if (!['www.youtube.com', 'youtube.com', 'www.youtube-nocookie.com', 'youtube-nocookie.com'].includes(url.hostname) || !/^\/embed\/[a-zA-Z0-9_-]{11}$/.test(url.pathname)) return;
    event.preventDefault();
    url.searchParams.set('autoplay', '1');
    var frame = document.createElement('iframe');
    frame.src = url.href;
    frame.title = link.getAttribute('aria-label') || '';
    frame.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
    frame.allowFullscreen = true;
    frame.referrerPolicy = 'strict-origin-when-cross-origin';
    link.replaceWith(frame);
    frame.focus();
  });
}());
