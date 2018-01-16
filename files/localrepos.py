#!/usr/bin/python2
#   Copyright Red Hat, Inc. All Rights Reserved.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

# TODO: This forked from a py2 script, move to py3

import argparse
import logging
import logging.config
import requests
from requests.auth import HTTPBasicAuth
from urlparse import parse_qsl, urlsplit
import git
import json
import os
import re
import shutil
import yaml


def setup_logging(level):
    log_config = """
    ---
    version: 1
    formatters:
        console:
            format: '%(asctime)s %(levelname)s %(name)s: %(message)s'
    handlers:
        console:
            class: logging.StreamHandler
            formatter: console
            level: {level}
            stream: ext://sys.stdout
    loggers:
        {name}:
            handlers:
                - console
            level: {level}
            propagate: 0
    root:
      handlers:
        - console
      level: {level}
    """.format(name=os.path.basename(__file__), level=level).lstrip()
    logging.config.dictConfig(yaml.safe_load(log_config))


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", help="Enable debug logging",
                        action="store_true")
    parser.add_argument("--config", help="Path to the configuration file",
                        default="/etc/hound/localrepos.yml")
    args = parser.parse_args()
    return args


def generate_org_repo_config(config, log, org):
    # This function is not split because we're not interested in iterating
    # across hundreds of repos more than once
    api = config['github_api']
    url = api + org + '/repos?per_page=100'
    username = config['github_username']
    token = config['github_token']
    clone_dir = config['localrepos_directory']
    blacklist = config['localrepos_blacklist']
    blacklisted = 0

    # Retrieve the amount of pages
    log.info("Retrieving the amount of repositories for: %s" % org)
    resp = requests.get(url, auth=HTTPBasicAuth(username, token))
    if resp.links:
        pages = parse_qsl(urlsplit(resp.links['last']['url']).query)[-1][1]
    else:
        pages = 1

    log.info("Retrieving %s pages of 100 results for %s..." % (pages, org))
    repos = {}
    for page in range(1, int(pages) + 1):
        log.info("Fetching page %s out of %s..." % (page, pages))
        url = api + org + '/repos?per_page=100&page=%s' % page
        resp = requests.get(url, auth=HTTPBasicAuth(username, token)).json()
        for repo in resp:
            name = repo['full_name']
            path = os.path.join(clone_dir, name)

            # If the repo is blacklisted, we're not going to clone it
            # and delete it if it exists
            if re.match(blacklist, name) or re.match(blacklist, repo['name']):
                if os.path.exists(path):
                    blacklisted += 1
                    log.info("Deleting %s which matches the blacklist" % path)
                    shutil.rmtree(path)
                continue

            repos[name] = {}
            repos[name]['url'] = "file://%s/%s" % (clone_dir, name)
            # https://github.com/etsy/hound/pull/275
            # Provided by "go get github.com/dmsimard/hound/cmds/houndd"
            repos[name]['vcs-config'] = {
                'ref': repo['default_branch']
            }
            base_url = 'https://github.com/%s/blob/%s/{path}{anchor}'
            repos[name]['url-pattern'] = {
                'base-url': base_url % (name, repo['default_branch']),
                'anchor': '#L{line}'
            }
            repos[name]['enable-poll-updates'] = False

            # If the repo already exists, update it
            if os.path.exists(path):
                log.info("Updating %s from %s" % (name, repo['clone_url']))
                clone = git.Repo(path)
                origin = clone.remotes.origin
                try:
                    origin.pull()
                except git.exc.GitCommandError as e:
                    log.error('Error updating %s: %s' % (name, str(e)))
            else:
                # If the repo doesn't exist, clone it
                log.info("Cloning %s from %s" % (name, repo['clone_url']))
                try:
                    clone = git.Repo.clone_from(repo['clone_url'], path,
                                                branch=repo['default_branch'])
                except git.exc.GitCommandError as e:
                    log.error('Error cloning %s: %s' % (name, str(e)))
    msg = "{0} repositories matching the blacklist were not cloned for {1}."
    log.info(msg.format(blacklisted, org))
    return repos


def main():
    args = get_args()
    level = "DEBUG" if args.debug else "INFO"
    setup_logging(level)
    log = logging.getLogger(os.path.basename(__file__))
    log.debug("Arguments: %s" % json.dumps(args.__dict__))

    # TODO: Add validation
    config = yaml.safe_load(open(args.config, 'r'))
    repos = {}
    for org in config['localrepos_organizations']:
        repos.update(generate_org_repo_config(config, log, org))

    config = {
        'max-concurrent-indexers': config['hound_indexers'],
        'dbpath': config['hound_index_files'],
        'repos': repos
    }

    with open('/etc/hound/config.json', 'w') as f:
        f.write(json.dumps(config, indent=2, sort_keys=True))

    log.info("%s repositories cloned and up to date." % len(repos))
    log.info("Hound configuration written to /etc/hound/config.json.")


if __name__ == "__main__":
    main()
