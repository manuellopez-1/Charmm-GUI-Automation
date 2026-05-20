# Manuel Alejandro Lopez 2025

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException

import os
import json
import time
import sys 
import numpy as np
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import WebDriverException
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.webdriver.chrome.options import Options
import threading
import sys
#import fcntl
from contextlib import contextmanager #these mf's wanna stop me from hitting next with multiple processes at the same time
CHARMMGUI_LOCKFILE = "/tmp/charmm_gui_next_step.lock"

@contextmanager #so gonna use a locking mechanism to stop multiple from submitting concurrently
def charmmgui_submit_lock():
    with open(CHARMMGUI_LOCKFILE, "w") as lock_f:
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_f, fcntl.LOCK_UN)


def findallsimilar(browser, entry):
    tag   = entry.get("tag")
    attrs = entry.get("attrs", {})
    text = entry.get("text").strip()
    xpath = f"//{tag}"
    for name, value in attrs.items():
        xpath += f"[@{name}='{value}']"
    if text:
        xpath += f"[normalize-space(.)='{text}']"
    return browser.find_elements(By.XPATH, xpath)

def betterclick(browser, entry):
    el = entry.get("element")
    last_error = None

    if el is not None:
        try:
            browser.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            el.click()
            return  # success
        except (ElementNotInteractableException,StaleElementReferenceException,ElementClickInterceptedException, WebDriverException,) as e:
            last_error = e
    candidates = findallsimilar(browser,{"tag":  entry.get("tag"),"attrs": entry.get("attrs"),"text": entry.get("text"),},)
    if not candidates:
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"No identical candidates found for entry: {entry}")

    for cand in candidates:
        try:
            if el is not None and hasattr(el, "id") and cand.id == el.id:
                continue
        except Exception:
            pass

        try:
            browser.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", cand
            )
            cand.click()
            return 
        except (ElementNotInteractableException,StaleElementReferenceException,ElementClickInterceptedException,WebDriverException,) as e:
            last_error = e
            continue
    if last_error is not None:
        raise last_error


def login(username, password,wait):
    loginbutton = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Login']")))
    loginbutton.click()

    userbox = wait.until(EC.presence_of_element_located((By.NAME,"email"))) #wish they made these functions more complex
    passwordbox = wait.until(EC.presence_of_element_located((By.NAME,"password")))
    userbox.clear()
    userbox.send_keys(username)
    passwordbox.send_keys(password)
    passwordbox.send_keys(Keys.RETURN)

def clicklist(browser,mute): 
    elements = browser.find_elements(By.XPATH,"//a | //button | //input[@type='submit'] | //input[@type='button']") 
    buttons = [] 
    for e in elements: 
        try: 
            text = e.text.strip() 
        except: 
            text = "" 
        try: 
            tag = e.tag_name 
        except: 
            tag = None 
        attrs = {} 
        for attr in ["id", "class", "name", "href", "value", "type"]: 
            try: 
                v = e.get_attribute(attr) 
                if attr == "value" or attr == "id" or attr == "type":
                    attrs[attr] = v if v is not None else ""
                else:
                    if v:         
                        attrs[attr] = v
            except: 
                pass 
        buttons.append({"element": e, "tag": tag,"text": text,"attrs": attrs}) 
        if mute ==0:
            print('tag: ' + str(tag) + ' , text: ' + str(text) + ' , attributes: ' + str(attrs) + ' \n')
    return buttons





def mostsimilar(inp, buttons):
    query = inp.strip().lower()
    if not query:
        return None
    for b in buttons:
        attrs = b.get("attrs", {}) or {}
        candidates = [
            (b.get("text") or ""),attrs.get("name") or "",attrs.get("value") or "",attrs.get("id") or "",attrs.get("href") or "",attrs.get("onclick") or "",]
        for c in candidates:
            c_low = c.strip().lower()
            if query == c_low or query in c_low:
                return b
    return None



def steplinks(browser, step_value):
    links = []
    rows = browser.find_elements(By.XPATH, "//table//tr")  

    for r in rows:
        cells = r.find_elements(By.TAG_NAME, "td")
        if len(cells) < 4:
            continue  
        step_text = cells[3].text.strip()
        if step_text == str(step_value):
            try:
                a = cells[0].find_element(By.TAG_NAME, "a")
                links.append(a)
            except NoSuchElementException:
                continue

    return links
    

def record(logs, button, filename):
    if not button:
        return
    entry = {"action": "click", "text": button.get("text", ""),"tag": button.get("tag", ""),"attrs": button.get("attrs", {})}
    logs.append(entry)
    with open(filename, "w") as f:
        json.dump(logs, f, indent=4)

import json

def record2(logs, field_name, entry_text, filename, ndx=0, hit_enter=False):
    entry = {
        "action": "type",
        "field": field_name,
        "text": entry_text,
        "hit_enter": hit_enter,
        "match_index": int(ndx)
    }
    logs.append(entry)
    with open(filename, "w") as f:
        json.dump(logs, f, indent=4)
def listtypebox(browser,mute):
    inputs = browser.find_elements(By.XPATH, "//input | //textarea")
    if mute ==0:
        print("Available Boxes to Type In: \n")
    boxes = []
    names = ''
    for e in inputs:
        try:
            t = (e.get_attribute("type") or "").lower()
            if t in ["text", "email", "password", "search", "number", "tel"] or e.tag_name == "textarea":
                info = {"element": e,"tag": e.tag_name,"type": t,"name": e.get_attribute("name"),"id": e.get_attribute("id"),"placeholder": e.get_attribute("placeholder"),"value": e.get_attribute("value"),}
                boxes.append(info)
                if info["name"]:
                    names += info["name"] + " , "
        except StaleElementReferenceException:
            continue
    if mute ==0:
        print(names)
    return boxes

def findtypeboxes(name, typeboxes):
    query = name.strip().lower()
    if not query:
        return []
    matches = []
    for b in typeboxes:
        name = (b.get("name") or "").strip().lower()
        placeholder = (b.get("placeholder") or "").strip().lower()
        if query in (name, placeholder):
            matches.append(b)
    return matches
    

def findtypebox(name, typeboxes):
    matches = findtypeboxes(name, typeboxes)
    return matches[0] if matches else None

""" This worked until there were two identical typeboxes
def findtypebox(name_query, typeboxes):
    query = name_query.strip().lower()
    if not query:
        return None
    for b in typeboxes:
        name = (b.get("name") or "").strip().lower()
        placeholder = (b.get("placeholder") or "").strip().lower()
        if query in (name, placeholder):
            return b
    return None
"""
def NextRecorder(logs, filename):
    entry = {"action": "next_step"}
    logs.append(entry)
    with open(filename, "w") as f:
        json.dump(logs, f, indent=4)

def listDropDowns(browser,mute):
    selects = browser.find_elements(By.TAG_NAME, "select")
    dropdowns = []
    if mute ==0:
        print("\n Dropdowns: \n")
    for i, s in enumerate(selects):
        name = s.get_attribute("name") or ""
        id_ = s.get_attribute("id") or ""
        options = s.find_elements(By.TAG_NAME, "option")
        option_texts = [o.text.strip() for o in options]
        dropdowns.append({"element": s,"name": name,"id": id_,"options": options,"option_texts": option_texts,})
        if mute ==0:
            print(str(i) + ' : ' + ' Name: ' +str(name) + ', ID: ' + str(id_))
        if mute ==0:
            for j, t in enumerate(option_texts):
                print('      ' + str(j) +' , ' + str(t))
    if mute ==0:
        print("\n")
    return dropdowns

def DropDownRecord(logs, dropdown_name, dropdown_id, option_text,filename):
    entry = {"action": "dropdown","dropdown_name": dropdown_name,"dropdown_id": dropdown_id,"option": option_text,}
    logs.append(entry)
    with open(filename, "w") as f:
        json.dump(logs, f, indent=4)

def BubbleList(browser,mute):
    inputs = browser.find_elements(
        By.XPATH, "//input[@type='checkbox'] | //input[@type='radio']"
    )
    checkables = []
    if mute ==0:
        print("Bubbles: \n")

    for i, e in enumerate(inputs):
        try:
            t = (e.get_attribute("type") or "").lower()
            name = e.get_attribute("name") or ""
            value = e.get_attribute("value") or ""
            checked_attr = e.get_attribute("checked")
            checked = bool(checked_attr)

            label_text = ""
            elem_id = e.get_attribute("id")
            if elem_id:
                labels = browser.find_elements(By.XPATH, f"//label[@for='{elem_id}']")
                if labels:
                    label_text = (labels[0].text or "").strip()

            if not label_text:
                try:
                    row = e.find_element(By.XPATH, "./ancestor::tr[1]")
                    label_text = (row.text or "").strip()
                except (StaleElementReferenceException, NoSuchElementException):
                    label_text = ""

            info = {"element": e,"type": t,"name": name,"value": value,"label": label_text,"checked": checked,}
            checkables.append(info)
            status = "checked" if checked else "unchecked"
            if mute ==0:
                print(str(i) + ': ' +'(' + str(t) + ') , Name: ' + str(name) + ' , value: ' + str(value) +' , label: ' + str(label_text) + ' , (' + str(status) + ')')

        except StaleElementReferenceException:
            continue
    if mute ==0:
        print("\n")
    return checkables


def CheckBoxRecord(logs, input_type, name, value, checked,filename, label=""):
    entry = {"action": "check","input_type": input_type,"name": name,"value": value,"label": label,"checked": checked,}
    logs.append(entry)
    with open(filename, "w") as f:
        json.dump(logs, f, indent=4)



def execute(browser,which,mute,last):
    action = which.get('action')
    if action =='click':
        nom = which.get('text').strip()
        if not nom:
            attrs = which.get("attrs", {})
            nom = attrs.get("value", "").strip()
        #A = None
        #while A is None:
        buttons = clicklist(browser,mute) #wait for loading
        A = mostsimilar(nom,buttons)
        #time.sleep(3)
        betterclick(browser, A)
        #A['element'].click()
    elif action =='type':
        field = which.get('field')
        enter = bool(which.get('hit_enter'))
        ndx = int(which.get('match_index',0))
        A = None
        while A is None:
            boxes =listtypebox(browser,mute)
            B = findtypeboxes(field, boxes)
            A = B[ndx]
            #time.sleep(3)
        
        A['element'].clear()
        A['element'].send_keys(which.get('text'))
        if enter ==True:
            A['element'].send_keys(Keys.RETURN)
    if action == 'next_step':
        time.sleep(30)
        with charmmgui_submit_lock():
            next_step = browser.find_element(
                        By.XPATH,
                        "//table[@class='nav_entry' and contains(normalize-space(.), 'Next Step')]"
                    )
            old_page = browser.find_element(By.TAG_NAME, "html")
            next_step.click()
            try:
                WebDriverWait(browser, 10*60).until(EC.staleness_of(old_page))
            except TimeoutException:
                if mute == 0:
                    print("[WARN] Page did not change after 10 minutes — continuing anyway")
                return
    elif action =='dropdown':
        dropname = which.get('dropdown_name')
        dropid = which.get('dropdown_id')
        target = None
        while target ==None:
            dropdowns = listDropDowns(browser,mute)
            for possible in dropdowns:
                if dropid ==possible['id'] or dropname == possible['name']:
                    target = possible
                    break
            time.sleep(3)
        chosen = None #assuming webpage loaded cus last part work
        for el, txt in zip(target['options'], target['option_texts']):
            if txt.strip() == which.get('option').strip():
                chosen = el
                break
        chosen.click()
    elif action =='check':
        target = None
        while target ==None:
            bubbles = BubbleList(browser,mute)
            for b in bubbles:
                if (b['type']  == which['input_type'] and b['name']  == which['name'] and b['value'] == which['value']): 
                    target = b
                    break
            time.sleep(3)
        target['element']
        checked = bool(which.get("checked"))
        if checked and not target['checked']:
            target['element'].click()
        elif not checked and target['checked']:
            target['element'].click()
    elif action == 'records':
        target_key = which.get("target")
        elem = None
        while elem is None:
            lip_buttons = listrecords(browser,mute)
            for b in lip_buttons:
                if target_key and b["target"] == target_key:
                    elem = b["element"]
                    break
            time.sleep(3)
        elem.click()

def listrecords(browser,mute):
    imgs = browser.find_elements(By.XPATH, "//img[contains(@onclick, 'liptype_toggle')]")
    lip_buttons = []
    if mute ==0:
        print("Extend window buttons: ")
    for i, e in enumerate(imgs):
        try:
            onclick = e.get_attribute("onclick") or ""
        except StaleElementReferenceException:
            continue
        target = None
        parts = onclick.split('"')
        if len(parts) >= 2:
            target = parts[1]
        info = {"element": e,"onclick": onclick,"target": target,}
        lip_buttons.append(info)
        if mute ==0:
            print(str(i) + ': onclick: ' + str(onclick) + ', target: ' + str(target))
    if mute ==0:
        print('\n')
    return lip_buttons

progress_lock = threading.Lock()
worker_progress = []
worker_totals = []
stop_progress = threading.Event()

def progressbars(num_workers):
    with progress_lock:
        for i in range(num_workers):
            done  = worker_progress[i]
            total = worker_totals[i]
            pct = int(100 * done / total) if total > 0 else 0
            print("Core " + str(i+1) + ' : ' + str(np.round(pct,3)) + ' % (' + str(done) + '/' + str(total)+ ')' ) 
        print("\n" + "----") #should maybe do more ---


def recordrecords(logs, target, onclick, filename):
    entry = {"action": "records","target": target, "onclick": onclick, }
    logs.append(entry)
    with open(filename, "w") as f:
        json.dump(logs, f, indent=4)

def parallelsubmission(id, username, password, howmany,read):
    global worker_progress
    url = 'https://www.charmm-gui.org/'
    
    for i in range(int(howmany)):
        #options = Options()
        #options.add_argument("--headless=new")
        #browser = webdriver.Chrome(options=options)
        browser = webdriver.Chrome()
        browser.get(url)
        wait = WebDriverWait(browser, 15)
        login(username, password,wait)
        
        for I in range(len(read)):
            entry = read[I]
            if I ==len(read)-1:
                last = 1
            else:
                last = 0
            execute(browser,entry,1,last)
            with progress_lock:
                worker_progress[id] +=1
        browser.close()

def main():
    usrnm = input("Username: ")
    psswrd =input("Password: ")
    typ = int(input("Action: Create Action File (0), Replay Action File (1), Append Action File (2): , Download TGZ Files (3) "))
    if typ !=3:
        Actionfile = input("Action File Name: ")
    if typ ==0:
        url = 'https://www.charmm-gui.org/'
        browser = webdriver.Chrome()
        browser.get(url)

        wait = WebDriverWait(browser, 15)
        logs = []

        login(usrnm, psswrd,wait)
        clickid = 1
        while clickid !=0:
            buttontype = int(input("Button Type: Click (1), Type in (2), Drop Down (3), Bubbles (4), next (5), Extend (6),  Exit (7): "))
            if buttontype ==1:
                buttons = clicklist(browser,0)
                inp = input('Button: ')
                whichone = mostsimilar(inp, buttons)
                record(logs, whichone,Actionfile)
                #whichone['element'].click()
                betterclick(browser, whichone)
            elif buttontype ==2:
                typboxes = listtypebox(browser,0)
                #print(typboxes)
                inp = input('Box Name: ')
                matches = findtypeboxes(inp, typboxes)
                print(matches)
                if len(matches)>1:
                    for i in range(len(matches)):
                        m = matches[i]
                        print(' '+str(i) + ': name: ' + m.get('name') + ' , id: ' + m.get('id') + ' , placeholder: ' + m.get('placeholder') + ' , type: ' + m.get('type') )
                    indexinquestion = int(input('Index: '))
                else:
                    indexinquestion = 0
                typebox = matches[indexinquestion]
                inp2 = input('Entry: ')
                typebox['element'].clear()
                typebox['element'].send_keys(inp2)
                inp3 = input('Hit Enter? yes (1)/ no (2): ')
                hitenter = (inp3=="1")
                if hitenter:
                    typebox['element'].send_keys(Keys.RETURN)
                record2(logs, inp, inp2,Actionfile, indexinquestion,hitenter)
            elif buttontype ==5:
                next_step = browser.find_element(By.XPATH,"//table[@class='nav_entry' and contains(normalize-space(.), 'Next Step')]") #turns out next isn't a button but a link
                NextRecorder(logs,Actionfile)
                next_step.click()
            elif buttontype == 3:
                drops = listDropDowns(browser,0)
                usr = int(input("Select dropdown index: "))
                dropdown = drops[usr]
                choice = int(input("Select Option Index: "))
                element = dropdown["options"][choice]
                text = dropdown["option_texts"][choice]
                element.click()
                DropDownRecord(logs,dropdown["name"],dropdown["id"],text,Actionfile)
            elif buttontype ==4:
                bubbles = BubbleList(browser,0)
                usr = int(input("Select Bubble Index: "))
                element = bubbles[usr]["element"]
                element.click()
                CheckBoxRecord(logs,bubbles[usr]["type"],bubbles[usr]["name"],bubbles[usr]["value"],True,Actionfile,label=bubbles[usr]["label"])
            elif buttontype ==6:
                extends = listrecords(browser,0)
                usr = int(input("Select Extend Index: "))
                chosen = extends[usr]
                chosen['element'].click()
                recordrecords(logs, chosen['target'],chosen['onclick'],Actionfile)

            else:
                return 
    elif typ ==1:
        with open(Actionfile,'r') as f:
            read = json.load(f)

        numcores =  os.cpu_count()-1 #this way there's a free core for the other functions of the computer?
        totalcreations = int(input('Total Iterations: '))
        ntasks = totalcreations//numcores 
        extraones = totalcreations% numcores
        tasksper = [0]*numcores
        for i in range(numcores):
            tasksper[i] = ntasks
            if i<extraones:
                tasksper[i] +=1


        global worker_progress, worker_totals
        worker_progress = [0] * numcores
        worker_totals   =[tasksper[i] * len(read) for i in range(numcores)]
        stop_progress.clear()
        def printer_loop(numcores):
            while not stop_progress.is_set():
                progressbars(numcores)
                time.sleep(1)

        printer_thread = threading.Thread(
            target=printer_loop,
            args=(numcores,),
            daemon=True,
        )
        printer_thread.start()


        with ThreadPoolExecutor(max_workers=numcores) as executor:
            collection = []
            for i in range(numcores):
                todo = tasksper[i]
                A =executor.submit(parallelsubmission,i, usrnm, psswrd,todo,read)
                collection.append(A)
            for A in as_completed(collection):
                A.result()
        stop_progress.set()
        printer_thread.join(timeout=1)
        return
    elif typ ==2:
        url = 'https://www.charmm-gui.org/'
        browser = webdriver.Chrome()
        browser.get(url)

        wait = WebDriverWait(browser, 15)
        login(usrnm, psswrd,wait)
        time.sleep(3)
        if os.path.isfile(Actionfile):
            with open(Actionfile, 'r') as f:
                logs = json.load(f)
        else:
            logs = []
        for entry in logs:
            execute(browser, entry,1,0)
        
        clickid = 1
        while clickid !=0:
            buttontype = int(input("Button Type: Click (1), Type in (2), Drop Down (3), Bubbles (4), next (5), Extend (6),  Exit (7): "))
            if buttontype ==1:
                buttons = clicklist(browser,0)
                inp = input('Button: ')
                whichone = mostsimilar(inp, buttons)
                record(logs, whichone,Actionfile)
                betterclick(browser, whichone)
                #whichone['element'].click()
                #whichone['element'].send_keys(Keys.RETURN)
            elif buttontype ==2:
                typboxes = listtypebox(browser,0)
                #print(typboxes)
                inp = input('Box Name: ')
                matches = findtypeboxes(inp, typboxes)
                print(matches)
                if len(matches)>1:
                    for i in range(len(matches)):
                        m = matches[i]
                        print(' '+str(i) + ': name: ' + m.get('name') + ' , id: ' + m.get('id') + ' , placeholder: ' + m.get('placeholder') + ' , type: ' + m.get('type') )
                    indexinquestion = int(input('Index: '))
                else:
                    indexinquestion = 0
                typebox = matches[indexinquestion]
                inp2 = input('Entry: ')
                typebox['element'].clear()
                typebox['element'].send_keys(inp2)
                inp3 = input('Hit Enter? yes (1)/ no (2): ')
                hitenter = (inp3=="1")
                if hitenter:
                    typebox['element'].send_keys(Keys.RETURN)
                record2(logs, inp, inp2,Actionfile, indexinquestion,hitenter)
            elif buttontype ==5:
                next_step = browser.find_element(By.XPATH,"//table[@class='nav_entry' and contains(normalize-space(.), 'Next Step')]") #turns out next isn't a button but a link
                NextRecorder(logs,Actionfile)
                next_step.click()
            elif buttontype == 3:
                drops = listDropDowns(browser,0)
                usr = int(input("Select dropdown index: "))
                dropdown = drops[usr]
                choice = int(input("Select Option Index: "))
                element = dropdown["options"][choice]
                text = dropdown["option_texts"][choice]
                element.click()
                DropDownRecord(logs,dropdown["name"],dropdown["id"],text,Actionfile)
            elif buttontype ==4:
                bubbles = BubbleList(browser,0)
                usr = int(input("Select Bubble Index: "))
                element = bubbles[usr]["element"]
                element.click()
                CheckBoxRecord(logs,bubbles[usr]["type"],bubbles[usr]["name"],bubbles[usr]["value"],True,Actionfile,label=bubbles[usr]["label"])
            elif buttontype  ==6:
                extends = listrecords(browser,0)
                usr = int(input("Select Extend Index: "))
                chosen = extends[usr]
                chosen['element'].click()
                recordrecords(logs, chosen['target'],chosen['onclick'],Actionfile)
            else:
                return
            

    elif typ ==3:
        exportstep = int(input("Export Step: "))
        url = 'https://charmm-gui.org/?doc=user/jobids'
        options = Options()
        #options.add_argument("--headless=new")
        #browser = webdriver.Chrome(options = options)
        browser = webdriver.Chrome()
        browser.get(url)

        wait = WebDriverWait(browser, 15)
        logs = []
        login(usrnm, psswrd,wait)
        buttons = clicklist(browser,1)
        time.sleep(1) #IDK works this way
        inp ='User Profile'
        whichone = mostsimilar(inp, buttons)
        betterclick(browser, whichone)
        inp ='Job IDs'
        buttons = clicklist(browser,1)
        whichone = mostsimilar(inp, buttons)
        betterclick(browser, whichone)
        buttons = clicklist(browser,1)
        six_links = steplinks(browser, str(exportstep))
        six_hrefs = [a.get_attribute("href") for a in six_links]
        for i in range(len(six_hrefs)):
            url = six_hrefs[i]
            browser.get(url)
            buttons = clicklist(browser,1)
            for button in buttons:
                text = button.get('text').strip()
                attributes = button.get('attrs')
                href = attributes.get('href')
                if text == "Go" and "step="+str(exportstep)+'&' in href:
                    betterclick(browser,button)
                    buttons = clicklist(browser,1)
                    whichone= mostsimilar('download.tgz',buttons)
                    betterclick(browser,whichone)
                    time.sleep(120)
                    break
            buttons = clicklist(browser,1)
            inp ='User Profile'
            whichone = mostsimilar(inp, buttons)
            betterclick(browser, whichone)
            inp ='Job IDs'
            buttons = clicklist(browser,1)
            whichone = mostsimilar(inp, buttons)
            betterclick(browser, whichone)
            print("Downloaded " + str(i+1) +' of ' + str(len(six_hrefs)))
        print('Downloaded All ' + str(len(six_hrefs)) + ' Files' )
        time.sleep(10000)
            
if __name__ == "__main__":
    main()
