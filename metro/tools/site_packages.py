# -*- coding: utf-8 -*-
"""
Created on Sun May 31 08:36:08 2020

@author: islam
"""

site_pack_path = 'C:\\Users\\islam\\AppData\\Local\\Programs\\Python\\' \
                    'Python37\\Lib\\site-packages'
#site_pack_path = 'C:\\Users\\kamelisl\\AppData\\Roaming\\Python\\Python38\\site-packages'
import sys
import site
for SITEPACKAGES in [site_pack_path, site.getusersitepackages()]:
    if SITEPACKAGES not in sys.path:
        sys.path.append(SITEPACKAGES)