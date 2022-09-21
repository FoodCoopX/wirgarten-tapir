# WirGarten Tapir Contributing Guide
This guide documents the development process and helps new developers to start working on the project.

## Setup Dev Environment
It is recommended to use a unix based system for development because of the better container support.

### IDE
Leon uses [PyCharm](https://www.jetbrains.com/pycharm/) for development.
It has a Poetry plugin that easily allows setting up a local (not in the container) Python env and run the tests in
there. Make sure to enable Django support in the project settings so that things like the template language and the
test runner are automagically selected (note that right now this doesn't really work anymore as the tests must be run
inside docker to have an LDAP server. But PyCharm is still pretty cool)

### Setup Git
1.  Install git: e.g. `sudo apt install git`
2.  Configure your SSH key: https://docs.github.com/en/authentication/connecting-to-github-with-ssh
3.  Run `git config core.commentchar "@"` (allows to start commit message with `#`)

### Setup Docker
1. Install Docker: https://docs.docker.com/engine/install/
2. Run Docker in Rootless mode: https://docs.docker.com/engine/security/rootless/
3. Verify that your installation is working: `docker run hello-world`
4. Install docker-compose: e.g. `sudo apt install docker-compose`

### Pre-commit hooks
Install Poetry: https://python-poetry.org/docs/#installation

First thing after checkout, run the following to install auto-formatting using [black](https://github.com/psf/black/)
before every commit:

    poetry install && pre-commit install

## Getting started

    docker-compose up

This starts a container with an LDAP server and automatically loads the test data into the LDAP.

Next, set up the test database and load test data

    # Create tables
    docker-compose exec web poetry run python manage.py migrate
    
    # Import configuration parameter definitions
    docker-compose exec web poetry run python manage.py parameter_definitions

    # Load admin (password: admin) account
    docker-compose exec web poetry run python manage.py loaddata admin_account
    
    # Load lots of test users & shifts
    docker-compose exec web poetry run python manage.py populate --reset_all


## Workflow
Any code changes should reference a GitHub issue, if you don't have one, create it.

For naming the branches, we are differentiating between feature and bugfix branches:
- `feature/#<github-issue>/<short-description>`
- `bug/#<github-issue>/<short-description>`

Assuming that you already have cloned the repo and `cd`'d into it:
1. Create your branch:`git checkout -b <your-branch-name>`
2. Work on your branch
3. At the end of the day: 
   - `git commit -m "<commit-message>"`
   - `git push`
4. When you are ready for review:
      - `git rebase -i origin/master`
      - `r` (reword) the first commit to `#<github-issue>: <commit-message>`
      - set all commits after that to `f` (fixup)
      - `git push --force-with-lease` 
      
     ![git-rebase](https://user-images.githubusercontent.com/12133154/191477746-23be2774-0f9d-4604-ad12-457bee8352af.gif)

5. Create Pull Request in GitHub and make sure the checks are passing
