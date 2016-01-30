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
from my_utils import uprint
from web_utils import getFileSha1, downloadFile, urlFileName


def main():
    try:
        conn= sqlite3.connect('baidu_rj.sqlite3')
        csr=conn.cursor()
        rows = csr.execute(
            "SELECT appname,file_url,file_sha1,tree_trail FROM TFiles").fetchall()
        for row in rows:
            appname,file_url,file_sha1,tree_trail = row
            if file_sha1: 
                continue
            local_file = urlFileName(file_url)
            uprint('"%s", %s, %s'%(appname, tree_trail, local_file))
            try:
                downloadFile(file_url, local_file)
            except TypeError:
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
            os.remove(local_file)
        conn.close()
    except Exception as ex:
        pdb.set_trace()
        traceback.print_exc()

if __name__=='__main__':
    main()
