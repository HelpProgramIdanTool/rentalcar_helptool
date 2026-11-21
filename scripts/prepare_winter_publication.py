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
css += '''
.prc-winter-page{box-sizing:border-box;width:100%;max-width:1040px;margin:0 auto!important;padding:0 24px;float:none!important;direction:rtl;text-align:right}
.prc-winter-page .winter-page{box-sizing:border-box;width:100%;max-width:920px;margin:0 auto!important;padding:0;float:none!important}
.prc-winter-page .article-section p,.prc-winter-page .personal-story p{font-size:16px;line-height:1.8}
body:has(.prc-winter-page) #main-content .entry-content{width:100%;max-width:100%;float:none}
body:has(.prc-winter-page) #main-content>.container{width:100%;max-width:1040px;margin:0 auto;padding:24px 0}
body:has(.prc-winter-page) #main-content .entry-title{max-width:920px;margin:24px auto 0;text-align:right}
@media(max-width:600px){.prc-winter-page{padding:0 16px}.prc-winter-page .winter-page{padding:0}.prc-winter-page .article-section p,.prc-winter-page .personal-story p{font-size:16px}}
'''
payload = dict(slug='winter-driving-poland', title='חורף בפולין בלי דרמה: צמיגים, שרשראות והדרך לזקופנה',
 content='<style>'+css+'</style><div class="prc-winter-page" lang="he" dir="rtl"><div class="winter-page">'+content+'</div></div>',
 excerpt='צמיגים מתאימים לעונה, שרשראות, תמרור C-18 והדרך לזקופנה: מדריך מעשי עם ניסיון אישי של עידן והכנה פשוטה לנסיעה בחורף.',
 status='publish', comment_status='closed')
path = review.OUT.parent / 'winter-publication.json'
path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
print(path)
