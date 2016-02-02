#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from urllib import request, parse
from pyquery import PyQuery as pq
import re
import pdb
import traceback
from functools import reduce
import urllib
from my_utils import uprint

def get_content_type(url:str)->str:
    if not re.match(r'http://|https://', url):
        return None
    try:
        with request.urlopen(url) as req:
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

def bfs_tree_traverse(start_url:str, max_depth:int=20):
    records = {}
    depth=0
    records[start_url] = (None,depth)
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
            try:
                with request.urlopen(url) as req:
                    mimetype = req.headers['Content-Type']
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


def main():
    links = bfs_tree_traverse('http://www.taobao.com/wangwang/', 9)
    for l in links:
        with request.urlopen(l) as req:
            print('%s'%l)
            print('headers= %s'%req.headers.items())
            if 'Content-Type' in req.headers:
                print('Content-Type=%s'% req.headers['Content-Type'])
            if 'Content-Length' in req.headers:
                print('Content-Length=%s'% req.headers['Content-Length'])


def main_serialize_tree():
    fruits = [[[['apple'],'banana'],'cherry'], 'durian']
    fruitsList = list ( serialize_tree(fruits) )
    print(fruitsList)

if __name__ == '__main__':
    main()

