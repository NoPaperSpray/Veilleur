"""Offline safety and recovery tests. Fake Discord, no credentials or live mutations."""
import copy
import tempfile
import time
import unittest
from pathlib import Path

from core import Service


class FakeAPI:
    def __init__(self):
        self.roles = [{"id": "1", "name": "@everyone", "permissions": "0", "position": 0,
                       "managed": False, "color": 0, "hoist": False, "mentionable": False}]
        self.channels = [{"id": "20", "guild_id": "1", "name": "général", "type": 0,
                          "position": 0, "parent_id": None, "permission_overwrites": []}]
        self.guild = {"id": "1", "name": "Test", "system_channel_id": "20"}
        self.members = {"30": {"roles": [], "nick": None, "communication_disabled_until": None}}
        self.messages = {"40": {"id": "40", "content": "avant", "embeds": [], "author": {"id": "99"}}}
        self.writes = []
        self.next_id = 100
        self.fail_mutation = False

    def request(self, method, path, data=None, reason=None):
        if method == "GET":
            if path == "/guilds/1":
                return copy.deepcopy(self.guild)
            if path == "/guilds/1/channels":
                return copy.deepcopy(self.channels)
            if path == "/guilds/1/roles":
                return copy.deepcopy(self.roles)
            if "/members/" in path:
                return copy.deepcopy(self.members[path.split("/")[-1]])
            if "/messages/" in path:
                return copy.deepcopy(self.messages[path.split("/")[-1]])
            if path.startswith("/channels/"):
                return copy.deepcopy(next(c for c in self.channels if c["id"] == path.split("/")[2]))
        self.writes.append((method, path, copy.deepcopy(data)))
        if self.fail_mutation:
            raise RuntimeError("Réponse réseau perdue")
        if method == "POST":
            self.next_id += 1
            item = dict(id=str(self.next_id), **copy.deepcopy(data))
            if path.endswith("/roles"):
                item.update(managed=False, position=len(self.roles))
                self.roles.append(item)
            elif path.endswith("/channels"):
                item.update(guild_id="1", position=len(self.channels), parent_id=data.get("parent_id"), permission_overwrites=[])
                self.channels.append(item)
            elif path.endswith("/messages"):
                self.messages[item["id"]] = item
            return copy.deepcopy(item)
        if method == "DELETE":
            if path.startswith("/channels/") and "/messages/" not in path:
                self.channels[:] = [c for c in self.channels if c["id"] != path.split("/")[-1]]
            if path.startswith("/guilds/1/roles/"):
                self.roles[:] = [r for r in self.roles if r["id"] != path.split("/")[-1]]
            return {"ok": True}
        if method == "PATCH" and path.startswith("/channels/"):
            if "/messages/" in path:
                item = self.messages[path.split("/")[-1]]
            else:
                item = next(c for c in self.channels if c["id"] == path.split("/")[-1])
            item.update(copy.deepcopy(data))
            return copy.deepcopy(item)
        if method == "PATCH" and path == "/guilds/1/roles":
            for position in data:
                next(r for r in self.roles if r["id"] == position["id"])["position"] = position["position"]
            return copy.deepcopy(self.roles)
        if method == "PATCH" and path.startswith("/guilds/1/roles/"):
            role = next(r for r in self.roles if r["id"] == path.split("/")[-1])
            role.update(copy.deepcopy(data))
            return copy.deepcopy(role)
        if method == "PATCH" and path == "/guilds/1":
            self.guild.update(copy.deepcopy(data))
            return copy.deepcopy(self.guild)
        return {"ok": True}


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.api = FakeAPI()
        self.s = Service(Path(self.temp.name), "1", self.api)

    def plan(self, actions=None):
        actions = actions or [{"action": "creer_role", "params": {"name": "Dev"}, "ref": "dev"}]
        return self.s.preview("Test", actions)["plan_id"]

    def approve_fake(self, plan_id, **overrides):
        # Only simulated human approvals in a temporary isolated test folder.
        approval = {"decision": "approved", "at": time.time(), "sha256": self.s.plan(plan_id)["sha256"]}
        approval.update(overrides)
        self.s.save("approvals", plan_id, approval)

    def test_preview_never_writes_discord(self):
        self.plan()
        self.assertEqual(self.api.writes, [])

    def test_unapproved_plan_cannot_execute(self):
        with self.assertRaisesRegex(ValueError, "Approbation"):
            self.s.execute(self.plan())
        self.assertEqual(self.api.writes, [])

    def test_rejected_expired_future_or_wrong_approval_blocked(self):
        for override in ({"decision": "rejected"}, {"at": time.time() - 601}, {"at": time.time() + 99}, {"sha256": "incorrect"}):
            plan_id = self.plan()
            self.approve_fake(plan_id, **override)
            with self.assertRaises(ValueError):
                self.s.execute(plan_id)
        self.assertEqual(self.api.writes, [])

    def test_altered_plan_blocked(self):
        plan_id = self.plan()
        self.approve_fake(plan_id)
        p = self.s.plan(plan_id)
        p["payload"]["operations"][0]["params"]["name"] = "Autre"
        self.s.save("plans", plan_id, p)
        with self.assertRaisesRegex(ValueError, "altéré"):
            self.s.execute(plan_id)

    def test_server_change_blocks_execution(self):
        plan_id = self.plan()
        self.approve_fake(plan_id)
        self.api.guild["name"] = "Changement externe"
        with self.assertRaisesRegex(ValueError, "changé"):
            self.s.execute(plan_id)
        self.assertEqual(self.api.writes, [])

    def test_target_member_change_blocks_execution(self):
        plan_id = self.plan([{"action": "modifier_membre", "params": {"membre_id": "30", "data": {"nick": "Nouveau"}}}])
        self.approve_fake(plan_id)
        self.api.members["30"]["nick"] = "Externe"
        with self.assertRaisesRegex(ValueError, "changé"):
            self.s.execute(plan_id)

    def test_target_message_change_blocks_execution(self):
        plan_id = self.plan([{"action": "modifier_message", "params": {"salon_id": "20", "message_id": "40", "data": {"content": "après"}}}])
        self.approve_fake(plan_id)
        self.api.messages["40"]["content"] = "Externe"
        with self.assertRaisesRegex(ValueError, "changé"):
            self.s.execute(plan_id)

    def test_approved_execution_backs_up_and_is_single_use(self):
        plan_id = self.plan()
        self.approve_fake(plan_id)
        result = self.s.execute(plan_id)
        self.assertEqual(result["status"], "completed")
        backup = self.s.read("backups", result["backup_id"])
        self.assertEqual(len(backup["state"]["roles"]), 1)
        with self.assertRaisesRegex(ValueError, "consommé"):
            self.s.execute(plan_id)
        self.assertEqual(len(self.api.writes), 1)

    def test_backup_failure_prevents_all_mutations(self):
        plan_id = self.plan()
        self.approve_fake(plan_id)
        def failed(*args):
            raise OSError("Disque plein")
        self.s.backup = failed
        with self.assertRaises(OSError):
            self.s.execute(plan_id)
        self.assertEqual(self.api.writes, [])

    def test_failure_stops_plan_without_replay(self):
        plan_id = self.plan([{"action": "creer_role", "params": {"name": "A"}}, {"action": "creer_role", "params": {"name": "B"}}])
        self.approve_fake(plan_id)
        self.api.fail_mutation = True
        result = self.s.execute(plan_id)
        self.assertEqual(result["status"], "partial_failure")
        self.assertEqual(len(self.api.writes), 1)
        self.assertEqual(self.s.read("runs", result["run_id"])["steps"][0]["status"], "failed_or_uncertain")
        with self.assertRaises(ValueError):
            self.s.restoration(result["backup_id"], result["run_id"])

    def test_refs_resolved_only_in_ids_and_mentions_disabled(self):
        plan_id = self.plan([{"action": "creer_salon", "params": {"name": "Accueil", "type": 0}, "ref": "accueil"},
                             {"action": "envoyer_message", "params": {"salon_id": "@accueil", "content": "@accueil"}}])
        self.approve_fake(plan_id)
        self.s.execute(plan_id)
        self.assertEqual(self.api.writes[-1][2]["content"], "@accueil")
        self.assertEqual(self.api.writes[-1][2]["allowed_mentions"], {"parse": []})
        self.assertNotIn("@accueil", self.api.writes[-1][1])

    def test_invalid_action_and_paths_rejected(self):
        for actions in ([{"action": "http", "params": {"url": "https://evil"}}],
                        [{"action": "supprimer_salon", "params": {"salon_id": "20/../../other"}}],
                        [{"action": "creer_role", "params": {"name": "A", "unexpected": True}}],
                        [{"action": "supprimer_salon", "params": {"salon_id": "@unknown"}}]):
            with self.assertRaises(ValueError):
                self.plan(actions)

    def test_cross_guild_channel_rejected(self):
        self.api.channels[0]["guild_id"] = "2"
        with self.assertRaisesRegex(ValueError, "hors"):
            self.plan([{"action": "supprimer_salon", "params": {"salon_id": "20"}}])

    def test_protected_role_rejected(self):
        with self.assertRaisesRegex(ValueError, "protégé"):
            self.plan([{"action": "supprimer_role", "params": {"role_id": "1"}}])

    def test_mutually_exclusive_permissions_rejected(self):
        with self.assertRaises(ValueError):
            self.plan([{"action": "permissions_salon", "params": {"salon_id": "20", "cible_id": "1", "type": 0, "allow": "1024", "deny": "1024"}}])

    def test_oversized_embed_rejected(self):
        with self.assertRaises(ValueError):
            self.plan([{"action": "envoyer_message", "params": {"salon_id": "20", "embeds": [{"description": "x" * 4097}]}}])

    def test_restore_missing_categories_roles_and_permissions_remaps_ids(self):
        self.api.roles.append(dict(id="12", name="Dev", permissions="0", position=1, managed=False))
        self.api.channels.append(dict(id="22", guild_id="1", name="Cat", type=4, position=0, parent_id=None, permission_overwrites=[]))
        self.api.channels[0]["parent_id"] = "22"
        self.api.channels[0]["permission_overwrites"] = [{"id": "12", "type": 0, "allow": "1024", "deny": "0"}]
        backup = self.s.backup()
        self.api.roles = self.api.roles[:1]
        self.api.channels = []
        preview = self.s.restoration(backup["backup_id"])
        actions = preview["actions"]
        modifications = [op["params"]["data"] for op in actions if op["action"] == "modifier_salon"]
        child = next(d for d in modifications if d["name"] == "général")
        self.assertEqual(child["parent_id"], "@salon22")
        self.assertEqual(child["permission_overwrites"][0]["id"], "@role12")
        self.assertEqual(self.api.writes, [])

    def test_undo_creations_is_preview_then_requires_approval(self):
        plan_id = self.plan()
        self.approve_fake(plan_id)
        run = self.s.execute(plan_id)
        preview = self.s.restoration(run["backup_id"], run["run_id"])
        self.assertTrue(any(op["action"] == "supprimer_role" for op in preview["actions"]))
        with self.assertRaisesRegex(ValueError, "Approbation"):
            self.s.execute(preview["plan_id"])

    def test_permission_request_uses_guild_channel_and_target(self):
        action = {"action": "permissions_salon", "params": {"salon_id": "20", "cible_id": "1", "type": 0, "allow": "1024", "deny": "2048"}}
        self.s.execute_operation(action, "test")
        self.assertEqual(self.api.writes[-1][:2], ("PUT", "/channels/20/permissions/1"))

    def test_member_role_request_uses_correct_ids(self):
        for action, method in (("ajouter_role", "PUT"), ("retirer_role", "DELETE")):
            self.s.execute_operation({"action": action, "params": {"membre_id": "30", "role_id": "12"}}, "test")
            self.assertEqual(self.api.writes[-1][:2], (method, "/guilds/1/members/30/roles/12"))

    def test_exclusive_lock(self):
        other = Service(Path(self.temp.name), "1", self.api)
        with self.s.execution_lock():
            with self.assertRaisesRegex(ValueError, "autre exécution"):
                with other.execution_lock():
                    pass

    def test_unchanged_backup_does_not_produce_mutation(self):
        backup = self.s.backup()
        preview = self.s.restoration(backup["backup_id"])
        self.assertEqual(preview["actions"], [])
        self.assertEqual(self.api.writes, [])

    def test_restore_missing_resources_can_be_executed_after_fake_approval(self):
        self.api.roles.append(dict(id="12", name="Dev", permissions="1024", position=1, managed=False))
        backup = self.s.backup()
        self.api.roles = self.api.roles[:1]
        self.api.channels = []
        self.api.guild["system_channel_id"] = None
        preview = self.s.restoration(backup["backup_id"])
        self.approve_fake(preview["plan_id"])
        result = self.s.execute(preview["plan_id"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(self.api.channels), 1)
        self.assertEqual(self.api.channels[0]["name"], "général")
        self.assertNotEqual(self.api.channels[0]["id"], "20")
        self.assertEqual(self.api.guild["system_channel_id"], self.api.channels[0]["id"])
        self.assertEqual(self.api.roles[-1]["name"], "Dev")

    def test_undo_rename_and_message_edit_restores_original_values(self):
        plan_id = self.plan([{"action": "modifier_salon", "params": {"salon_id": "20", "data": {"name": "après"}}},
                             {"action": "modifier_message", "params": {"salon_id": "20", "message_id": "40", "data": {"content": "après"}}}])
        self.approve_fake(plan_id)
        run = self.s.execute(plan_id)
        self.assertEqual(self.api.channels[0]["name"], "après")
        undo = self.s.restoration(run["backup_id"], run["run_id"])
        self.approve_fake(undo["plan_id"])
        result = self.s.execute(undo["plan_id"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(self.api.channels[0]["name"], "général")
        self.assertEqual(self.api.messages["40"]["content"], "avant")

    def test_undo_created_role_execution_removes_it(self):
        plan_id = self.plan()
        self.approve_fake(plan_id)
        run = self.s.execute(plan_id)
        undo = self.s.restoration(run["backup_id"], run["run_id"])
        self.approve_fake(undo["plan_id"])
        self.assertEqual(self.s.execute(undo["plan_id"])["status"], "completed")
        self.assertEqual(len(self.api.roles), 1)


if __name__ == "__main__":
    unittest.main()
