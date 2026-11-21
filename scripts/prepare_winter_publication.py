"""Prepare approved winter article with styles scoped to its content."""
import json
import re
import build_winter_driving_review as review

source = review.OUT.read_text(encoding='utf-8')
content = re.search(r'<main\b[^>]*>(.*?)</main>', source, re.S).group(1)
content = re.sub(r'<h1>.*?</h1>', '', content, flags=re.S)
css = re.search(r'<style>(.*?)</style>', source, re.S).group(1)
def scope(match):
    selector = match.group(1).strip()
    if selector.startswith('@'):
        return selector+'{'
    return ','.join('.prc-winter-page '+s.strip() for s in selector.split(','))+'{'
css = re.sub(r'([^{}]+)\{', scope, css)
css += '''.prc-winter-page{--navy:#163960;--blue:#145f9e;--ink:#25374a;--muted:#627387;--line:#dce4ed;--gold:#ffdf70;color:var(--ink);font:16px/1.75 Arial,sans-serif}.prc-winter-page img{max-width:100%}body:has(.prc-winter-page) #sidebar{display:none}body:has(.prc-winter-page) #left-area{width:100%;padding:0}body:has(.prc-winter-page) #main-content .container:before{display:none}body:has(.prc-winter-page) .entry-title{font-size:clamp(29px,4vw,44px);line-height:1.3;color:#163960}'''
payload = dict(slug='winter-driving-poland', title='חורף בפולין בלי דרמה: צמיגים, שרשראות והדרך לזקופנה',
 content='<style>'+css+'</style><div class="prc-winter-page" lang="he" dir="rtl"><div class="winter-page">'+content+'</div></div>',
 excerpt='צמיגים מתאימים לעונה, שרשראות, תמרור C-18 והדרך לזקופנה: מדריך מעשי עם ניסיון אישי של עידן והכנה פשוטה לנסיעה בחורף.',
 status='publish', comment_status='closed')
path = review.OUT.parent / 'winter-publication.json'
path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
print(path)
