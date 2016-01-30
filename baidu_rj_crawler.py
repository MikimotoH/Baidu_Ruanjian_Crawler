#!/usr/bin/env python3
# coding: utf-8
from selenium import webdriver
import sqlite3
from harvest_utils import waitClickable, waitVisible, waitText, getElems, \
        getElemText,getFirefox,driver,dumpSnapshot,\
        getText,getNumElem,waitTextChanged,waitElem,\
        waitUntil,clickElem,getElemAttr,hasElem,waitUntilStable,\
        waitUntilA,mouseClickE,waitTextA,UntilTextChanged,mouseOver
from selenium.common.exceptions import NoSuchElementException, \
        TimeoutException, StaleElementReferenceException, \
        WebDriverException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait,Select
from selenium.webdriver.common.action_chains import ActionChains
import re
from datetime import datetime
from selenium.webdriver.common.keys import Keys
import harvest_utils
import pdb
import traceback
from my_utils import uprint,ulog
import itertools
import sys
import os


driver,conn = [None]*2
startTrail=[]
prevTrail=[]

def getStartIdx():
    global startTrail
    if startTrail:
        return startTrail.pop(0)
    else:
        return 0

def sql(query:str, var=None):
    global conn
    csr=conn.cursor()
    try:
        if var:
            rows = csr.execute(query,var)
        else:
            rows = csr.execute(query)
        if not query.startswith('SELECT'):
            conn.commit()
        if query.startswith('SELECT'):
            return rows.fetchall()
        else:
            return
    except sqlite3.Error as ex:
        print(ex)
        raise ex

def is_int(txt:str)->bool:
    return re.match(r'\d+', txt) is not None

def guessDate(txt:str)->datetime:
    """ txt = '2014-10-02' """
    try:
        m = re.search(r'\d{4}-\d{2}-\d{2}', txt)
        return datetime.strptime(m.group(0), '%Y-%m-%d')
    except Exception as ex:
        pdb.set_trace()
        print('txt=',txt)

def guessFileSize(txt:str)->int:
    """ txt='6.56 MB'
    """
    try:
        m = re.search(r'(\d+\.?\d+)\s*(M|K)', txt, re.I)
        if not m:
            ulog('error txt="%s"'%txt)
            return 0
        unitDic=dict(M=1024**2,K=1024)
        unitTxt = m.group(2).upper()
        return int(float(m.group(1)) * unitDic[unitTxt] )
    except Exception as ex:
        pdb.set_trace()
        print('txt=',txt)

def itemWalker():
    global driver,prevTrail
    try:
        items = getElems('ul.softList > li > div')
        numItems = len(items)
        startIdx = getStartIdx()
        for idx in range(startIdx, numItems):
            item = items[idx]
            ulog('item= %s'%item.text)
            appname = item.find_element_by_css_selector('.title').text
            page_url = item.find_element_by_css_selector('a').get_attribute('href')
            desc = item.find_element_by_css_selector('.desc').text
            info = item.find_element_by_css_selector('.info').text
            file_date = guessDate(info)
            file_size = guessFileSize(info)
            file_url = item.find_element_by_css_selector('.download a').get_attribute('href')
            tree_trail=str(prevTrail+[idx])
            sql("INSERT OR REPLACE INTO TFiles("
                " appname, file_url,desc, file_date, file_size, page_url,"
                " tree_trail) VALUES("
                ":appname,:file_url,:desc,:file_date,:file_size,:page_url,"
                ":tree_trail)", locals())
            ulog('UPSERT "%(appname)s", "%(info)s", "%(file_url)s", '
                '%(tree_trail)s'%locals())
    except Exception as ex:
        pdb.set_trace()
        traceback.print_exc()
        driver.save_screenshot('baidu_rj.png')


def pageWalker():
    global driver,prevTrail
    try:
        startIdx = getStartIdx()
        startPage = startIdx+1
        ulog('startPage=%d'%startPage)
        maxPage=max(int(_.text) for _ in getElems('.page > span > a') if is_int(_.text))
        ulog('maxPage=%d'%maxPage)
        if startPage > maxPage:
            return
        while True:
            curPage = int(waitText('.pageList > a.active'))
            ulog('curPage=%d'%curPage)
            if startPage == curPage:
                break
            pageLinks = [_ for _ in getElems('.page > span > a') if is_int(_.text)]
            pageLink = min(pageLinks, key=lambda p: abs(int(p.text)-startPage))
            pageLink.click()

        # for idx in range(0, startIdx):
        #     nextPage = waitClickable('.page > span:nth-child(3) > a')
        #     nextPage.click()
        for idx in itertools.count(startIdx):
            ulog('idx=%d, page=%d'%(idx,idx+1))
            prevTrail+=[idx]
            itemWalker()
            prevTrail.pop()
            nextPage = waitClickable('.page > span:nth-child(3) > a')
            if nextPage.get_attribute('class')=='quiet':
                break
            nextPage.click()

    except Exception as ex:
        pdb.set_trace()
        traceback.print_exc()
        driver.save_screenshot('baidu_rj.png')

def FenLeiWalker():
    global driver,prevTrail
    try:
        fenleis = getElems('.sortDetail > li')
        numFenLeis = len(fenleis)
        startIdx = getStartIdx()
        for idx in range(startIdx, numFenLeis):
            fenlei = fenleis[idx]
            ulog('FenLei= %s'%fenlei.text)
            fenlei.find_element_by_css_selector('a').click()
            prevTrail+=[idx]
            pageWalker()
            prevTrail.pop()
            if idx < numFenLeis-1:
                fenleis = getElems('.sortDetail > li')
    except Exception as ex:
        pdb.set_trace()
        traceback.print_exc()
        driver.save_screenshot('baidu_rj.png')

def main():
    global startTrail,prevTrail, driver,conn
    try:
        startTrail = [int(re.search(r'\d+', _).group(0)) for _ in sys.argv[1:]]
        conn=sqlite3.connect('baidu_rj.sqlite3')
        sql(
            "CREATE TABLE IF NOT EXISTS TFiles("
            "appname TEXT,"
            "file_url TEXT,"
            "desc TEXT,"
            "file_date TEXT,"
            "file_size INTEGER,"
            "page_url TEXT,"
            "tree_trail TEXT,"
            "file_sha1 TEXT,"
            "PRIMARY KEY (file_url)"
            "UNIQUE(file_url)"
            ");")
        # driver = webdriver.PhantomJS()
        driver=harvest_utils.getFirefox()
        harvest_utils.driver = driver
        driver.get('http://rj.baidu.com/')
        prevTrail=[]
        FenLeiWalker()
        driver.quit()
        conn.close()
    except Exception as ex:
        pdb.set_trace()
        traceback.print_exc()
        driver.save_screenshot('baidu_rj.png')

if __name__=='__main__':
    main()
