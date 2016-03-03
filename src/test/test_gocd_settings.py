import unittest
import json
from gocd_settings import Pipeline

TEST_DATA1 = '''{
    "build_cause": {
        "material_revisions": [
            {
                "changed": false,
                "material": {
                    "description": "URL: /tmp/test3, Branch: master",
                    "fingerprint": "48cba2b88c48c4ad485fb9dab6ba505170d0a02fce6e1b6cdaa1f2af730aec17",
                    "id": 2,
                    "type": "Git"
                },
                "modifications": [
                    {
                        "comment": "test",
                        "email_address": null,
                        "id": 3,
                        "modified_time": 1455889817000,
                        "revision": "ecc9ba924d30b29401ff06af6e6b7aa002a65ec6",
                        "user_name": "Your Name <you@example.com>"
                    }
                ]
            },
            {
                "changed": false,
                "material": {
                    "description": "test1",
                    "fingerprint": "74a4c922452603d7ceb7950807208172bdacefebe1d3e43bdb05bac21750a995",
                    "id": 4,
                    "type": "Pipeline"
                },
                "modifications": [
                    {
                        "comment": "Unknown",
                        "email_address": null,
                        "id": 7,
                        "modified_time": 1455890779505,
                        "revision": "test1/2/defaultStage/1",
                        "user_name": "Unknown"
                    }
                ]
            },
            {
                "changed": true,
                "material": {
                    "description": "test2",
                    "fingerprint": "ba8efc100441d356366f169dc4d10f0c30b410f11ea58cb36c34fe987ed7980e",
                    "id": 5,
                    "type": "Pipeline"
                },
                "modifications": [
                    {
                        "comment": "Unknown",
                        "email_address": null,
                        "id": 8,
                        "modified_time": 1455890819738,
                        "revision": "test2/3/defaultStage/1",
                        "user_name": "Unknown"
                    }
                ]
            }
        ],
        "trigger_forced": false,
        "trigger_message": "triggered by test2/3/defaultStage/1"
    },
    "can_run": true,
    "comment": null,
    "counter": 3,
    "id": 8,
    "label": "3",
    "name": "test3",
    "natural_order": 3.0,
    "preparing_to_schedule": false,
    "stages": [
        {
            "approval_type": "success",
            "approved_by": "changes",
            "can_run": true,
            "counter": "1",
            "id": 8,
            "jobs": [
                {
                    "id": 8,
                    "name": "defaultJob",
                    "result": "Passed",
                    "scheduled_date": 1455890861129,
                    "state": "Completed"
                }
            ],
            "name": "defaultStage",
            "operate_permission": true,
            "rerun_of_counter": null,
            "result": "Passed",
            "scheduled": true
        }
    ]
}
'''


TEST_DATA2 = '''{
    "build_cause": {
        "material_revisions": [
        ]
    },
    "can_run": true,
    "comment": null,
    "counter": 3,
    "id": 8,
    "label": "3",
    "name": "test3",
    "natural_order": 3.0,
    "preparing_to_schedule": false,
    "stages": [
        {
            "approval_type": "success",
            "approved_by": "changes",
            "can_run": true,
            "counter": "1",
            "id": 8,
            "jobs": [
                {
                    "id": 8,
                    "name": "defaultJob",
                    "result": "Passed",
                    "scheduled_date": 1455890861129,
                    "state": "Completed"
                }
            ],
            "name": "defaultStage",
            "operate_permission": true,
            "rerun_of_counter": null,
            "result": "Passed",
            "scheduled": true
        }
    ]
}
'''


class StubGo(object):
    def __init__(self):
        self.first_call = True

    def get_pipeline_instance(self, pipeline, instance):
        if self.first_call:
            self.first_call = False
            return json.loads(TEST_DATA1)
        else:
            return json.loads(TEST_DATA2)


class GocdSettingsTests(unittest.TestCase):
    def test_get_pipelines_with_several_version_of_same_material(self):
        pl = Pipeline('test3/3', StubGo(), 'json')
        pl.prepare_recursive_repos()
        self.assertEqual([(x.pipeline, x.instance) for x in pl.upstreams], [(u'test1', u'2'), (u'test2', u'3')])
        self.assertEqual([x.as_dict() for x in pl.source_repos],
                         [{'type': u'Git', 'description': u'URL: /tmp/test3, Branch: master',
                           'revision': u'ecc9ba924d30b29401ff06af6e6b7aa002a65ec6'}])


if __name__ == '__main__':
    unittest.main()
