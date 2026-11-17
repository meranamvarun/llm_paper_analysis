"""Execute real browser ES module: no Node installation required."""
import functools
import http.server
import json
from pathlib import Path
import threading
import unittest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT = Path(__file__).resolve().parents[2]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class PrepCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(QuietHandler, directory=str(ROOT))
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        options = Options()
        options.add_argument('--headless=new')
        cls.driver = webdriver.Chrome(options=options)
        cls.driver.get(f'http://127.0.0.1:{cls.server.server_port}/')
        result = cls.driver.execute_async_script("""const done=arguments[0];
        import('./site/core.js').then(m=>{window.Core=m;done('loaded')}).catch(e=>done(String(e)));""")
        if result != 'loaded':
            cls.driver.quit()
            cls.server.shutdown()
            cls.server.server_close()
            raise AssertionError('Required core module unavailable: ' + result)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        cls.server.shutdown()
        cls.server.server_close()

    def js(self, script):
        return self.driver.execute_script(script)

    def test_calendar_and_taper(self):
        self.assertEqual(self.js("return Core.daysBetween('2026-11-17','2026-12-06')"),19)
        self.assertEqual(self.js("return Core.addDays('2028-02-28',1)"),'2028-02-29')
        self.assertFalse(self.js("return Core.validDate('2026-02-30')"))
        self.assertEqual(self.js("return Core.newCardLimit(180,'2026-12-03','2026-12-06')"),0)
        self.assertEqual(self.js("return Core.dayKey(new Date('2026-11-16T20:00:00Z'))"),'2026-11-17')

    def test_review_and_new_cap(self):
        result = self.js("""const now=Date.parse('2026-11-17T04:00:00Z');
        const good=Core.rateCard(null,'good',now,'2026-12-06');
        const again=Core.rateCard(good,'again',now,'2026-12-06');
        const late=Core.rateCard({...good,interval:14},'easy',Date.parse('2026-12-04T04:00:00Z'),'2026-12-06');
        return {good,again,late};""")
        self.assertEqual(result['good']['dueDate'],'2026-11-18')
        self.assertEqual(self.js("const n=Date.parse('2026-11-17T04:00:00Z');return Core.rateCard(null,'again',n,'2026-12-06').dueAt-n"),600000)
        self.assertLessEqual(result['late']['dueDate'],'2026-12-05')
        self.assertEqual(result['again']['lapses'],1)
        self.assertGreater(self.js("const n=Date.parse('2026-12-05T04:00:00Z');return Core.rateCard(null,'good',n,'2026-12-06').dueAt-n"),3600000)

    def test_scoring_and_skip(self):
        self.assertEqual(self.js("return Core.scoreAnswers([{correctIndex:1},{correctIndex:0},{correctIndex:2}],[1,1,null])"),
                         dict(correct=1,wrong=1,skipped=1,net=0.75))

    def test_state_rejects_and_preserves(self):
        self.assertTrue(self.js("return Core.validateState(Core.freshState()).ok"))
        self.assertFalse(self.js("return Core.validateState({schema:999}).ok"))
        self.assertFalse(self.js("const s=Core.freshState();s.settings.examDate='2026-02-30';return Core.validateState(s).ok"))
        self.assertFalse(self.js("const s=Core.freshState();s.cards.x={dueAt:'bad'};return Core.validateState(s).ok"))
        self.assertFalse(self.js("const s=Core.freshState();s.readTopics=['a','a'];return Core.validateState(s).ok"))

    def test_due_queue_and_daily_new_limit(self):
        self.assertEqual(self.js("""const s=Core.freshState();const now=Date.parse('2026-11-17T04:00:00Z');
        s.cards.a={...Core.rateCard(null,'again',now-20*60000,s.settings.examDate),introduced:'2026-11-17'};
        return Core.cardQueue([{id:'a'},{id:'b'},{id:'c'}],s,now,1).map(x=>x.id);"""),['a'])


if __name__ == '__main__':
    unittest.main()
