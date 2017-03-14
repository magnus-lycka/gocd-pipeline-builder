#!/usr/bin/python -tt
# -*- coding: utf-8 -*-

from __future__ import division, print_function
from collections import namedtuple
import unittest
from gocdpb import tagrepos
import json
from os import getcwd, path, chdir
import argparse

from subprocess import CalledProcessError as Cpe


class MockSubprocess(object):
    response = u"Return from check_output args={}, kwargs={}"
    CalledProcessError = Cpe
    STDOUT = "sys.stdout"

    def __init__(self, log=None):
        self.check_output_args = []
        self.check_output_kwargs = []
        if log is None:
            log = []
        self.log = log
        self.raise_when_tagging = False

    def check_output(self, *args, **kwargs):
        self.check_output_args.append(args)
        self.check_output_kwargs.append(kwargs)
        response = self.response.format(args, kwargs)
        self.log.append(response)
        if self.raise_when_tagging and args and 'tag' in args[0]:
            raise Cpe(128, args[0], "tag already exists")
        return response

    def set_raise_when_tagging(self):
        self.raise_when_tagging = True


class MockCall(object):
    def __init__(self, name, log=None):
        self.name = name
        if log is None:
            log = []
        self.log = log

    def __call__(self, *args, **kwargs):
        self.log.append((self.name, args, kwargs))


testdata = [
    {
        "description": "URL: /tmp/test3, Branch: master",
        "pipelines": [
            {
                "counter": "3",
                "name": "test3"
            }
        ],
        "revision": "ecc9ba924d30b29401ff06af6e6b7aa002a65ec6",
        "type": "Git"
    },
    {
        "description": "URL: /tmp/test1, Branch: master",
        "pipelines": [
            {
                "counter": "2",
                "name": "test1"
            }
        ],
        "revision": "c142925e8d183b108020072143a669515612e8f3",
        "type": "Git"
    },
    {
        "description": "URL: /tmp/test2, Branch: master",
        "pipelines": [
            {
                "counter": "3",
                "name": "test2"
            }
        ],
        #"revision": "8e1ddbf0aa8f65295028413d0433247a72258aaf",
        "tag": "tagga-ner",
        "type": "Git"
    }
]


class TestsBase(unittest.TestCase):
    def setUp(self):
        self._saved_subprocess = tagrepos.subprocess
        self._saved_chdir = tagrepos.chdir
        self._saved_rmtree = tagrepos.chdir
        self.log = []
        tagrepos.subprocess = MockSubprocess(log=self.log)
        tagrepos.chdir = MockCall('chdir', log=self.log)
        tagrepos.rmtree = MockCall('rmtree', log=self.log)

    def tearDown(self):
        tagrepos.subprocess = self._saved_subprocess
        tagrepos.chdir = self._saved_chdir
        tagrepos.rmtree = self._saved_rmtree


class GitTaggerTests(TestsBase):
    def test_tag_repos(self):
        directory = 'directory'
        repo = '/tmp/test1'
        branch = 'master'
        rev = "c142925e8d183b108020072143a669515612e8f3"
        tag = 'RELEASE-1.2.3'
        startdir = getcwd()

        tagger = tagrepos.GitTagger(directory)
        tagger.clone(repo, branch)
        tagger.tag(tag, rev)
        tagger.push(tag)
        tagger.clean()

        expected = [
            ('chdir', ('directory',), {}),
            u"Return from check_output args=(['git', 'clone', '/tmp/test1'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', ('test1',), {}),
            u"Return from check_output args=(['git', 'checkout', 'master'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),
            ('chdir', ('directory/test1',), {}),
            u"Return from check_output args=(['git', 'tag', 'RELEASE-1.2.3', "
            u"'c142925e8d183b108020072143a669515612e8f3'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),
            ('chdir', ('directory/test1',), {}),
            u"Return from check_output args=(['git', 'push', 'origin', "
            u"'RELEASE-1.2.3'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),
            ('chdir', ('directory',), {}),
            ('rmtree', ('test1',), {}),
            ('chdir', (startdir,), {})
        ]
        self.assertEqual(expected, self.log)

    def test_tag_repos_when_tag_already_exists(self):
        tagrepos.subprocess.set_raise_when_tagging()

        directory = 'directory'
        repo = '/tmp/test1'
        branch = 'master'
        rev = "c142925e8d183b108020072143a669515612e8f3"
        tag = 'RELEASE-1.2.3'
        startdir = getcwd()

        tagger = tagrepos.GitTagger(directory)
        tagger.clone(repo, branch)
        tagger.tag(tag, rev)

        expected = [
            ('chdir', ('directory',), {}),
            u"Return from check_output args=(['git', 'clone', '/tmp/test1'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', ('test1',), {}),
            u"Return from check_output args=(['git', 'checkout', 'master'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),
            ('chdir', ('directory/test1',), {}),
            u"Return from check_output args=(['git', 'tag', 'RELEASE-1.2.3', "
            u"'c142925e8d183b108020072143a669515612e8f3'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),

        ]
        self.assertEqual(expected, self.log)

    def test_branch_repos(self):
        directory = 'directory'
        repo = '/tmp/test1'
        branch = 'master'
        rev = "c142925e8d183b108020072143a669515612e8f3"
        tag = 'RELEASE-1.2.3'
        startdir = getcwd()

        tagger = tagrepos.GitTagger(directory)
        tagger.clone(repo, branch)
        tagger.branch(tag, rev)

        expected = [
            ('chdir', ('directory',), {}),
            u"Return from check_output args=(['git', 'clone', '/tmp/test1'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', ('test1',), {}),
            u"Return from check_output args=(['git', 'checkout', 'master'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),
            ('chdir', ('directory/test1',), {}),
            u"Return from check_output args=(['git', 'branch', 'RELEASE-1.2.3', "
            u"'c142925e8d183b108020072143a669515612e8f3'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {})
        ]
        self.assertEqual(expected, self.log)


class TagReposTests(TestsBase):
    def test_branch_and_tag_repos(self):
        directory = 'directory'
        tag = 'GUTEN_TAG'
        startdir = getcwd()

        tagrepos.branch_tag_repos(directory,
                                  tag,
                                  testdata,
                                  branch_set=set(['test2', 'test3', 'not_used']),
                                  push=True,
                                  clean=True)

        expected = [
            ('chdir', ('directory',), {}),
            u"Return from check_output args=(['git', 'clone', '/tmp/test3'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', ('test3',), {}),
            u"Return from check_output args=(['git', 'checkout', 'master'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test3',), {}),
            u"Return from check_output args=(['git', 'branch', 'GUTEN_TAG', "
            u"'ecc9ba924d30b29401ff06af6e6b7aa002a65ec6'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test3',), {}),
            u"Return from check_output args=(['git', 'push', 'origin', 'GUTEN_TAG'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),
            ('chdir', ('directory',), {}),
            ('rmtree', ('test3',), {}),
            ('chdir', (startdir,), {}),

            ('chdir', ('directory',), {}),
            u"Return from check_output args=(['git', 'clone', '/tmp/test1'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', ('test1',), {}),
            u"Return from check_output args=(['git', 'checkout', 'master'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test1',), {}),
            u"Return from check_output args=(['git', 'tag', 'GUTEN_TAG', "
            u"'c142925e8d183b108020072143a669515612e8f3'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test1',), {}),
            u"Return from check_output args=(['git', 'push', 'origin', 'GUTEN_TAG'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),
            ('chdir', ('directory',), {}),
            ('rmtree', ('test1',), {}),
            ('chdir', (startdir,), {}),

            ('chdir', ('directory',), {}),
            u"Return from check_output args=(['git', 'clone', '/tmp/test2'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', ('test2',), {}),
            u"Return from check_output args=(['git', 'checkout', 'master'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test2',), {}),
            u"Return from check_output args=(['git', 'branch', 'GUTEN_TAG', "
            u"'tagga-ner'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test2',), {}),
            u"Return from check_output args=(['git', 'push', 'origin', 'GUTEN_TAG'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),
            ('chdir', ('directory',), {}),
            ('rmtree', ('test2',), {}),
            ('chdir', (startdir,), {}),
        ]
        self.assertEqual(expected, self.log)

    def test_branch_repos(self):
        """
        same as test_brand_and_tag_repos, but skip repos we don't tag
        """
        directory = 'directory'
        tag = 'GUTEN_TAG'
        startdir = getcwd()

        tagrepos.branch_tag_repos(directory,
                                  tag,
                                  testdata,
                                  branch_set=set(['test2', 'test3', 'not_used']),
                                  push=True,
                                  clean=True,
                                  tag=False)

        expected = [
            ('chdir', ('directory',), {}),
            u"Return from check_output args=(['git', 'clone', '/tmp/test3'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', ('test3',), {}),
            u"Return from check_output args=(['git', 'checkout', 'master'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test3',), {}),
            u"Return from check_output args=(['git', 'branch', 'GUTEN_TAG', "
            u"'ecc9ba924d30b29401ff06af6e6b7aa002a65ec6'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test3',), {}),
            u"Return from check_output args=(['git', 'push', 'origin', 'GUTEN_TAG'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),
            ('chdir', ('directory',), {}),
            ('rmtree', ('test3',), {}),
            ('chdir', (startdir,), {}),

            ('chdir', ('directory',), {}),
            u"Return from check_output args=(['git', 'clone', '/tmp/test2'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', ('test2',), {}),
            u"Return from check_output args=(['git', 'checkout', 'master'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test2',), {}),
            u"Return from check_output args=(['git', 'branch', 'GUTEN_TAG', "
            u"'tagga-ner'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test2',), {}),
            u"Return from check_output args=(['git', 'push', 'origin', 'GUTEN_TAG'],), kwargs={'stderr': 'sys.stdout'}",
            ('chdir', (startdir,), {}),
            ('chdir', ('directory',), {}),
            ('rmtree', ('test2',), {}),
            ('chdir', (startdir,), {}),
        ]
        self.assertEqual(expected, self.log)

    def test_consistency(self):
        # Find files from unittest.discover
        if __name__ != '__main__':
            root_dir = path.dirname(path.realpath(__file__))
            chdir(root_dir)
        structure = json.load(open('testdata/good_repos.json'))
        self.assertIsNone(tagrepos.check_consistent(structure, 'this-works/261'))

    def test_inconsistency(self):
        # Find files from unittest.discover
        if __name__ != '__main__':
            root_dir = path.dirname(path.realpath(__file__))
            chdir(root_dir)
        structure = json.load(open('testdata/bad_repos.json'))
        self.assertRaises(ValueError, tagrepos.check_consistent, structure, 'this-does-not-work/261')

    def helper_define_by_tag(self):
        pipeline = 'want'
        repo = 'this/I/want.git'
        tag = 'MyTag'
        old = [
            {
                "description": "URL: ssh://git@git/{}, Branch: master".format(repo),
                "pipelines": [
                    {
                        "counter": "15",
                        "name": pipeline
                    }
                ],
                "revision": "123",
                "type": "Git"
            },
            {
                "description": "URL: ssh://git@git/not/this/one.git, Branch: master",
                "pipelines": [
                    {
                        "counter": "9",
                        "name": "one"
                    }
                ],
                "revision": "456",
                "type": "Git"
            }
        ]

        def assertions(structure):
            self.assertEqual(structure[0].get('tag'), tag)
            self.assertEqual(structure[0].get('revision'), None)
            self.assertEqual(structure[1].get('tag'), None)
            self.assertEqual(structure[1].get('revision'), "456")

        TestData = namedtuple('TestData', 'repo pipeline old tag assertions')
        return TestData(repo, pipeline, old, tag, assertions)

    def test_define_by_tag_fail(self):
        self.assertRaises(ValueError, tagrepos.use_tag_in_repolist, [], 'tag')

    def test_define_by_tag_repo(self):
        helper = self.helper_define_by_tag()
        new_repolist, change_count = tagrepos.use_tag_in_repolist(helper.old, helper.tag, repo=helper.repo)
        self.assertEqual(change_count, 1)
        helper.assertions(new_repolist)

    def test_define_by_tag_pipeline(self):
        helper = self.helper_define_by_tag()
        new_repolist, change_count = tagrepos.use_tag_in_repolist(helper.old, helper.tag, pipeline=helper.pipeline)
        self.assertEqual(change_count, 1)
        helper.assertions(new_repolist)

class BranchParamTests(TestsBase):
    def test_branch_list_empty(self):
        pargs = argparse.Namespace
        pargs.branch_list = None
        pargs.branch_list_from_file = None

        x = tagrepos.branch_set_from_args(pargs)
        self.assertEqual(x, set([]))

    def test_branch_list_cmd(self):
        pargs = argparse.Namespace
        pargs.branch_list = "abc, def"
        pargs.branch_list_from_file = None

        x = tagrepos.branch_set_from_args(pargs)
        self.assertEqual(x, set(['abc', 'def']))

    def test_branch_list_file(self):
        # Find files from unittest.discover
        if __name__ != '__main__':
            root_dir = path.dirname(path.realpath(__file__))
            chdir(root_dir)

        pargs = argparse.Namespace
        pargs.branch_list = None
        pargs.branch_list_from_file = open("testdata/pipeline.txt")

        x = tagrepos.branch_set_from_args(pargs)
        self.assertEqual(x, set(['abc', 'def']))

    def test_branch_list_cmd_and_file_with_duplicates(self):
        # Find files from unittest.discover
        if __name__ != '__main__':
            root_dir = path.dirname(path.realpath(__file__))
            chdir(root_dir)

        pargs = argparse.Namespace
        pargs.branch_list = "abc, ghi"
        pargs.branch_list_from_file = open("testdata/pipeline.txt")

        x = tagrepos.branch_set_from_args(pargs)
        self.assertEqual(x, set(['abc', 'def', 'ghi']))

if __name__ == '__main__':
    unittest.main()
