#!/usr/bin/env python3
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

import argparse
import json
import logging
import logging.config
import os
import re
import shutil
from urllib.parse import parse_qs, urlparse, urlsplit

import git
import requests
import yaml
from requests.auth import HTTPBasicAuth


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
    """.format(
        name=os.path.basename(__file__), level=level
    ).lstrip()
    logging.config.dictConfig(yaml.safe_load(log_config))


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", help="Enable debug logging", action="store_true")
    parser.add_argument(
        "--config",
        help="Path to read the localrepos configuration file from",
        default="/etc/hound/localrepos.yml",
    )
    args = parser.parse_args()
    return args


def generate_repo_config(config, log, repo):
    link = urlparse(repo)
    try:
        namespace, repo = link.path[1:].split("/")
    except Exception:
        log.warning("Cannot parse namespace and repository from %s" % link.path[1:])
        return {}

    api = config["github_repo_api"]
    url = f"{api}/{namespace}/{repo}"
    username = config["github_username"]
    token = config["github_token"]
    clone_dir = config["localrepos_directory"]
    ignore = config["localrepos_ignore"] if config["localrepos_ignore"] != "" else None

    log.info("Retrieving repository: %s" % url)
    resp = requests.get(url, auth=HTTPBasicAuth(username, token)).json()

    name = resp["full_name"]
    path = os.path.join(clone_dir, name)

    # If the repo is ignored, we're not going to clone it.
    # Delete it if it exists.
    if ignore is not None:
        if re.match(ignore, name) or re.match(ignore, resp["name"]):
            if os.path.exists(path):
                log.info("Deleting %s which is ignored" % path)
                shutil.rmtree(path)
            return {}

    # If the repo is private, we don't want to make it available for search
    if resp["private"]:
        if os.path.exists(path):
            log.info("Deleting %s because it's private" % path)
            shutil.rmtree(path)
        return {}

    repo_config = {}
    repo_config[name] = {}
    repo_config[name]["url"] = "file://%s/%s" % (clone_dir, name)
    repo_config[name]["vcs-config"] = {"ref": resp["default_branch"]}
    base_url = "https://github.com/%s/blob/%s/{path}{anchor}"
    repo_config[name]["url-pattern"] = {
        "base-url": base_url % (name, resp["default_branch"]),
        "anchor": "#L{line}",
    }
    repo_config[name]["enable-poll-updates"] = False

    # If the repo already exists, update it
    if os.path.exists(path):
        log.info("Updating %s from %s" % (name, resp["clone_url"]))
        clone = git.Repo(path)
        origin = clone.remotes.origin
        try:
            origin.pull()
        except git.exc.GitCommandError as e:
            log.error("Error updating %s: %s" % (name, str(e)))
    else:
        # If the repo doesn't exist, clone it
        log.info("Cloning %s from %s" % (name, resp["clone_url"]))
        try:
            clone = git.Repo.clone_from(
                resp["clone_url"], path, branch=resp["default_branch"]
            )
        except git.exc.GitCommandError as e:
            log.error("Error cloning %s: %s" % (name, str(e)))

    return repo_config


def generate_org_repo_config(config, log, org):
    # This function is not split because we're not interested in iterating
    # across hundreds of repos more than once
    api = config["github_org_api"]
    url = f"{api}/{org}/repos?per_page=100"
    username = config["github_username"]
    token = config["github_token"]

    # Retrieve the amount of pages
    log.info("Retrieving the amount of repositories for: %s" % org)
    resp = requests.get(url, auth=HTTPBasicAuth(username, token))
    if resp.links:
        # get the last page
        query = urlsplit(resp.links["last"]["url"]).query
        pages = parse_qs(query)["page"][0]
    else:
        pages = 1

    log.info("Retrieving %s pages of 100 results for %s..." % (pages, org))
    repos = {}
    for page in range(1, int(pages) + 1):
        log.info("Fetching page %s out of %s..." % (page, pages))
        url = f"{api}/{org}/repos?per_page=100&page={page}"
        resp = requests.get(url, auth=HTTPBasicAuth(username, token)).json()
        for repo in resp:
            repos.update(generate_repo_config(config, log, repo["html_url"]))

    return repos


def main():
    args = get_args()
    level = "DEBUG" if args.debug else "INFO"
    setup_logging(level)
    log = logging.getLogger(os.path.basename(__file__))
    log.debug("Arguments: %s" % json.dumps(args.__dict__))

    # TODO: Add validation
    config = yaml.safe_load(open(args.config, "r"))
    repos = {}
    for org in config["localrepos_organizations"]:
        repos.update(generate_org_repo_config(config, log, org))

    for repo in config["localrepos_extra_repositories"]:
        repos.update(generate_repo_config(config, log, repo))

    config = {
        "max-concurrent-indexers": config["hound_indexers"],
        "dbpath": config["hound_index_files"],
        "repos": repos,
        "vcs-config": {
            "git": {
                "detect-ref": True
            }
        }
    }

    # TODO: put the path into a CLI argument, we can provide it from the role via hound_config
    with open("/etc/hound/config.json", "w") as f:
        f.write(json.dumps(config, indent=2, sort_keys=True))

    log.info("%s repositories cloned and up to date." % len(repos))
    log.info("Hound configuration written to /etc/hound/config.json.")


if __name__ == "__main__":
    main()
