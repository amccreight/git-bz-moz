# Copyright (C) 2010 Mozilla Foundation
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


# Extracted from __init__.py from bzexport.


import os
import platform
import time
import urllib
import urllib2
import json
from mercurial import config, demandimport, util
from mercurial.i18n import _
try:
    import cPickle as pickle
except:
    import pickle
import bz

# requests doesn't like lazy importing
demandimport.disable()
import requests
demandimport.enable()

from auth import (
    getbugzillaauth,
    win_get_folder_path,
)


# Returns [ { search_string: original, names: [ str ], real_names: [ str ] } ]
def find_users(ui, api_server, user_cache_filename, auth, search_strings):
    c = bzauth.load_user_cache(ui, api_server, user_cache_filename)
    section = api_server

    search_results = []
    for search_string in search_strings:
        name = c.get(section, search_string)
        if name:
            search_results.append({"search_string": search_string,
                                   "names": [name],
                                   "real_names": ["not_a_real_name"]})
            continue

        try:
            try:
                users = bz.find_users(auth, search_string)
            except Exception as e:
                raise util.Abort(e.message)
            name = None
            real_names = map(lambda user: "%s <%s>" % (user["real_name"], user["email"])
                             if user["real_name"] else user["email"], users["users"])
            names = map(lambda user: user["name"], users["users"])
            search_results.append({"search_string": search_string,
                                   "names": names,
                                   "real_names": real_names})
            if len(real_names) == 1:
                c.set(section, search_string, names[0])
        except Exception, e:
            search_results.append({"search_string": search_string,
                                   "error": str(e),
                                   "real_names": None})
            raise
    bzauth.store_user_cache(c, user_cache_filename)
    return search_results


# search_strings is a simple list of strings
def validate_users(ui, api_server, auth, search_strings, multi_callback, multi_desc):
    search_results = find_users(ui, api_server, INI_CACHE_FILENAME, auth, search_strings)
    search_failed = False
    results = {}
    for search_result in search_results:
        if search_result["real_names"] is None:
            ui.write_err("Error: couldn't find user with search string \"%s\": %s\n" %
                         (search_result["search_string"], search_result["error"]))
            search_failed = True
        elif len(search_result["real_names"]) > 10:
            ui.write_err("Error: too many bugzilla users matching \"%s\":\n\n" % search_result["search_string"])
            for real_name in search_result["real_names"]:
                ui.write_err("  %s\n" % real_name.encode('ascii', 'replace'))
            search_failed = True
        elif len(search_result["real_names"]) > 1:
            user = multi_callback(ui, multi_desc, search_result)
            if user is not None:
                results[search_result['search_string']] = [user]
        elif len(search_result["real_names"]) == 1:
            results[search_result['search_string']] = search_result['names']
        else:
            ui.write_err("Couldn't find a bugzilla user matching \"%s\"!\n" % search_result["search_string"])
            search_failed = True
    return None if search_failed else results

