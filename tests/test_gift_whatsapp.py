"""Gift-date instructions must follow the owner's WhatsApp booking workflow."""
import json,re,unittest
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]
class Text(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.parts=[]
 def handle_starttag(self,t,a):
  if t in ['script','style']:self.skip+=1
 def handle_endtag(self,t):
  if t in ['script','style']:self.skip=max(0,self.skip-1)
 def handle_data(self,d):
  if not self.skip:self.parts.append(d)
class GiftWhatsAppTests(unittest.TestCase):
 def test_gift_landings_explain_date_booking_by_whatsapp(self):
  for name in ['regalar-vuelo-en-globo.html','regalar-vuelo-en-globo-segovia.html','en/gift-hot-air-balloon-segovia.html']:
   s=(ROOT/name).read_text();p=Text();p.feed(s);text=' '.join(' '.join(p.parts).split())
   with self.subTest(page=name):
    self.assertRegex(text,r'WhatsApp al 614 007 056|WhatsApp at \+34 614 007 056')
    self.assertRegex(text,r'no reserva fecha ni plazas|does not reserve a date or seats')
    self.assertIn('https://wa.me/34614007056',s)
 def test_changed_faq_answers_are_visible_and_not_only_structured(self):
  for name in ['regalar-vuelo-en-globo.html','regalar-vuelo-en-globo-segovia.html','en/gift-hot-air-balloon-segovia.html']:
   s=(ROOT/name).read_text();p=Text();p.feed(s);visible=' '.join(' '.join(p.parts).split())
   for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>',s,re.S):
    for node in json.loads(block).get('@graph',[]):
     if node.get('@type')=='FAQPage':
      for q in node['mainEntity']:
       answer=q['acceptedAnswer']['text']
       if 'WhatsApp' in answer:
        self.assertIn(' '.join(answer.split()),visible)
 def test_legal_and_llm_summaries_explain_the_same_channel(self):
  for name in ['legales.html','llms.txt','llms-full.txt']:
   s=(ROOT/name).read_text()
   with self.subTest(page=name):
    self.assertIn('WhatsApp',s)
    self.assertRegex(s,r'referencia del billete|voucher reference')
 def test_no_static_page_sends_gift_holders_to_an_automatic_redemption_form(self):
  for p in ROOT.rglob('*.html'):
   self.assertNotRegex(p.read_text(),r'href=[\"\'][^\"\']*/canjear(?:[?\"\'])')
if __name__=='__main__':unittest.main()
