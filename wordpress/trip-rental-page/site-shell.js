(function(){
 'use strict';
 function init(){
  var header=document.getElementById('trip-shell-header');
  if(!header)return;
  // Works even with a legacy template that omitted wp_body_open.
  var page=document.getElementById('page-container');
  if(page&&page.parentNode&&(header.compareDocumentPosition(page)&Node.DOCUMENT_POSITION_PRECEDING))page.parentNode.insertBefore(header,page);
  var toggle=header.querySelector('.trip-menu-toggle');
  header.setAttribute('data-menu-ready','true');
  function close(){header.classList.remove('is-open');toggle.setAttribute('aria-expanded','false');header.querySelectorAll('.trip-nav-item.is-open').forEach(function(item){item.classList.remove('is-open');item.querySelector('.trip-submenu-toggle').setAttribute('aria-expanded','false');});}
  toggle.addEventListener('click',function(){var open=header.classList.toggle('is-open');toggle.setAttribute('aria-expanded',String(open));});
  header.querySelectorAll('.trip-submenu-toggle').forEach(function(button){
   button.addEventListener('click',function(){var open=button.closest('.trip-nav-item').classList.toggle('is-open');button.setAttribute('aria-expanded',String(open));});
  });
  document.addEventListener('keydown',function(event){if(event.key==='Escape'){var button=header.querySelector('.trip-submenu-toggle[aria-expanded="true"]');var open=header.classList.contains('is-open');close();if(open)toggle.focus();else if(button)button.focus();}});
  document.addEventListener('click',function(event){if(!header.contains(event.target))close();});
  var wide=window.matchMedia('(min-width:1100px)');
  if(wide.addEventListener)wide.addEventListener('change',function(){if(wide.matches)close();});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
}());
