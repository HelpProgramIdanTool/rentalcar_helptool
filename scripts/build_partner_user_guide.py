"""Build the Hebrew partner guide. Run with uv run --with python-bidi python ..."""
from pathlib import Path
from bidi.algorithm import get_display
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf/Poland_Rent_a_Car_Partner_Guide_HE_Updated.pdf'
LOGIN='https://rentalcar-helptool.onrender.com/partners/login/'
EMAIL='idanrentacar@gmail.com'
PHONE='+48 533 100 636'
TOTAL_PAGES=7
W,H=A4
M=43
NAVY='#163960';BLUE='#145f9e';INK='#23364b';MUTED='#5c6e81'
PALE='#edf4fb';PURPLE='#eee5f7';AMBER='#fff5df';GREEN='#eaf5ee'


class Guide:
    def __init__(self):
        OUT.parent.mkdir(parents=True,exist_ok=True)
        pdfmetrics.registerFont(TTFont('Guide','C:/Windows/Fonts/arial.ttf'))
        pdfmetrics.registerFont(TTFont('GuideBold','C:/Windows/Fonts/arialbd.ttf'))
        self.c=canvas.Canvas(str(OUT),pagesize=A4,pageCompression=1)
        self.c.setTitle('Poland Rent a Car | מדריך לשימוש בקבינט השותפים')
        self.c.setAuthor('Poland Rent a Car | Idan')
        self.c.setSubject('כניסה, הצעות מחיר, הזמנות ושירות אישי לשותפים')
        self.c.setViewerPreference('Direction','R2L')
        self.page=0;self.y=0

    def text(self,text,x,y,size=11.3,bold=False,color=INK,rtl=True):
        c=self.c;c.setFont('GuideBold' if bold else 'Guide',size);c.setFillColor(HexColor(color))
        # ActualText preserves logical Hebrew when a reader copies the visual RTL run.
        c._code.append('/Span << /ActualText <FEFF'+text.encode('utf-16-be').hex().upper()+'> >> BDC')
        if rtl:c.drawRightString(x,y,get_display(text,base_dir='R'))
        else:c.drawString(x,y,text)
        c._code.append('EMC')

    def lines(self,text,width,size=11.3,bold=False):
        font='GuideBold' if bold else 'Guide';result=[]
        for paragraph in text.split('\n'):
            line=''
            for word in paragraph.split():
                test=(line+' '+word).strip()
                if line and pdfmetrics.stringWidth(get_display(test,base_dir='R'),font,size)>width:
                    result.append(line);line=word
                else:line=test
            result.append(line)
        return result

    def para(self,text,size=11.3,bold=False,color=INK,gap=9,indent=0):
        for line in self.lines(text,W-2*M-indent,size,bold):
            self.text(line,W-M-indent,self.y,size,bold,color);self.y-=16.4
        self.y-=gap

    def heading(self,title):
        self.y-=5;self.text(title,W-M,self.y,14.5,True,NAVY);self.y-=25

    def step(self,number,title,body):
        self.c.setFillColor(HexColor(BLUE));self.c.circle(W-M-10,self.y-1,10,fill=1,stroke=0)
        self.text(str(number),W-M-6.5,self.y-5,10,True,'#ffffff')
        self.text(title,W-M-29,self.y-4,12,True,NAVY);self.y-=25
        self.para(body,indent=29,gap=10)

    def callout(self,title,body,background=PALE,accent=BLUE):
        title_lines=self.lines(title,W-2*M-32,11.6,True)
        body_lines=self.lines(body,W-2*M-32,10.8)
        height=20+16*len(title_lines)+15.8*len(body_lines)
        bottom=self.y-height+10
        self.c.setFillColor(HexColor(background));self.c.roundRect(M,bottom,W-2*M,height,8,fill=1,stroke=0)
        self.c.setFillColor(HexColor(accent));self.c.roundRect(W-M-4,bottom,4,height,2,fill=1,stroke=0)
        top=self.y-9
        for line in title_lines:self.text(line,W-M-15,top,11.6,True,accent);top-=16
        for line in body_lines:self.text(line,W-M-15,top,10.8);top-=15.8
        self.y=bottom-18

    def new(self,kicker,title,subtitle):
        if self.page:self.finish()
        self.page+=1;c=self.c
        c.setFillColor(HexColor(NAVY));c.rect(0,H-78,W,78,fill=1,stroke=0)
        self.text('Poland Rent a Car',M,H-33,15,True,'#ffffff',False)
        self.text('המדריך לשותפים',W-M,H-33,10.5,False,'#dce9f5')
        self.text(kicker,W-M,H-59,9,False,'#ffdf70')
        self.y=H-116
        self.text(title,W-M,self.y,24,True,NAVY);self.y-=28
        self.para(subtitle,11,color=MUTED,gap=16)

    def finish(self):
        assert self.y>66,f'Page {self.page} overflowed: {self.y}'
        c=self.c;c.setStrokeColor(HexColor('#d6e0eb'));c.line(M,49,W-M,49)
        self.text(f'עמוד {self.page} מתוך {TOTAL_PAGES}',W-M,32,8.5,color=MUTED)
        self.text('Poland Rent a Car | 21.11.2026',M,32,8,color=MUTED,rtl=False)
        c.linkURL(LOGIN,(M,22,230,44),relative=0,thickness=0)
        c.showPage()

    def buttons(self,labels):
        count=len(labels);gap=8;width=(W-2*M-gap*(count-1))/count
        for i,label in enumerate(labels):
            x=W-M-width-i*(width+gap)
            self.c.setFillColor(HexColor(BLUE));self.c.roundRect(x,self.y-27,width,34,6,fill=1,stroke=0)
            self.text(label,x+width-12,self.y-14,10.4,True,'#ffffff')
        self.y-=49

    def route(self):
        labels=['פרטי הלקוח והנסיעה','בחירת רכבים','תצוגת ההצעה','פרטי ההזמנה']
        width=(W-2*M-21)/4
        for i,label in enumerate(labels):
            x=W-M-width-i*(width+7)
            self.c.setFillColor(HexColor(PALE));self.c.roundRect(x,self.y-60,width,63,7,fill=1,stroke=0)
            self.c.setFillColor(HexColor('#ffdf70'));self.c.circle(x+width-19,self.y-14,10,fill=1,stroke=0)
            self.text(str(i+1),x+width-15.5,self.y-18,10,True,NAVY)
            for j,line in enumerate(self.lines(label,width-16,10.2,True)):
                self.text(line,x+width-8,self.y-37-j*14,10.2,True,NAVY)
        self.y-=83


def build():
    g=Guide()
    g.new('מתחילים כאן','האזור האישי שלכם','מדריך מעשי ליצירת הצעות מחיר ולהזמנת רכב, עם ליווי אישי של עידן.')
    g.para('הקבינט מאפשר להכין הצעה ללקוח, להשוות בין אפשרויות, לשלוח את ההצעה ולהפוך אפשרות נבחרת לבקשת הזמנה. אתם רואים רק את ההצעות וההזמנות שנוצרו דרך החשבון שלכם.',gap=16)
    g.route()
    g.heading('כניסה למערכת')
    g.para('פתחו את הקישור הבא והזינו את שם המשתמש והסיסמה שקיבלתם מעידן. השתמשו בפרטי הכניסה שלכם, לא בפרטים של הלקוח שעבורו אתם מכינים הצעה.')
    g.buttons(['כניסה לאזור האישי'])
    g.c.linkURL(LOGIN,(M,g.y+15,W-M,g.y+49),relative=0,thickness=0)
    g.text(LOGIN,M,g.y,9,color=BLUE,rtl=False);g.y-=25
    g.callout('שלוש הלשוניות בראש המסך','לתת הצעה - מתחילים הצעה חדשה.\nהצעות - חוזרים להצעות שכבר נשמרו.\nהזמנות - רואים בקשות הזמנה שנוצרו בקבינט ואת מצבן.')
    g.callout('חשוב לדעת כבר בהתחלה','יצירת הצעה ופתיחת תצוגה מקדימה אינן שולחות מייל.\nשליחת בקשת הזמנה לחברה אינה אישור סופי להזמנה.',AMBER,'#87591c')
    g.heading('יש לכם כתובת אישית')
    g.para('לבקשה שאינה רגילה, לשינוי או לביטול - פנו לעידן. אם שכחתם סיסמה, בקשו ממנו עזרה. בסיום העבודה במחשב משותף לחצו על ״יציאה״.',size=10.8,gap=6)
    g.text(EMAIL,M,g.y,10.4,True,BLUE,False);g.c.linkURL('mailto:'+EMAIL,(M,g.y-3,225,g.y+12),relative=0,thickness=0)
    g.text(PHONE,W-M-pdfmetrics.stringWidth(PHONE,'GuideBold',10.4),g.y,10.4,True,BLUE,False);g.c.linkURL('https://wa.me/48533100636',(W-190,g.y-3,W-M,g.y+12),relative=0,thickness=0);g.y-=20

    g.new('גישה מהירה למערכת','סמל במחשב או בטלפון','אפשר לפתוח את הקבינט בלחיצה על סמל, בלי לחפש את הקישור בכל פעם. אין צורך להוריד אפליקציה מחנות.')
    g.para('תחילה פותחים בדפדפן רגיל את עמוד הכניסה הבא. אם הקישור נפתח בתוך WhatsApp או אפליקציית מייל, מעתיקים אותו ל-Chrome או ל-Safari. לא משתמשים בגלישה פרטית.',size=10.8)
    g.text(LOGIN,M,g.y,9,color=BLUE,rtl=False);g.c.linkURL(LOGIN,(M,g.y-3,W-M,g.y+12),relative=0,thickness=0);g.y-=25
    g.step(1,'מחשב - Chrome','פתחו את עמוד הכניסה. בתפריט שלוש הנקודות בחרו ״העברה, שמירה ושיתוף״ (Cast, save, and share), ואז ״יצירת קיצור דרך״ (Create shortcut). תנו לקיצור שם, למשל Poland Rent a Car, ולחצו ״יצירה״. פתחו את הקיצור שנוצר כדי לוודא שהוא מוביל לקבינט.')
    g.step(2,'טלפון Android - Chrome','פתחו את עמוד הכניסה ב-Chrome. לחצו על שלוש הנקודות ובחרו ״הוספה למסך הבית״. בגרסאות אחרות האפשרות מופיעה תחת Install and create shortcut ואז Create shortcut. תנו לסמל שם, לחצו ״הוספה״ ואשרו את ההוספה למסך הבית אם תתבקשו.')
    g.step(3,'iPhone - Safari','פתחו את עמוד הכניסה ב-Safari. לחצו על כפתור השיתוף, בחרו ״הוסף למסך הבית״ (Add to Home Screen), תנו לסמל שם ולחצו ״הוסף״. אם האפשרות אינה מופיעה, גללו ברשימת פעולות השיתוף ובדקו גם ״עריכת פעולות״ (Edit Actions).')
    g.callout('מה הסמל עושה?','הסמל הוא קיצור דרך לאותו חשבון ואותם נתונים. כדי לעבוד נדרשים חיבור לאינטרנט ופרטי הכניסה שלכם. אם המערכת מבקשת סיסמה מחדש, נכנסים כרגיל; הסמל אינו עוקף את ההתחברות. שמות התפריטים עשויים להשתנות לפי שפת המכשיר וגרסת הדפדפן.',PALE)
    g.para('להוראות היצרן המעודכנות: קיצורי דרך ב-Chrome וב-Safari.',size=9.5,color=MUTED,gap=5)
    for label,url in [('Chrome - Computer','https://support.google.com/chrome/answer/15085120?co=GENIE.Platform%3DDesktop&hl=en'),('Chrome - Android','https://support.google.com/chrome/answer/15085120?co=GENIE.Platform%3DAndroid&hl=en'),('Safari - iPhone','https://support.apple.com/guide/iphone/bookmark-a-website-iph42ab2f3a7/ios')]:
        g.text(label,M,g.y,9,color=BLUE,rtl=False);g.c.linkURL(url,(M,g.y-3,M+180,g.y+12),relative=0,thickness=0);g.y-=16

    g.new('שלב 1 מתוך 4','פרטי הלקוח והנסיעה','פתחו את הלשונית ״לתת הצעה״. הנתונים שתזינו ישמשו לחישוב ולשמירת ההצעה.')
    g.step(1,'זהו את הלקוח','מלאו לפחות פרט אחד: שם פרטי, שם משפחה, מייל או טלפון. מומלץ למלא כמה שיותר פרטים כדי שתזהו את ההצעה בהמשך. בטלפון ציינו גם את קידומת המדינה.')
    g.step(2,'בחרו קבלה והחזרה','לכל צד בחרו עיר ומקום: נמל תעופה, סניף בעיר או מלון / כתובת. כשנבחרת כתובת, יש לציין שם מלון וכתובת מלאה. הקבלה וההחזרה אינן חייבות להיות באותו מקום.')
    g.step(3,'קבעו תאריכים ושעות','בחרו תאריך בעזרת סמל לוח השנה, או הקלידו בפורמט DD.MM.YYYY. בחרו שעה מהרשימה במרווחים של חצי שעה. מועד ההחזרה חייב להיות אחרי מועד הקבלה, גם אם מדובר באותו יום.')
    g.step(4,'בדקו את ההצהרות','ההצהרות מסומנות מראש: גיל וותק הרישיון של הנהגים, כרטיס אשראי על שם הנהג והחובה לציין יציאה למדינות אחרות. בדקו שהן נכונות. אם אחת מהן אינה מתאימה, שנו את הסימון כדי שהבקשה תעבור לבדיקה אישית.')
    g.step(5,'הוסיפו את פרטי הנסיעה','ציינו את מספר הנהגים ואת מספר כיסאות הילדים / הבוסטרים. בשלב ההצעה נדרש רק מספר הכיסאות; את פרטי הילדים ממלאים בעת ההזמנה. סמנו יציאה לאיחוד האירופי / שווייץ ושרשראות שלג לפי הצורך.')
    g.buttons(['חישוב מחירים'])
    g.callout('מה קורה לאחר החישוב?','החלק העליון עובר לבחירת רכבים. אם יש שדה לא תקין, תקבלו הסבר ותצטרכו לתקנו. אם המסלול או תנאי הנהגים דורשים בדיקה, השתמשו בבקשה האישית לעידן. אין צורך להמציא נתון כדי להמשיך.',AMBER,'#87591c')

    g.new('שלב 2 מתוך 4','השוואה ובחירת רכבים','אפשר להרכיב הצעה מכמה קבוצות ומכמה חברות - בהתאם למה שהלקוח מחפש.')
    g.callout('הבדלים בין החברות','הבלוק הסגול נפתח בלחיצה. הוא מרכז הבדלים שימושיים בין החברות, למשל סוג השירות, קבלת הרכב, החזרתו ומדיניות הדלק. קראו גם את התנאים המלאים בהצעה עצמה.',PURPLE,'#654381')
    g.step(1,'פתחו קטגוריה שמעניינת את הלקוח','קטגוריות הרכב מגיעות סגורות. לחצו על הכותרת של הקטגוריה הרצויה כדי לראות את האפשרויות שבתוכה. אפשר לסגור אותה ולעבור לקטגוריה אחרת.')
    g.step(2,'השוו בין האפשרויות','לכל אפשרות בדקו את החברה, הקבוצה והדגמים המייצגים, את המחיר לכל תקופת ההשכרה ואת הפיקדון. הפיקדון מוצג בנפרד מהמחיר; קראו את תנאי החסימה והשחרור בהצעה.')
    g.step(3,'סמנו מה ייכלל בהצעה','סמנו את התיבה ליד כל אפשרות שתרצו להציג ללקוח. ניתן לבחור כמה אפשרויות. אם אותה קבוצה מופיעה גם בקטגוריה אחרת, הסימון נשמר והמערכת מציינת שהיא כבר נבחרה - אין צורך לבחור אותה פעמיים.')
    g.step(4,'עברו לתצוגה המקדימה','אחרי שבחרתם לפחות אפשרות אחת, לחצו על ״יצירת הצעה ותצוגה מקדימה״. ההצעה נשמרת ואפשר לעיין בה לפני שליחה.')
    g.buttons(['יצירת הצעה ותצוגה מקדימה'])
    g.callout('שכחתם משהו בנתוני הנסיעה?','לחצו על כפתור החזרה לפרטי הלקוח והנסיעה. הנתונים נשמרים. לאחר שינוי חשבו שוב את המחירים; בדקו מחדש את האפשרויות שנשארו זמינות.',PALE,BLUE)
    g.para('אם אין מחיר מלא לתאריכים או למסלול שבחרתם, קראו את ההודעה שמופיעה ושלחו בקשה לעידן. אין לראות במחיר שמוצג אישור לזמינות רכב.',size=10.8)

    g.new('שלב 3 מתוך 4','תצוגה מקדימה ושליחת ההצעה','בדקו את ההצעה המלאה לפני שאתם מעבירים אותה ללקוח או מתקדמים להזמנה.')
    g.para('בתצוגה המקדימה מופיעים מספר ההצעה, פרטי ההשכרה, האפשרויות שסימנתם והתנאים. עברו על המסלול, התאריכים, השעות, המחירים, הפיקדון ומה כלול בכל אפשרות.')
    g.buttons(['שליחת ההצעה מהמערכת','העתקת ההצעה'])
    g.callout('למי ההצעה נשלחת?','ללא סימון נוסף: ההצעה נשלחת אליכם, עם עותק לעידן.\nאם מסמנים ״גם ללקוח, בנוסף לשותף ולהעתק לעידן״ וממלאים מייל תקין: גם הלקוח יקבל את ההצעה.\nלסיום לחצו על ״שליחת ההצעה מהמערכת״ והמתינו להודעת הצלחה.',GREEN,'#286241')
    g.heading('העתקה במקום שליחה מתוך המערכת')
    g.para('לחצו על ״העתקת ההצעה״ והדביקו במייל או בהודעה שאתם מכינים. במייל, העיצוב נשמר כשהדפדפן ותוכנת הדואר תומכים בכך. אם ההעתקה האוטומטית נחסמת, יופיע טקסט מסומן שאפשר להעתיק ידנית. העתקה לבדה אינה שולחת דבר.')
    g.heading('חוזרים להצעה קיימת')
    g.para('פתחו את הלשונית ״הצעות״ ובחרו את ההצעה הרצויה. אפשר לקרוא אותה, להעתיק, לשלוח או לבחור מתוכה אפשרות להזמנה. לחזרה לנתונים השתמשו ב״חזרה לעריכת הנתונים והבחירה״. ההצעה הקודמת נשארת שמורה; אחרי התיקון צרו הצעה מעודכנת.')
    g.callout('תוקף המחיר','המחיר נשמר ל-7 ימים ממועד יצירת ההצעה. לאחר מכן הוא תקף כל עוד לא פורסם מחירון חדש של החברה הרלוונטית. אם מתקבלת דרישה לעדכן מחיר, חשבו וצרו הצעה מעודכנת לפני המשך. תוקף מחיר אינו אישור זמינות.',AMBER,'#87591c')

    g.new('שלב 4 מתוך 4','מהצעה לבקשת הזמנה','בחרו אפשרות אחת מתוך הצעה שמורה ורק אז מלאו את פרטי הנהגים והחשבונית.')
    g.step(1,'בחרו את הרכב מתוך ההצעה','מתחת לתצוגה המקדימה מופיעות האפשרויות שנבחרו. לחצו ליד האפשרות הרצויה על ״בחירת אפשרות זו והשלמת פרטי הנהגים״. בדקו שוב את החברה, הקבוצה, הסכום והפיקדון.')
    g.step(2,'מלאו פרטי נהגים ויצירת קשר','מלאו את שם הנהג באנגלית, טלפון כולל קידומת המדינה ומייל איש קשר. השלימו שמות נהגים נוספים בהתאם למספר הנהגים שבחרתם. הוסיפו מספר טיסה כשהוא רלוונטי. שם איש הקשר שהכין את ההצעה אינו מחליף את שם הנהג.')
    g.callout('כיסאות ילדים ובוסטרים','אם בהצעה בחרתם כיסאות, ייפתח בלוק לכל כיסא. זמינים ארבעה שדות: גיל בשנים, גובה בס״מ, משקל בק״ג וסוג הכיסא / הבוסטר. חובה למלא לפחות אחד מהפרטים בכל בלוק בנפרד. מומלץ לספק כמה שיותר מידע מדויק.',PALE,BLUE)
    g.step(3,'חשבונית מיוחדת והערות','אם נדרשת חשבונית עם פרטים מיוחדים, סמנו זאת והשלימו את שם החברה באנגלית ואת כתובת מגורי הקבע באנגלית. הוסיפו מספר מס / זיהוי אם יש, והערות רלוונטיות. אם אין צורך בחשבונית מיוחדת, אין חובה למלא את השדות האלה.')
    g.step(4,'בדקו לפני האישור','סמנו שבדקתם את הנתונים ולחצו על ״בדיקה לפני אישור ההזמנה״. קראו את הסיכום, כולל הנהגים והכיסאות. כדי לתקן, חזרו לעריכת פרטי ההזמנה. כדי לבחור אפשרות אחרת, חזרו להצעה.')
    g.buttons(['אישור ושליחת ההזמנה לחברה'])
    g.callout('הלחיצה האחרונה שולחת בקשה אמיתית','בקשת ההזמנה נשלחת לחברת ההשכרה, עם עותק אליכם ולעידן, ונשמרת במערכת. המתינו לתוצאה. אין לשלוח הזמנה נוספת אם אינכם בטוחים שהפעולה הושלמה - פנו לעידן.',AMBER,'#87591c')

    g.new('אחרי השליחה','מעקב, שינויים ועזרה','הלשונית ״הזמנות״ מרכזת הזמנות שנוצרו דרך הקבינט שלכם בלבד.')
    g.heading('מה המשמעות של מצב ההזמנה?')
    g.callout('ממתינה לאישור','בקשת ההזמנה נשלחה לחברה. זו עדיין אינה הזמנה מאושרת. יש להמתין לאישור הסופי ולמספר ההזמנה של החברה.',PALE,BLUE)
    g.callout('אושרה על ידי עידן','לאחר עדכון האישור במערכת, תוכלו לראות את המצב ואת מספר ההזמנה של חברת ההשכרה, כשהוא הוזן.',GREEN,'#286241')
    g.callout('השליחה לא אושרה / יש לפנות לעידן','ייתכן שההזמנה כבר נשמרה במערכת גם אם המייל לא אושר. אל תיצרו הזמנה חדשה ואל תניחו שהרכב הוזמן. פנו לעידן עם מספר ההצעה או ההזמנה.',AMBER,'#87591c')
    g.heading('שינוי או ביטול של הזמנה קיימת')
    g.para('פתחו את ההזמנה ובחרו בקשת שינוי או ביטול. כתבו במדויק מה צריך להשתנות ושלחו את הבקשה לעידן. הבקשה אינה משנה או מבטלת את ההזמנה אוטומטית; יש להמתין לטיפול ולאישור ממנו.')
    g.heading('בקשה מיוחדת? עידן יבדוק.')
    g.para('הבלוק הבז׳ בתחתית המסך הוא פנייה אישית, נפרדת משלבי יצירת ההצעה. השתמשו בו למסלול לא רגיל, לתנאי נהג שאינם מתאימים להצהרות, למחיר שלא התקבל או לשאלה שדורשת בדיקה. פרטו מה מבוקש וציינו את מספר ההצעה או ההזמנה אם יש.')
    g.heading('לא קיבלתם מייל או לא מצליחים להיכנס?')
    g.para('בדקו אם הופיעה הודעת הצלחה, אם כתובת המייל נכונה וגם את תיקיית הספאם. אם מוצגת שגיאה או שהמצב אינו ברור, פנו לעידן לפני ניסיון הזמנה נוסף. לחשבון שננעל או לסיסמה שנשכחה - בקשו ממנו עזרה.',size=10.8)
    g.text(EMAIL,M,g.y,10.6,True,BLUE,False);g.c.linkURL('mailto:'+EMAIL,(M,g.y-3,225,g.y+12),relative=0,thickness=0)
    g.text(PHONE,W-M-pdfmetrics.stringWidth(PHONE,'GuideBold',10.6),g.y,10.6,True,BLUE,False);g.c.linkURL('https://wa.me/48533100636',(W-190,g.y-3,W-M,g.y+12),relative=0,thickness=0);g.y-=20
    g.finish();g.c.save()
    print(OUT)


if __name__=='__main__':build()
