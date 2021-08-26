# hound-localrepos

[Hound](https://github.com/hound-search/hound) is an extremely fast source code search engine.

It looks like this:
![Hound Screen Capture](https://github.com/hound-search/hound/blob/main/imgs/screen_capture.gif)

You can read more about it on their GitHub repository: https://github.com/hound-search/hound

# About localrepos

The OpenStack and Ansible communities have been using Hound to index and search
code in thousands of git repositories with millions of lines of code in many
different languages including python, bash, golang, yaml, jinja2, javascript,
html, css, ruby and powershell.

localrepos is meant to provide an integration of Hound that indexes a list of
specified GitHub repositories or organizations that are cloned and kept up to
date on the local filesystem.

Indexing and searching locally is fast and decreases the likelihood of running into
GitHub rate limits.

This project will:

- Configure a cron to run a synchronization script that clones (or updates) specific git repositories (or entire GitHub organizations)
- Install, configure and start Hound to index the cloned git repositories
- Install and set up nginx to handle SSL termination and be a reverse proxy in front of the server exposed by hound

It is currently tested against Fedora 34 and only supports GitHub but could be
improved to support other distributions and generic git repositories.

We accept pull requests :)

## Using this project

First, install Ansible and this role if they are not already installed elsewhere:

```bash
python3 -m venv ~/.ansible/venv
source ~/.ansible/venv/bin/activate
pip install ansible
git clone https://github.com/dmsimard/hound-localrepos ~/.ansible/roles/localrepos
```

Then, at a minimum, it is required to provide two Ansible variables:

- ``github_username``
- ``github_token`` (you can get one [here](https://github.com/settings/tokens))

These, along with the remainder of your customized [configuration variables](https://github.com/dmsimard/hound-localrepos/blob/master/defaults/main.yml)
(ideally encrypted with [ansible-vault](https://docs.ansible.com/ansible/latest/user_guide/vault.html)) can be provided
to the role as a [vars_file or through extra-vars](https://docs.ansible.com/ansible/latest/user_guide/playbooks_variables.html):

```bash
cat <<EOF > extra-vars.yaml
nginx_fqdn: codesearch.example.org
nginx_ssl: true
nginx_ssl_cert: /etc/letsencrypt/live/{{ nginx_fqdn }}/fullchain.pem
nginx_ssl_key: /etc/letsencrypt/live/{{ nginx_fqdn }}/privkey.pem
localrepos_organizations:
  - some_organization_name
  - another_organization_name
localrepos_extra_repositories:
  - https://github.com/namespace/repository
github_username: foo
github_token: bar
EOF

# Provide your own inventory or use the example hosts file to deploy on localhost
ansible-playbook -i ~/.ansible/roles/localrepos/contrib/hosts \
  --extra-vars "@extra-vars.yaml" \
  ~/.ansible/roles/localrepos/contrib/site.yml
```

## Contributors

See contributors on [GitHub](https://github.com/dmsimard/hound-localrepos/graphs/contributors).

## Copyright

    Copyright 2017 Red Hat, Inc.

    Licensed under the Apache License, Version 2.0 (the "License"); you may
    not use this file except in compliance with the License. You may obtain
    a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
