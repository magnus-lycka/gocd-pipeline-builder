#!/usr/bin/python -tt
# coding:utf-8

from __future__ import division, print_function
import unittest
from gocdpb import tagrepos
import json
from os import getcwd, path, chdir
import sys

from subprocess import CalledProcessError as CPE

class MockSubprocess(object):
    response = u"Return from check_output args={}, kwargs={}"
    CalledProcessError = CPE
    STDERR = "sys.stderr"

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
            raise CPE(128, args[0], "tag already exists")
            #e.output = "tag already exists"
            #raise e
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
        "revision": "8e1ddbf0aa8f65295028413d0433247a72258aaf",
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
        tagger.push()
        tagger.clean()

        expected = [
            ('chdir', ('directory',), {}),
            u"Return from check_output args=(['git', 'clone', '/tmp/test1'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', ('test1',), {}),
            u"Return from check_output args=(['git', 'checkout', 'master'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', (startdir,), {}),
            ('chdir', ('directory/test1',), {}),
            u"Return from check_output args=(['git', 'tag', 'RELEASE-1.2.3', "
            u"'c142925e8d183b108020072143a669515612e8f3'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', (startdir,), {}),
            ('chdir', ('directory/test1',), {}),
            u"Return from check_output args=(['git', 'push', '--mirror'],), kwargs={'stdout': 'sys.stderr'}",
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
            u"Return from check_output args=(['git', 'clone', '/tmp/test1'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', ('test1',), {}),
            u"Return from check_output args=(['git', 'checkout', 'master'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', (startdir,), {}),
            ('chdir', ('directory/test1',), {}),
            u"Return from check_output args=(['git', 'tag', 'RELEASE-1.2.3', "
            u"'c142925e8d183b108020072143a669515612e8f3'],), kwargs={'stdout': 'sys.stderr'}",
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
            u"Return from check_output args=(['git', 'clone', '/tmp/test1'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', ('test1',), {}),
            u"Return from check_output args=(['git', 'checkout', 'master'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', (startdir,), {}),
            ('chdir', ('directory/test1',), {}),
            u"Return from check_output args=(['git', 'branch', 'RELEASE-1.2.3', "
            u"'c142925e8d183b108020072143a669515612e8f3'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', (startdir,), {})
        ]
        self.assertEqual(expected, self.log)


class TagReposTests(TestsBase):
    def test_tag_repos(self):
        directory = 'directory'
        tag = 'GUTEN_TAG'
        startdir = getcwd()

        tagrepos.tag_repos(directory,
                           tag,
                           testdata,
                           branch_list=['test2', 'test3', 'not_used'],
                           push=True,
                           clean=True)

        expected = [
            ('chdir', ('directory',), {}),
            u"Return from check_output args=(['git', 'clone', '/tmp/test3'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', ('test3',), {}),
            u"Return from check_output args=(['git', 'checkout', 'master'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test3',), {}),
            u"Return from check_output args=(['git', 'tag', 'GUTEN_TAG', "
            u"'ecc9ba924d30b29401ff06af6e6b7aa002a65ec6'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test3',), {}),
            u"Return from check_output args=(['git', 'branch', 'GUTEN_TAG', "
            u"'ecc9ba924d30b29401ff06af6e6b7aa002a65ec6'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test3',), {}),
            u"Return from check_output args=(['git', 'push', '--mirror'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', (startdir,), {}),
            ('chdir', ('directory',), {}),
            ('rmtree', ('test3',), {}),
            ('chdir', (startdir,), {}),

            ('chdir', ('directory',), {}),
            u"Return from check_output args=(['git', 'clone', '/tmp/test1'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', ('test1',), {}),
            u"Return from check_output args=(['git', 'checkout', 'master'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test1',), {}),
            u"Return from check_output args=(['git', 'tag', 'GUTEN_TAG', "
            u"'c142925e8d183b108020072143a669515612e8f3'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test1',), {}),
            u"Return from check_output args=(['git', 'push', '--mirror'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', (startdir,), {}),
            ('chdir', ('directory',), {}),
            ('rmtree', ('test1',), {}),
            ('chdir', (startdir,), {}),

            ('chdir', ('directory',), {}),
            u"Return from check_output args=(['git', 'clone', '/tmp/test2'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', ('test2',), {}),
            u"Return from check_output args=(['git', 'checkout', 'master'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test2',), {}),
            u"Return from check_output args=(['git', 'tag', 'GUTEN_TAG', "
            u"'8e1ddbf0aa8f65295028413d0433247a72258aaf'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test2',), {}),
            u"Return from check_output args=(['git', 'branch', 'GUTEN_TAG', "
            u"'8e1ddbf0aa8f65295028413d0433247a72258aaf'],), kwargs={'stdout': 'sys.stderr'}",
            ('chdir', (startdir,), {}),

            ('chdir', ('directory/test2',), {}),
            u"Return from check_output args=(['git', 'push', '--mirror'],), kwargs={'stdout': 'sys.stderr'}",
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


if __name__ == '__main__':
    unittest.main()
