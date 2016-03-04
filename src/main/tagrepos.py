# coding=utf-8
from __future__ import division, print_function
from os import path, chdir, getcwd
from shutil import rmtree
import collections
import argparse
import sys
import json
import functools
import subprocess
import pipes


class Git(object):
    def __init__(self, verbose=False):
        self.verbose = verbose

    def _call_git(self, *args):
        result = subprocess.check_output(['git'] + list(args))
        if self.verbose:
            print("git", " ".join(map(pipes.quote, args)))
            print(result)
        return result

    def __getattr__(self, name):
        return functools.partial(self._call_git, name)


class GitTagger(object):
    def __init__(self, directory):
        self.directory = directory
        self.repo_name = None
        self.msg = None
        self.start_dir = None
        self.git = None

    @staticmethod
    def get_repo_name(url):
        repo_name = path.basename(url)
        if url.endswith('.git'):
            repo_name = path.splitext(repo_name)[0]
        return repo_name

    def clone(self, repo, branch):
        self.start_dir = getcwd()
        chdir(self.directory)
        self.git = Git()
        self.git.clone(repo)
        self.repo_name = self.get_repo_name(repo)
        chdir(self.repo_name)
        self.git.checkout(branch)
        chdir(self.start_dir)

    def tag(self, name, revision):
        chdir(path.join(self.directory, self.repo_name))
        self.git.tag(name, revision)
        self.msg = 'Tagged {}:{} with {}'.format(self.repo_name, revision, name)
        chdir(self.start_dir)

    def branch(self, name, revision):
        chdir(path.join(self.directory, self.repo_name))
        self.git.branch(name, revision)
        self.msg = 'Branched {}:{} with {}'.format(self.repo_name, revision, name)
        chdir(self.start_dir)

    def push(self):
        chdir(path.join(self.directory, self.repo_name))
        self.git.push('--mirror')
        chdir(self.start_dir)

    def clean(self):
        chdir(self.directory)
        rmtree(self.repo_name)
        chdir(self.start_dir)


def tag_repos(directory, name, structure, branch_list=None, push=False, clean=False):
    if branch_list is None:
        branch_list = []
    for repo in structure:
        if repo['type'] != 'Git':
            print("Don't know how to handle material type " + repo['type'])
            print(repo)
            continue
        should_branch = False
        for pipeline in repo['pipelines']:
            if pipeline['name'] in branch_list:
                should_branch = True
        desc = repo['description']
        url_part, branch_part = desc.split(',')
        url = url_part.split(':', 1)[1].strip()
        branch = branch_part.split(':', 1)[1].strip()
        rev = repo['revision']
        tagger = GitTagger(directory)
        tagger.clone(url, branch)
        tagger.tag(name, rev)
        if should_branch:
            tagger.branch(name, rev)
        if push:
            tagger.push()
        if clean:
            tagger.clean()


def check_consistent(structure, label):
    revisions = collections.defaultdict(list)
    pipelines = collections.defaultdict(list)
    for repository in structure:
        description = repository['description']
        revision = repository['revision']
        revisions[description].append(revision)
        for pipeline in repository['pipelines']:
            name = pipeline['name']
            counter = pipeline['counter']
            pipelines[(description, revision)] = "{}/{}".format(name, counter)
    bad = False
    for description, revision_list in revisions.items():
        if len(revision_list) > 1:
            bad = True
            print('Repository {} used with more than one revision:'.format(description))
            for revision in revision_list:
                print('Revision {} used in build {}'.format(revision, pipelines[(description, revision)]))
    if bad:
        raise ValueError('Inconsistencies found in {}'.format(label))


def main():
    parser = argparse.ArgumentParser(
        description="Tag and/or branch a set of Git repositories as provided by json data.")
    parser.add_argument(
        'jsonfile',
        help='Json file as produced by gocdrepos. Read from stdin if no  filename given.',
        nargs='?',
        type=argparse.FileType('r'),
        default=sys.stdin)
    parser.add_argument(
        '-d', '--directory',
        default='/tmp',
        help="Parent directory of repository clones clones. Default to /tmp."
    )
    parser.add_argument(
        '-t', '--tag-name',
        required=True,
        help="Name of tag / branch to create."
    )
    parser.add_argument(
        '-b', '--branch-list',
        help="Comma-separated list of pipeline names. Create branches for these."
    )
    parser.add_argument(
        '-p', '--push',
        action='store_true',
        help="Push changes to remote repo."
    )
    parser.add_argument(
        '-c', '--clean',
        action='store_true',
        help="Remove cloned repo."
    )

    pargs = parser.parse_args()
    branch_list = [] if not pargs.branch_list else pargs.branch_list.split(',')
    structure = json.load(pargs.jsonfile)

    check_consistent(structure, pargs.jsonfile.name)
    tag_repos(pargs.directory, pargs.tag_name, structure, branch_list, pargs.push, pargs.clean)


if __name__ == '__main__':
    main()