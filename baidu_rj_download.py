#!/usr/bin/env python3
# coding: utf-8
import sqlite3
import pdb
import traceback
import sys
from ftp_credentials import ftpHostName,ftpUserName,ftpPassword
import ftputil
from os import path
import os
import re
from my_utils import uprint
from web_utils import getFileSha1, downloadFile, urlFileName
import urllib


def main():
    try:
        conn= sqlite3.connect('baidu_rj.sqlite3')
        csr=conn.cursor()
        rows = csr.execute(
            "SELECT appname,file_url,tree_trail, file_size, has_uploaded"
            " FROM TFiles "
            " where file_sha1 is NULL or LENGTH(file_sha1)=0").fetchall()
        for row in rows:
            appname,file_url,tree_trail, file_size, has_uploaded = row
            tree_trail = [int(_) for _ in re.findall('\d+', tree_trail) ]
            #if tree_trail[0] == 2: # is Game
            #    uprint('"%s" is a Game: %s'%(appname,tree_trail))
            #    continue
            if tree_trail[1] >= 20:
                uprint('"%s" bypass becasue it is not ranked in first 20 pages: %s'%(appname,tree_trail))
                continue
            # if file_size > 200*1024*1024: # too big
            #    uprint('"%s" file_size=%d is too big'%(appname,file_size))
            #    continue
            if has_uploaded == 1:
                uprint('has_uploaded=%d'%has_uploaded)
                continue
            local_file = urlFileName(file_url)
            uprint('"%s", %s, %s\n%s'%(appname, tree_trail, local_file, 
                file_url))
            try:
                downloadFile(file_url, local_file)
            except TypeError:
                continue
            except urllib.error.HTTPError as ex:
                # HTTP Error 404: Not Found
                print(ex)
                continue

            file_sha1 = getFileSha1(local_file)
            file_size = path.getsize(local_file)
            csr.execute(
                "UPDATE TFiles SET file_sha1=:file_sha1,file_size=:file_size"
                " WHERE file_url = :file_url", locals())
            conn.commit()
            ftp = ftputil.FTPHost(ftpHostName,ftpUserName,ftpPassword)
            uprint('upload to GRID')
            ftp.upload(local_file, path.basename(local_file))
            ftp.close()
            csr.execute(
                "UPDATE TFiles SET has_uploaded=1"
                " WHERE file_url=:file_url", locals())
            conn.commit()
            os.remove(local_file)
        conn.close()
    except Exception as ex:
        pdb.set_trace()
        traceback.print_exc()

if __name__=='__main__':
    main()
