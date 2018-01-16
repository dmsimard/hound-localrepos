hound-localrepos
================

**Pronounced** ``/Haʊnd ˈləʊk(ə)lrɪˈpɒ/`` (just kidding)

.. image:: https://raw.githubusercontent.com/etsy/hound/master/screen_capture.gif

Hound is a Go project by Etsy_ that indexes version-controlled project
repositories (such as Git or SVN) and provides a simple web interface to search
code.

The OpenStack_ community uses Hound to index and search code through more
than 2000 repositories in different languages including Bash, Python, Ruby,
Javascript, Puppet and Ansible.

This project is an Ansible_ role that will:
- Install and configure Hound_ to index repositories stored on the local filesystem
- Install a synchronization script that clones all the GitHub repositories from an organization and keeps them up-to-date.
- Set up the script to run on a regular schedule

Indexing git repositories locally is better in terms of performance but it's
also less likely to get you rate-limited from GitHub.

.. _Ansible: https://www.ansible.com/
.. _RHEL: https://www.redhat.com/en/technologies/linux-platforms/enterprise-linux
.. _CentOS: https://www.centos.org/
.. _hound: https://github.com/etsy/hound
.. _Etsy: https://www.etsy.com
.. _Openstack: https://www.openstack.org/

Configuration
=============

The role has parameters in order to allow you to customize the installation
of Hound, where the repositories will be downloaded, etc.
The default variables are as follows::

    ###########################
    # Go configuration
    ###########################
    # Whether to install Go
    go_install: true

    # Location where to retrieve the Go tarball from
    go_tarball_location: https://dl.google.com/go/go1.9.2.linux-amd64.tar.gz

    # Checksum of the tarball
    go_tarball_checksum: de874549d9a8d8d8062be05808509c09a88a248e77ec14eb77453530829ac02b

    ###########################
    # Hound configuration
    ###########################
    # Where to retrieve Hound from
    # This specific location is set-up to include a non-merged pull-request
    hound_location: github.com/dmsimard/hound/cmds/houndd

    # Host to listen on
    hound_host: 0.0.0.0

    # Port to listen on
    hound_port: 6080

    # Path to configuration file
    hound_config: /etc/hound/config.json

    # Maximum amount of hound concurrent indexers
    hound_indexers: 4

    # Path to hound index files
    hound_index_files: /var/lib/hound/data

    ###########################
    # Local repository synchronization
    ###########################
    # Path to local git repositories
    localrepos_directory: /var/lib/hound/local

    # Cron formatted schedule to run the synchronization
    # Defaults to '0 * * * *' which runs hourly at "00" minutes.
    localrepos_schedule:
      minute: '0'
      hour: '*'
      day: '*'
      weekday: '*'
      month: '*'

    # List of GitHub organizations you'd like to index
    localrepos_organizations:
      - rdo-infra

    # Blacklist of repositories that should not be synchronized.
    # This is a regular expression.
    localrepos_blacklist: "^puppet.*"

    # Location where to write the localrepos configuration file
    # Warning: contains your GitHub credentials
    localrepos_config: /etc/hound/localrepos.yml

    ###########################
    # GitHub Authentication
    ###########################
    # These parameters are required in order to dynamically retrieve all the
    # repositories from a GitHub organization through the GitHub API.
    # Your GitHub username
    github_username:

    # Your GitHub personal token
    # You can generate a new token here: https://github.com/settings/tokens
    github_token:

    # The GitHub API endpoint
    # (Keep the default unless you're using GitHub enterprise)
    github_api: https://api.github.com/orgs/

Using the hound-localrepos Ansible role
=======================================

If you are not familiar with Ansible, the following commands will get you
started from scratch on a brand new RHEL or CentOS server with sane defaults::

    pip install ansible
    mkdir roles
    git clone https://github.com/dmsimard/hound-localrepos roles/localrepos
    ANSIBLE_ROLES_PATH="$(pwd)/roles" ansible-playbook -i roles/localrepos/contrib/hosts roles/localrepos/contrib/playbook.yml

Note that you will need to supply the ``github_username`` and
``github_token`` credentials in order to be able to query the GitHub API.

The GitHub token can be generated in your GitHub settings_.

If you're supplying the variables from the ansible-playbook command, you can do
it like this::

    ansible-playbook -i roles/localrepos/contrib/hosts \
     --extra-var github_username=user \
     --extra-var github_token=token \
     roles/localrepos/contrib/playbook.yml

.. _settings: https://github.com/settings/tokens

Contributors
============

See contributors on GitHub_.

.. _GitHub: https://github.com/openstack/ara/graphs/contributors

Copyright
=========

Copyright 2017 Red Hat, Inc.

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
