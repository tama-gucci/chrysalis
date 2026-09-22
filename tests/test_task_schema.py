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
        if "schema" in schema and "value" in schema["schema"]:
            props = schema["schema"]["value"]["properties"]
            self.assertIn(str(schema.get("version")), ["1", "0.2.0", "0.3.0"])
            self.assertEqual(props["status"]["enum"], ["todo", "in-progress", "done", "archived"])
            expected_props = {
                "title": "string", "dateCreated": "string", "due": ["string", "null"],
                "scheduled": ["string", "null"], "priority": "string", "urgency_tier": "integer",
                "modality": "string", "timeEstimate": "integer", "energy": "string",
                "friction": "string", "micro_chunked": "boolean", "tags": "array",
                "linked_zettels": "array", "project_ref": ["string", "null"],
                "googleCalendarEventId": ["string", "null"], "startedAt": ["string", "null"],
                "completedAt": ["string", "null"],
            }
            for name, prop_type in expected_props.items():
                with self.subTest(field=name):
                    self.assertEqual(props[name]["type"], prop_type)
            self.assertEqual(props["linked_zettels"]["items"]["type"], "string")
            return

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
        if "schema" in self.schema and "value" in self.schema["schema"]:
            self.assertIn("collection", self.schema)
            self.assertEqual(self.schema["collection"]["display"]["name_field"], "title")
            return

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
