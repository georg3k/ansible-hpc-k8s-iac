#!/usr/bin/env python3

import os
import sys
import json
import ldap
import ldap.asyncsearch
import pip

if __name__ == "__main__":

    # Configuration loading
    config = None
    with open('hass-ldap-sync.json') as f:
        config = json.load(f)

    admins = []
    admins_gid = ''

    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
    l = ldap.initialize(config['ldap']['url'])
    l.protocol_version = ldap.VERSION3
    search_filter = '(uid=%s)' % os.environ['username']
    l.simple_bind_s(config['ldap']['bind_dn'], config['ldap']['password'])

    for group_dn, group_data in l.search_s(base=config['ldap']['groups_base_dn'],
                                                   scope=ldap.SCOPE_SUBTREE,
                                                   filterstr='(cn=%s)' % config['ldap']['admin_group']):
        admins_gid = group_data['gidNumber'][0].decode()
        if 'memberUid' in group_data.keys():
            for member in group_data['memberUid']:
                admins.append(member)

    for user_dn, user_data in l.search_s(base=config['ldap']['base_dn'],
                                         scope=ldap.SCOPE_SUBTREE,
                                         filterstr=search_filter):
        
        if user_data['gidNumber'][0].decode() == admins_gid:
            admins.append(user_data['uid'][0].decode())
        
        l.simple_bind_s(user_dn, os.environ['password'])
        if os.environ['username'] not in admins:
            sys.exit(-1)