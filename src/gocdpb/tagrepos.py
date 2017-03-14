# -*- coding: utf-8 -*-
from __future__ import division, print_function
from copy import deepcopy
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
        if self.verbose:
            print("git", " ".join(map(pipes.quote, args)))
        try:
            result = subprocess.check_output(['git'] + list(args), stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            # Make sure we always see what the stdout before re-raising the exception.
            # Otherwise it gets lost.
            print(e.output)
            raise

        if self.verbose:
            print(result)
        return result

    def __getattr__(self, name):
        return functools.partial(self._call_git, name)


class GitTagger(object):
    def __init__(self, directory, verbose=False):
        self.directory = directory
        self.repo_name = None
        self.msg = None
        self.start_dir = None
        self.git = None
        self.verbose = verbose

    @staticmethod
    def get_repo_name(url):
        repo_name = path.basename(url)
        if url.endswith('.git'):
            repo_name = path.splitext(repo_name)[0]
        return repo_name

    def clone(self, repo, branch):
        self.start_dir = getcwd()
        chdir(self.directory)
        self.git = Git(verbose=self.verbose)
        self.git.clone(repo)
        self.repo_name = self.get_repo_name(repo)
        chdir(self.repo_name)
        self.git.checkout(branch)
        chdir(self.start_dir)

    def tag(self, name, revision):
        chdir(path.join(self.directory, self.repo_name))
        try:
            self.git.tag(name, revision)
        except subprocess.CalledProcessError as e:
            # if the tag already exists, we should just carry on
            if "already exists" in e.output:
                print("tag {} already exists, continuing".format(name))
            else:
                raise

        self.msg = 'Tagged {}:{} with {}'.format(self.repo_name, revision, name)
        chdir(self.start_dir)

    def branch(self, name, revision):
        chdir(path.join(self.directory, self.repo_name))
        self.git.branch(name, revision)
        self.msg = 'Branched {}:{} with {}'.format(self.repo_name, revision, name)
        chdir(self.start_dir)

    def push(self, tag_or_branch):
        chdir(path.join(self.directory, self.repo_name))
        self.git.push('origin', tag_or_branch)
        chdir(self.start_dir)

    def clean(self):
        chdir(self.directory)
        rmtree(self.repo_name)
        chdir(self.start_dir)


def branch_tag_repos(directory, name, structure, branch_set=None, push=False, clean=False, verbose=False, tag=True):
    if branch_set is None:
        branch_set = set()
    for repo in structure:
        if repo['type'] != 'Git':
            print("Don't know how to handle material type " + repo['type'])
            print(repo)
            continue
        should_branch = False
        for pipeline in repo['pipelines']:
            if pipeline['name'] in branch_set:
                should_branch = True
        if not (tag or should_branch):
            continue
        desc = repo['description']
        url_part, branch_part = desc.split(',')
        url = url_part.split(':', 1)[1].strip()
        branch = branch_part.split(':', 1)[1].strip()
        rev = repo.get('revision') or repo['tag']
        tagger = GitTagger(directory, verbose)
        tagger.clone(url, branch)
        if should_branch:
            tagger.branch(name, rev)
        else:
            tagger.tag(name, rev)
        if push:
            tagger.push(name)
        if clean:
            tagger.clean()


def check_consistent(structure, label):
    revisions = collections.defaultdict(list)
    pipelines = collections.defaultdict(list)
    for repository in structure:
        description = repository['description']
        revision = repository.get('revision') or repository['tag']
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


def use_tag_in_repolist(repo_list, tag, repo=None, pipeline=None):
    repo_list_copy = deepcopy(repo_list)
    change_count = 0
    if repo:
        checker = lambda repo, mapping: repo in mapping['description']
        name = repo
    elif pipeline:
        checker = lambda pipeline, mapping: any(pipeline == pl['name'] for pl in mapping['pipelines'])
        name = pipeline
    else:
        raise ValueError('repo or pipeline must be provided')
    for entry in repo_list_copy:
        if checker(name, entry):
            del entry['revision']
            entry['tag'] = tag
            change_count += 1
    return repo_list_copy, change_count


def main_updaterepolist():
    parser = argparse.ArgumentParser(
        description="Update a json file created with gocdrepos to replace the "
                    "revision with a provided tag for a certain repository.")

    parser.add_argument(
        'jsonfile',
        help='Json file as produced by gocdrepos.',
        type=argparse.FileType('r'))
    parser.add_argument(
        '-t', '--tag-name',
        required=True,
        help="Name of branch to create."
    )
    parser.add_argument(
        '-r', '--repository',
        help="Substring of repository path (actually 'Description')."
    )

    pargs = parser.parse_args()
    structure = json.load(pargs.jsonfile)
    json_path = pargs.jsonfile.name
    check_consistent(structure, json_path)
    new_structure, count = use_tag_in_repolist(structure, pargs.tag_name, pargs.repository)
    if count != 1:
        print("Expected one change in file, but noticed", count)
    check_consistent(structure, json_path)
    with open(json_path, 'w') as jsonfile:
        json.dump(new_structure, jsonfile)


def parse_branch_list(fh):
    for line in fh.readlines():
        line = line.strip()
        if line:
            yield line;

def branch_set_from_args(pargs):
    branch_set = set();

    if pargs.branch_list:
        branch_set.update([x.strip() for x in pargs.branch_list.split(',')])

    if pargs.branch_list_from_file:
        branch_set.update(parse_branch_list(pargs.branch_list_from_file))

    return branch_set

def main_branchrepos():
    parser = argparse.ArgumentParser(
        description="Branch a set of Git repositories as provided by json data.")

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
        help="Name of branch to create."
    )
    parser.add_argument(
        '-b', '--branch-list',
        help="Comma-separated list of pipeline names. Create branches for these."
    )
    parser.add_argument(
        '-B', '--branch-list-from-file',
        type=argparse.FileType('r'),
        help="Pipeline names read in from file. Create branches for these."
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
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Verbose Git output."
    )

    pargs = parser.parse_args()
    branch_set = branch_set_from_args(pargs)
    structure = json.load(pargs.jsonfile)

    check_consistent(structure, pargs.jsonfile.name)
    branch_tag_repos(
        pargs.directory, pargs.tag_name, structure, branch_set, pargs.push, pargs.clean, pargs.verbose, tag=False
    )


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
        '-B', '--branch-list-from-file',
        type=argparse.FileType('r'),
        help="Pipeline names read in from file. Create branches for these."
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
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Verbose Git output."
    )

    pargs = parser.parse_args()
    branch_set = branch_set_from_args(pargs)
    structure = json.load(pargs.jsonfile)

    check_consistent(structure, pargs.jsonfile.name)
    branch_tag_repos(pargs.directory, pargs.tag_name, structure, branch_set, pargs.push, pargs.clean, pargs.verbose)


if __name__ == '__main__':
    main()
