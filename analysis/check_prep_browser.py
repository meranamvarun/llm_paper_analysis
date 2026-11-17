"""End-to-end checks using an isolated browser; never a user's browser profile."""
import json
from pathlib import Path
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/student_strategy/20261117/site_qa'
URL='http://127.0.0.1:8765/site/'
KEY='clat-pg-study-studio-v1'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    downloads=OUT/'downloads';downloads.mkdir(exist_ok=True)
    options=Options()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=1440,1100')
    options.add_experimental_option('prefs',{'download.default_directory':str(downloads),'download.prompt_for_download':False})
    driver=webdriver.Chrome(options=options)
    wait=WebDriverWait(driver,15)
    results={}
    a=json.loads((ROOT/'site/content-foundations.json').read_text(encoding='utf-8'))
    b=json.loads((ROOT/'site/content-breadth.json').read_text(encoding='utf-8'))
    questions={q['id']:q for d in [a,b] for q in d['questions']+[q for p in d['passages'] for q in p['questions']]}

    def el(selector):return driver.find_element(By.CSS_SELECTOR,selector)
    def click(selector):
        element=el(selector);driver.execute_script('arguments[0].scrollIntoView({block:"center",behavior:"instant"})',element);element.click()
    def route(value,selector):
        driver.execute_script('location.hash=arguments[0]',value)
        wait.until(lambda d:d.find_elements(By.CSS_SELECTOR,selector))
    def state():return json.loads(driver.execute_script('return localStorage.getItem(arguments[0])',KEY))
    def answer(index,confidence='medium'):
        click(f'input[name="answer"][value="{index}"]')
        click(f'input[name="confidence"][value="{confidence}"]')
        click('#answer-form button[type="submit"]')

    try:
        driver.get(URL)
        wait.until(lambda d:d.find_elements(By.CSS_SELECTOR,'.hero'))
        assert '19' in el('.hero-side').text
        driver.save_screenshot(str(OUT/'desktop-today.png'))
        results['initial_countdown_19_days']=True
        route('learn','.topic-grid')
        assert len(driver.find_elements(By.CSS_SELECTOR,'.topic-card'))==16
        el('#library-search').send_keys('restrictions')
        assert len(driver.find_elements(By.CSS_SELECTOR,'.topic-card'))==1
        route('learn/constitutional-rights','.lesson')
        assert len(driver.find_elements(By.CSS_SELECTOR,'.lesson-section'))>=5
        el('#lesson-note').send_keys('<img src=x onerror=alert(1)> My rule and exception.')
        click('[data-action="save-note"]')
        click('[data-action="mark-read"]')
        driver.refresh();wait.until(lambda d:d.find_elements(By.CSS_SELECTOR,'.lesson'))
        assert 'My rule' in el('#lesson-note').get_attribute('value')
        assert not driver.find_elements(By.CSS_SELECTOR,'.lesson img')
        results['lesson_search_notes_reload_escaped']=True
        click('[data-action="topic-recall"]')
        wait.until(lambda d:d.find_elements(By.CSS_SELECTOR,'.flashcard'))
        click('[data-action="reveal-card"]')
        assert not driver.find_elements(By.CSS_SELECTOR,'.answer-block')
        el('#card-attempt').send_keys('Article 19 is framed for citizens; check the restriction clause.')
        click('[data-action="reveal-card"]')
        assert driver.find_elements(By.CSS_SELECTOR,'.answer-block')
        assert 'answer-block' in driver.switch_to.active_element.get_attribute('class')
        driver.save_screenshot(str(OUT/'desktop-flashcard.png'))
        click('[data-rating="good"]')
        assert len(state()['cards'])==1
        click('[data-action="end-recall"]')
        driver.refresh();wait.until(lambda d:d.find_elements(By.CSS_SELECTOR,'[data-action="start-recall"]'))
        assert len(state()['cards'])==1
        results['recall_attempt_gate_rating_due_persistence']=True

        route('learn/constitutional-rights','.lesson')
        click('[data-action="topic-quiz"]')
        quiz=state()['quizDraft'];first=questions[quiz['ids'][0]]
        answer((first['correctIndex']+1)%4,'high')
        assert driver.find_elements(By.CSS_SELECTOR,'.feedback.wrong')
        assert 'feedback' in driver.switch_to.active_element.get_attribute('class')
        click('[data-action="quiz-next"]')
        click('[data-action="quiz-skip"]')
        quiz=state()['quizDraft'];answer(questions[quiz['ids'][2]]['correctIndex'],'low')
        click('[data-action="quiz-next"]')
        answer(questions[quiz['ids'][3]]['correctIndex'],'high')
        click('[data-action="finish-quiz"]')
        result=state()['quizResults'][-1]
        assert (result['correct'],result['wrong'],result['skipped'],result['net'])==(2,1,1,1.75)
        assert len(state()['attempts'])==3
        results['quiz_confidence_feedback_skip_scoring']=True

        route('mistakes','.mistake-card')
        assert len(driver.find_elements(By.CSS_SELECTOR,'.mistake-card'))==2
        qid=first['id']
        el(f'[data-repair-rule="{qid}"]').send_keys('Apply the right-holder rule and keep its exception.')
        click(f'[data-action="save-repair"][data-question="{qid}"]')
        click(f'[data-action="retest"][data-question="{qid}"]')
        assert not driver.find_elements(By.CSS_SELECTOR,'.feedback')
        answer(first['correctIndex'],'high')
        click('[data-action="finish-quiz"]')
        assert state()['repairs'][qid]['fixed'] is True
        route('mistakes','.mistake-card')
        assert 'Retested correctly' in el('#main').text
        assert len(driver.find_elements(By.CSS_SELECTOR,'.mistake-card'))==2
        results['mistake_repair_blind_retest_history_retained']=True

        route('practice','.results-score')
        click('[data-action="end-results"]')
        Select(el('#quiz-topic')).select_by_value('contract')
        Select(el('#quiz-count')).select_by_value('4')
        click('#quiz-simulation')
        click('[data-action="start-quiz"]')
        quiz=state()['quizDraft'];answer(questions[quiz['ids'][0]]['correctIndex'])
        assert not driver.find_elements(By.CSS_SELECTOR,'.feedback')
        driver.refresh();wait.until(lambda d:d.find_elements(By.CSS_SELECTOR,'.question-panel'))
        assert state()['quizDraft']['committed'][0]
        driver.execute_script('const k=arguments[0],s=JSON.parse(localStorage.getItem(k));s.quizDraft.deadline=Date.now()-1000;localStorage.setItem(k,JSON.stringify(s));',KEY)
        driver.refresh();wait.until(lambda d:d.find_elements(By.CSS_SELECTOR,'.results-score'))
        assert state()['quizDraft'] is None
        assert state()['quizResults'][-1]['skipped']==3
        results['simulation_hides_feedback_reload_resume_expiry_submits']=True

        click('[data-action="end-results"]')
        assert len(driver.find_elements(By.CSS_SELECTOR,'.passage-card'))==8
        click('[data-action="start-passage"]')
        assert len(el('.passage-panel p').text.split())>=170
        driver.save_screenshot(str(OUT/'desktop-passage.png'))
        click('[data-action="discard-quiz"]');driver.switch_to.alert.accept()
        wait.until(lambda d:d.find_elements(By.CSS_SELECTOR,'.passage-card'))
        results['eight_original_passage_sets_render']=True

        route('plan','.calendar')
        assert len(driver.find_elements(By.CSS_SELECTOR,'.day-card'))==19
        click('input[data-day="2026-11-17"]')
        driver.refresh();wait.until(lambda d:d.find_elements(By.CSS_SELECTOR,'.calendar'))
        assert el('input[data-day="2026-11-17"]').is_selected()
        results['calendar_19_days_checks_persist']=True

        click('[data-action="settings"]')
        existing=set(downloads.glob('*.json'))
        click('[data-action="export"]')
        wait.until(lambda d:len(set(downloads.glob('*.json'))-existing)>0)
        backup=next(iter(set(downloads.glob('*.json'))-existing))
        saved=json.loads(backup.read_text(encoding='utf-8'))
        assert saved['schema']==1 and saved['notes']['constitutional-rights']
        bad=OUT/'invalid-backup.json';bad.write_text('{"schema":999}',encoding='utf-8')
        before=state()
        el('#import-file').send_keys(str(bad))
        wait.until(lambda d:'Import rejected' in el('#import-status').text)
        assert state()==before
        saved['settings']['minutes']=90
        restored=OUT/'valid-backup.json';restored.write_text(json.dumps(saved),encoding='utf-8')
        el('#import-file').send_keys(str(restored));wait.until(lambda d:alert_present(d));driver.switch_to.alert.accept()
        wait.until(lambda d:not el('#settings-dialog').is_displayed())
        assert state()['settings']['minutes']==90
        results['actual_export_invalid_import_preserves_valid_import_restores']=True

        # Isolated-profile storage denial must not pretend that progress is saved.
        denial=driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument',{'source':"Storage.prototype.setItem=function(){throw new DOMException('Test storage denied','QuotaExceededError')};"})
        driver.refresh();wait.until(lambda d:'Not saving' in el('#save-status').text)
        assert driver.find_elements(By.CSS_SELECTOR,'.storage-warning')
        driver.execute_cdp_cmd('Page.removeScriptToEvaluateOnNewDocument',{'identifier':denial['identifier']})
        results['storage_denial_visible']=True

        driver.refresh();wait.until(lambda d:d.find_elements(By.CSS_SELECTOR,'.calendar'))
        driver.execute_script('localStorage.removeItem(arguments[0])',KEY)
        driver.get(URL+'#today');driver.refresh();wait.until(lambda d:d.find_elements(By.CSS_SELECTOR,'.hero'))
        driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        mobile={}
        for page,selector in [('today','.hero'),('learn','.topic-grid'),('practice','.practice-grid'),('mistakes','.empty-state'),('plan','.calendar'),('sources','.source-card')]:
            route(page,selector)
            assert driver.execute_script('return window.innerWidth')==390
            assert driver.execute_script('return document.documentElement.scrollWidth<=window.innerWidth'),page
            mobile[page]=True
            if page in ['today','learn','practice']:driver.save_screenshot(str(OUT/f'mobile-{page}.png'))
        route('learn/contract','.lesson')
        assert driver.execute_script('return document.documentElement.scrollWidth<=window.innerWidth')
        mobile['lesson']=True
        click('[data-action="topic-recall"]');wait.until(lambda d:d.find_elements(By.CSS_SELECTOR,'.flashcard'))
        assert driver.execute_script('return document.documentElement.scrollWidth<=window.innerWidth')
        driver.save_screenshot(str(OUT/'mobile-flashcard.png'))
        mobile['recall']=True
        route('practice','.practice-grid')
        click('[data-action="start-passage"]')
        assert driver.execute_script('return document.documentElement.scrollWidth<=window.innerWidth')
        click('[data-passage-toggle] > summary')
        wait.until(lambda d:state()['quizDraft'].get('passageCollapsed') is True)
        quiz=state()['quizDraft']
        answer(questions[quiz['ids'][0]]['correctIndex'],'high')
        click('[data-action="quiz-next"]')
        assert not el('[data-passage-toggle]').get_attribute('open')
        assert driver.execute_script('return document.documentElement.scrollWidth<=window.innerWidth')
        driver.save_screenshot(str(OUT/'mobile-passage.png'))
        mobile['passage_quiz_and_persistent_collapse']=True
        results['keyboard_focus_after_reveal_and_feedback']=True
        results['mobile_390_no_body_overflow']=mobile
        logs=driver.get_log('browser')
        # Deliberate storage denial is handled and should not produce console errors.
        assert not [r for r in logs if r['level']=='SEVERE'],logs
        results['browser_console']=logs
        results['project_subpath_asset_loading']=True
        results['browser']='isolated headless Chrome via Selenium'
        (OUT/'browser-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        print(json.dumps(results))
    except Exception:
        driver.save_screenshot(str(OUT/'failure.png'))
        (OUT/'failure-state.json').write_text(json.dumps({'url':driver.current_url,'main':driver.find_element(By.ID,'main').text,'logs':driver.get_log('browser')},ensure_ascii=True,indent=2),encoding='utf-8')
        raise
    finally:driver.quit()


def alert_present(driver):
    try:driver.switch_to.alert.text;return True
    except Exception:return False


if __name__=='__main__':main()
