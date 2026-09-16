"""Protect the maintained Chrysalis schema from lossy plugin regeneration."""

from pathlib import Path
import unittest

import yaml


class TaskSchemaContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).resolve().parents[1] / "_types" / "task.md"
        cls.schema = yaml.safe_load(source.read_text().split("---", 2)[1])

    def test_framework_fields_and_lifecycle(self):
        schema = self.schema
        fields = schema["fields"]
        self.assertEqual(schema["version"], "0.2.0")
        self.assertEqual(fields["status"]["values"], ["todo", "in-progress", "done", "archived"])
        expected_types = {
            "title": "string", "dateCreated": "datetime", "due": "date",
            "scheduled": "date", "priority": "enum", "urgency_tier": "number",
            "modality": "string", "timeEstimate": "integer", "energy": "string",
            "friction": "string", "micro_chunked": "boolean", "tags": "list",
            "linked_zettels": "list", "project_ref": "link",
            "googleCalendarEventId": "string", "startedAt": "datetime",
            "completedAt": "datetime",
        }
        for name, field_type in expected_types.items():
            with self.subTest(field=name):
                self.assertEqual(fields[name]["type"], field_type)
        self.assertEqual(fields["linked_zettels"]["items"], {"type": "link"})

    def test_plugin_annotations_and_framework_nlp_remain_compatible(self):
        fields = self.schema["fields"]
        for name in ["title", "status", "priority", "due", "scheduled", "tags",
                     "dateCreated", "timeEstimate", "googleCalendarEventId"]:
            with self.subTest(field=name):
                self.assertEqual(fields[name]["tn_role"], name)
        self.assertEqual(fields["status"]["tn_completed_values"], ["done"])
        expected = [
            {"property_id": name, "trigger": trigger, "enabled": enabled}
            for name, trigger, enabled in [
                ("tags", "#", True), ("contexts", "@", True),
                ("projects", "+", True), ("status", "*", False),
                ("priority", "!", False),
            ]
        ]
        for namespace in ["x-chrysalis", "x-tasknotes"]:
            self.assertEqual(self.schema[namespace]["nlp"]["triggers"], expected)
