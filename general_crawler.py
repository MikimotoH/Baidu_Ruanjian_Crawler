#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from urllib import request, parse
from urllib.parse import urlunsplit, urlsplit
from pyquery import PyQuery as pq
import re
import pdb
import traceback
from functools import reduce
import urllib
from my_utils import uprint
import sqlite3

def get_content_type(url:str)->str:
    if not re.match(r'http://|https://', url):
        return None
    try:
        with request.urlopen(url, timeout=120) as req:
            return req.headers['Content-Type']
    except urllib.error.HTTPError as ex:
        uprint('HTTP error code=%s'%ex.getcode())
        return ''
    except Exception as ex:
        pdb.set_trace()
        traceback.print_exc()
        return None

def make_url_abs(url:str, base:str)->str:
    if re.match(r'http://|https://', url):
        return url
    if re.match(r'javascript:|mailto:', url):
        return None
    pr = parse.urlsplit(base)
    scheme = pr.scheme if pr.scheme else 'http'
    if url.startswith('//'):
        return pr.scheme + ':' + url
    else:
        return parse.urljoin(base, url)

def get_children(url:str)->[str]:
    content_type = get_content_type(url)
    if content_type is None:
        uprint('invalid url ='+url)
        return None
    elif not content_type.startswith('text/'):
        return None
    elif not content_type.startswith('text/html'):
        pdb.set_trace()
        uprint(content_type)
    try:
        d = pq(url=url)
    except ConnectionError as ex:
        uprint('ConnectionError= %s'%ex)
        return None
    return [_ for _ in (make_url_abs(_.attrib['href'],url) for _ in d('a') if 'href' in _.attrib) if _]

def unfold_list(listOfList):
    return reduce(lambda x,y:x+y, listOfList)

def serialize_tree(tree):
    if isinstance(tree,str):
        yield tree
        return
    for branch in tree:
        yield from serialize_tree(branch)

def crawl_files(fqdn:str, max_depth:int=4, timeout:int=120)->[str]:
    try:
        records = {}
        depth=0
        records[fqdn] = (None,depth)
        num_apps=0
        from urllib.parse import urlsplit
        for depth in range(depth, max_depth+1):
            if num_apps>0:
                uprint('num_apps=%d'%num_apps)
                break
            urls = [_ for _ in records if not records[_][0]]
            if len(urls)==0:
                uprint('len(urls)==0')
                break
            for url in urls:
                if not re.match(r'http://|https://', url):
                    continue
                mimetype='ERROR: '
                try:
                    with request.urlopen(url, timeout=timeout) as req:
                        mimetype = req.headers['Content-Type']
                        assert mimetype
                except urllib.error.HTTPError as ex:
                    mimetype = 'ERROR: ' + str(ex)
                except Exception as ex:
                    print('ex=%s'%ex)
                    mimetype = 'ERROR: ' + str(ex)
                records[url] = (mimetype,depth)
                if mimetype.startswith('ERROR: '):
                    continue
                if mimetype.startswith('application/'):
                    num_apps+=1
                if not mimetype.startswith('text/html'):
                    continue
                # get children
                try:
                    d = pq(url=url)
                except ConnectionError as ex:
                    print('ConnectionError= %s'%ex)
                    continue
                except Exception as ex:
                    print('Exception= %s,%s'%(ex, type(ex)))
                    continue
                children=[_.attrib['href'] for _ in d('a') if 'href' in _.attrib]
                children=[make_url_abs(_,url) for _ in children]
                children=[_ for _ in children if _]
                for child in children:
                    if child not in records:
                        records[child] = (None,depth+1)
        return [_ for _ in records if records[_][0] and records[_][0].startswith('application/') ]
    except Exception as ex:
        pdb.set_trace()
        traceback.print_exc()


def formalize_fqdn(fqdn:str)->str:
    if not re.match(r'http://|https://', fqdn):
        if re.match(r'\w+', fqdn):
            fqdn = 'http://'+fqdn
        else:
            raise Exception('strange fqdn %s'%fqdn)
    from urllib.parse import urlsplit, urlunsplit
    pr = urlsplit(fqdn)
    _scheme,_netloc,_path,_query,_fragment = pr.scheme,pr.netloc,pr.path,pr.query,pr.fragment
    if _path=='':
        assert not _query and not _fragment
        _path='/'
    return urllib.parse.SplitResult(_scheme,_netloc,_path,_query,_fragment).geturl()


def http_headers(url:str, timeout:int=120)->dict:
    with request.urlopen(furl,timeout=timeout) as req:
        return dict(req.headers)

def main():
    try:
        applist={}
        with open('China_Popular_App_List.txt', 'r') as fin:
            for line in fin:
                tok=[_.strip('"') for _ in re.findall(r'".*?(?<!")"', line)]
                appname,fqdn=tok[1],tok[3]
                try:
                    fqdn = formalize_fqdn(fqdn)
                except Exception as ex:
                    uprint('Strange FQDN "%s", %s'%(appname, fqdn))
                    continue
                if appname in applist:
                    fqdn1=applist[appname]
                    if fqdn1[0] != fqdn:
                        uprint('not unique appname "%s"'%appname)
                        applist[appname]=fqdn1+[fqdn]
                else:
                    applist[appname]=[fqdn]
        # create sqlite table
        with sqlite3.connect('china_popular_app_list.sqlite3') as conn:
            csr=conn.cursor()
            csr.execute("CREATE TABLE IF NOT EXISTS Apps"
                "(name TEXT,fqdn TEXT,file_url TEXT,"
                "PRIMARY KEY(name,fqdn) )", locals())
            conn.commit()

        with sqlite3.connect('china_popular_app_list.sqlite3') as conn:
            csr=conn.cursor()
            for name in applist:
                fqdns = applist[name]
                for fqdn in fqdns:
                    uprint('crawl "%s" %s'%(name,fqdn))
                    files=crawl_files(fqdn)
                    uprint('num_files=%d'%len(files))
                    if not files:
                        uprint('No files for fqdn='+fqdn)
                        csr.execute("INSERT INTO Apps(name,fqdn)VALUES"
                            "(:name,:fqdn)",locals())
                        continue
                    for furl in files:
                        uprint('"%s" has file= %s'%(name,furl))
                        csr.execute(
                            "INSERT OR REPLACE INTO Apps("
                            " name, fqdn, file_url)VALUES("
                            ":name,:fqdn,:furl)",locals())
                        conn.commit()

    except Exception as ex:
        pdb.set_trace()
        traceback.print_exc()
        print(ex)


def main_serialize_tree():
    fruits = [[[['apple'],'banana'],'cherry'], 'durian']
    fruitsList = list ( serialize_tree(fruits) )
    print(fruitsList)

if __name__ == '__main__':
    main()

