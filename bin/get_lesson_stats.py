#! /usr/bin/env python
'''
Usage: python get_lesson_stats.py your_github_username your_github_personal_access_token

Use the GitHub API to summarise lessons in The Carpentries Incubator.

The personal access token must have at least the public_repo and read_org scopes.
'''

import requests
import sys
from collections import defaultdict
from time import sleep
from datetime import datetime, timedelta

def isLessonRepo(repoJSON, username, token):
    '''returns True if the repository described by repoJSON has
    the 'lesson' topic tag, or False otherwise.

    Expects:
        - repoJSON: a JSON blob from the GitHub API, describing a repository
        - username: your GitHub username for authentication
        - token: a GitHub Personal Access Token, with public_repo scope
    '''
    REPOSITORY_TOPICS_URL = "https://api.github.com/repos/carpentries-incubator/{}/topics"
    header = {"Accept": "application/vnd.github.mercy-preview+json"} # this part of the GitHub API is experimental, so we opt in to using it with this header
    topics = requests.get(REPOSITORY_TOPICS_URL.format(repoJSON['name']), headers=header, auth=(username, token))
    return 'lesson' in topics.json()['names']

def getLifeCycleStage(repoJSON, username, token):
    '''returns life cycle stage of lesson repo, based on the
    presence of a topic tag in the set "life_cycle_stages".

    Expects:
        - repoJSON: a JSON blob from the GitHub API, describing a repository
        - username: your GitHub username for authentication
        - token: a GitHub Personal Access Token, with public_repo scope
    '''
    REPOSITORY_TOPICS_URL = "https://api.github.com/repos/carpentries-incubator/{}/topics"
    life_cycle_stages = {"pre-alpha", "alpha", "beta", "stable"}
    header = {"Accept": "application/vnd.github.mercy-preview+json"} # this part of the GitHub API is experimental, so we opt in to using it with this header
    topics = requests.get(REPOSITORY_TOPICS_URL.format(repoJSON['name']), headers=header, auth=(username, token))
    for topic in topics.json()['names']:
        if topic in life_cycle_stages:
            return topic

def isHelpWantedIssue(issueJSON):
    '''returns True if the issue described by issueJSON has
    the 'help-wanted' or 'help wanted' label, or False otherwise.

    Expects:
        - issueJSON: a JSON blob from the GitHub API, describing an issue
    '''
    for label in issueJSON['labels']:
        return label['name'] in ['help-wanted', 'help wanted']

def isHelpWantedRepo(repoJSON, username, token):
    '''returns the number of issues that return True from isHelpWantedIssue.

    Expects:
        - repoJSON: a JSON blob from the GitHub API, describing a repository
        - username: your GitHub username for authentication
        - token: a GitHub Personal Access Token, with public_repo scope
    '''
    REPOSITORY_ISSUES_URL = "https://api.github.com/repos/carpentries-incubator/{}/issues"
    issues = requests.get(REPOSITORY_ISSUES_URL.format(repoJSON['name']), auth=(username, token))
    help_wanted_issues = 0
    for issue in issues.json():
        if isHelpWantedIssue(issue):
            help_wanted_issues += 1
    return help_wanted_issues


def mostRecentRepo(repositoriesJSON):
    '''returns a tuple of the ISO format datetime of the most recent update in a
    given set of repositories, and the JSON blob for that most-recently-updated repository.

    Expects:
        - repositoriesJSON: a JSON blob describing a set of repositories
    '''
    most_recent = (None, None)
    for repo in repositoriesJSON:
        if most_recent[0] is not None:
            if datetime.fromisoformat(most_recent[0]) < datetime.fromisoformat(repo['updated_at'].rstrip('Z')):
                most_recent =  (repo['updated_at'].rstrip('Z'), repo)
        else:
            most_recent =  (repo['updated_at'].rstrip('Z'), repo)
    return most_recent


def updatedThisMonth(repositoriesJSON):
    '''returns the number of repositories that have been updated in the last
    30 days, in a given set of repositories.

    Expects:
        - repositoriesJSON: a JSON blob describing a set of repositories
    '''
    updated_repos = 0
    month = timedelta(days=30)
    one_month_ago = datetime.today() - month
    for repo in repositoriesJSON:
        if datetime.fromisoformat(repo['updated_at'].rstrip('Z')) > one_month_ago:
            updated_repos += 1
    return updated_repos


def getIncubatorRepos(username, token, per_page=100, page_num=1):
    '''returns a JSON blob of public repositories from
    The Carpentries Incubator organization (github.com/carpentries-incubator).

    Expects:
        - username: your GitHub username for authentication
        - token: a GitHub Personal Access Token, with public_repo scope
        - per_page: the maximum number of repositories to return per page
        - page_num: the page of results to return
    '''
    INCUBATOR_REPOS_URL = "https://api.github.com/orgs/carpentries-incubator/repos"
    response = requests.get(INCUBATOR_REPOS_URL,
        params={"type": "public",
                "per_page": per_page,
                "page": page_num},
        auth = (username, token))
    if 200 <= response.status_code < 300:
        return response.json()
    else:
        response.raise_for_status()


if __name__ == "__main__":
    USERNAME = sys.argv[1]
    TOKEN = sys.argv[2]

    repos = getIncubatorRepos(USERNAME, TOKEN)
    stage_counts = defaultdict(int)
    help_wanted_repos = 0
    for repo in repos:
        if isLessonRepo(repo, USERNAME, TOKEN):
            sleep(2) # be nice to GitHub's server, and wait two seconds between each request :)
            life_cycle = getLifeCycleStage(repo, USERNAME, TOKEN)
            if life_cycle:
                stage_counts[life_cycle] += 1
            if isHelpWantedRepo(repo, USERNAME, TOKEN):
                help_wanted_repos += 1
    total_lessons = 0
    for stage, count in stage_counts.items():
        sys.stdout.write(f'{stage}: {count}\n')
        total_lessons += count
    sys.stdout.write(f'total: {total_lessons}\n')
    percs = []
    stages = []
    for stage, count in stage_counts.items():
        percs.append(round((count*100)/total_lessons))
        stages.append(stage)
    if sum(percs) != 100:
        percs[percs.index(max(percs))] += 100 - sum(percs)
    for i in range(len(percs)):
        sys.stdout.write(f'perc_{stages[i]}: {percs[i]}\n')
    sys.stdout.write(f'help-wanted: {help_wanted_repos}\n')
    most_recent_date, most_recent_repo = mostRecentRepo(repos)
    sys.stdout.write(f'most-recent:\n  title: {most_recent_repo["description"]}\n  url: {most_recent_repo["html_url"]}\n  isodatetime: {most_recent_date}\n')
    recently_updated = updatedThisMonth(repos)
    sys.stdout.write(f'recently-updated: {recently_updated}\n')
