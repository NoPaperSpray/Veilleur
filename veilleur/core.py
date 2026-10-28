"""Plans, Discord requests and the bits needed to undo them."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

import httpx

SCHEMA = 2
CHANNEL_FIELDS = {"name", "type", "topic", "position", "parent_id", "nsfw",
                  "rate_limit_per_user", "bitrate", "user_limit", "permission_overwrites"}
ROLE_FIELDS = {"name", "permissions", "color", "hoist", "mentionable"}
GUILD_FIELDS = {"name", "description", "verification_level", "default_message_notifications",
                "explicit_content_filter", "afk_channel_id", "afk_timeout", "system_channel_id"}
MEMBER_FIELDS = {"nick", "communication_disabled_until"}
CATALOG = {
    "creer_salon": ({"name", "type"}, CHANNEL_FIELDS),
    "modifier_salon": ({"salon_id", "data"}, {"salon_id", "data"}),
    "supprimer_salon": ({"salon_id"}, {"salon_id"}),
    "creer_role": ({"name"}, ROLE_FIELDS),
    "modifier_role": ({"role_id", "data"}, {"role_id", "data"}),
    "supprimer_role": ({"role_id"}, {"role_id"}),
    "position_role": ({"role_id", "position"}, {"role_id", "position"}),
    "permissions_salon": ({"salon_id", "cible_id", "type", "allow", "deny"},
                          {"salon_id", "cible_id", "type", "allow", "deny"}),
    "retirer_permissions": ({"salon_id", "cible_id"}, {"salon_id", "cible_id"}),
    "ajouter_role": ({"membre_id", "role_id"}, {"membre_id", "role_id"}),
    "retirer_role": ({"membre_id", "role_id"}, {"membre_id", "role_id"}),
    "modifier_membre": ({"membre_id", "data"}, {"membre_id", "data"}),
    "envoyer_message": (set(), {"salon_id", "content", "embeds"}),
    "modifier_message": ({"salon_id", "message_id", "data"}, {"salon_id", "message_id", "data"}),
    "supprimer_message": ({"salon_id", "message_id"}, {"salon_id", "message_id"}),
    "modifier_serveur": ({"data"}, {"data"}),
}
LIMITS = [
    "Une suppression Discord est irréversible : les éléments recréés ont de nouveaux IDs.",
    "Les messages supprimés ne retrouvent pas leur auteur, leur date, leurs réactions ou leurs pièces jointes.",
    "Les sauvegardes couvrent la structure et les membres/messages ciblés, pas tout l'historique du serveur.",
    "Les salons que le bot ne voit pas peuvent manquer de la sauvegarde.",
    "Supprimer un rôle ne sauvegarde pas toutes ses affectations. Les fils, invitations et intégrations ne sont pas restaurés.",
    "La restauration est un nouveau plan à approuver ; elle ne s'exécute jamais automatiquement.",
]


def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(data):
    return hashlib.sha256(canonical(data).encode()).hexdigest()


def snowflake(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,22}", value):
        raise ValueError("Identifiant Discord invalide (texte numérique requis)")
    return value


def select(data, fields):
    return {key: copy.deepcopy(data[key]) for key in fields if key in data}


def permission_report(state, member):
    """Report guild-level role permissions; channel overrides are separate."""
    roles = state["roles"]
    guild_id = state["serveur"]["id"]
    member_roles = set(member.get("roles", []))
    selected = [role for role in roles if role["id"] == guild_id or role["id"] in member_roles]
    mask = 0
    for role in selected:
        mask |= int(role.get("permissions", "0"))
    admin = bool(mask & (1 << 3))
    bits = {"voir_salons": 10, "gerer_salons": 4, "gerer_roles": 28, "gerer_serveur": 5,
            "envoyer_messages": 11, "integrer_liens": 14, "lire_historique": 16, "moderation": 40}
    return {"administrateur": admin,
            "permissions_serveur": {name: admin or bool(mask & (1 << bit)) for name, bit in bits.items()},
            "role_le_plus_haut": max((r for r in selected if r["id"] != guild_id),
                                     key=lambda r: r.get("position", 0), default=None),
            "salons_visibles": len(state["salons"]),
            "limites": ["Les permissions propres aux salons ne sont pas calculées ici.",
                        "Le bot ne peut gérer que les rôles situés sous son rôle le plus haut.",
                        "Les salons non visibles par le bot peuvent manquer de la liste et des sauvegardes.",
                        "Les permissions des membres et les fonctionnalités du serveur peuvent limiter certaines actions."]}


class DiscordAPI:
    def __init__(self, token):
        self.client = httpx.Client(base_url="https://discord.com/api/v10", timeout=30,
                                  headers={"Authorization": "Bot " + token,
                                           "User-Agent": "DiscordBot (https://localhost, 2.0)"})

    def request(self, method, path, data=None, reason=None):
        headers = {"X-Audit-Log-Reason": quote(reason[:400], safe="")} if reason else {}
        for attempt in range(4):
            try:
                response = self.client.request(method, path, json=data, headers=headers)
            except httpx.TransportError as error:
                # Discord may have done the deed before the connection died. Don't retry.
                raise RuntimeError("Connexion interrompue ; état incertain. Lire le journal avant toute reprise.") from error
            if response.status_code == 429 and attempt < 3:
                delay = float(response.json().get("retry_after", 1))
                if delay > 15:
                    raise RuntimeError("Limite Discord atteinte ; attendre avant une nouvelle opération.")
                time.sleep(max(0.05, delay))
                continue
            if response.is_error:
                try:
                    error = response.json()
                except ValueError:
                    error = {}
                raise RuntimeError(f"Discord HTTP {response.status_code}, code {error.get('code', '?')}: "
                                   f"{error.get('message', 'Requête refusée')}")
            return response.json() if response.content else {"ok": True}


class Service:
    def __init__(self, root, guild, api):
        self.root, self.guild, self.api = Path(root), snowflake(guild), api
        self.data = self.root / "data"
        for folder in ("plans", "approvals", "backups", "runs"):
            (self.data / folder).mkdir(parents=True, exist_ok=True)

    def path(self, kind, item):
        if not re.fullmatch(r"[a-f0-9]{32}", item):
            raise ValueError("ID local invalide")
        return self.data / kind / (item + ".json")

    def save(self, kind, item, value):
        path = self.path(kind, item)
        temp = path.with_suffix("." + uuid.uuid4().hex + ".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, path)

    def read(self, kind, item):
        return json.loads(self.path(kind, item).read_text(encoding="utf-8"))

    @contextmanager
    def execution_lock(self):
        # One execution at a time; the OS releases the lock if we die.
        with (self.data / "execution.lock").open("a+b") as handle:
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                raise ValueError("Une autre exécution est en cours") from error
            try:
                yield
            finally:
                handle.seek(0)
                if os.name == "nt":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle, fcntl.LOCK_UN)

    def state(self):
        return {"serveur": self.api.request("GET", f"/guilds/{self.guild}"),
                "salons": self.api.request("GET", f"/guilds/{self.guild}/channels"),
                "roles": self.api.request("GET", f"/guilds/{self.guild}/roles")}

    def fingerprint(self, state):
        return digest({"serveur": select(state["serveur"], GUILD_FIELDS),
                       "salons": sorted([dict(id=c["id"], **select(c, CHANNEL_FIELDS)) for c in state["salons"]], key=lambda x: x["id"]),
                       "roles": sorted([dict(id=r["id"], position=r["position"], **select(r, ROLE_FIELDS)) for r in state["roles"]], key=lambda x: x["id"])})

    def channel(self, channel_id):
        c = self.api.request("GET", f"/channels/{snowflake(channel_id)}")
        if c.get("guild_id") != self.guild:
            raise ValueError("Salon hors du serveur configuré")
        return c

    def member(self, member_id):
        return self.api.request("GET", f"/guilds/{self.guild}/members/{snowflake(member_id)}")

    def message(self, channel_id, message_id):
        self.channel(channel_id)
        return self.api.request("GET", f"/channels/{channel_id}/messages/{snowflake(message_id)}")

    def validate(self, operations):
        if not isinstance(operations, list) or not 1 <= len(operations) <= 200:
            raise ValueError("Un plan contient de 1 à 200 actions")
        refs = set()
        for op in operations:
            if not isinstance(op, dict) or set(op) - {"action", "params", "ref"}:
                raise ValueError("Format action/params/ref attendu")
            action, p = op.get("action"), op.get("params")
            if action not in CATALOG or not isinstance(p, dict):
                raise ValueError("Action inconnue ou paramètres invalides")
            required, allowed = CATALOG[action]
            if required - set(p) or set(p) - allowed:
                raise ValueError(f"Paramètres invalides pour {action} ; autorisés : {sorted(allowed)}")

            def check_ids(value, key=""):
                if isinstance(value, dict):
                    for k, v in value.items():
                        check_ids(v, k)
                elif isinstance(value, list):
                    for v in value:
                        check_ids(v, key)
                elif key.endswith("_id") or key == "id":
                    if value is None:
                        return
                    if isinstance(value, str) and value.startswith("@"):
                        if value[1:] not in refs:
                            raise ValueError("Référence inconnue ou utilisée avant sa création : " + value)
                    else:
                        snowflake(value)
            check_ids(p)
            fields = {"modifier_salon": CHANNEL_FIELDS - {"type"}, "modifier_role": ROLE_FIELDS,
                      "modifier_serveur": GUILD_FIELDS, "modifier_membre": MEMBER_FIELDS,
                      "modifier_message": {"content", "embeds"}}
            if action in fields and (not isinstance(p["data"], dict) or not p["data"] or set(p["data"]) - fields[action]):
                raise ValueError("Champs de modification invalides")
            body = p.get("data", p)
            if "name" in body and (not isinstance(body["name"], str) or not 1 <= len(body["name"]) <= 100):
                raise ValueError("Nom invalide")
            if "permissions" in body and (not isinstance(body["permissions"], str) or not re.fullmatch(r"[0-9]+", body["permissions"])):
                raise ValueError("Masque de permissions décimal texte requis")
            for key, low, high in (("color", 0, 0xFFFFFF), ("position", 0, 10000), ("user_limit", 0, 99), ("rate_limit_per_user", 0, 21600)):
                if key in body and (type(body[key]) is not int or not low <= body[key] <= high):
                    raise ValueError("Valeur invalide : " + key)
            if "permission_overwrites" in body:
                if not isinstance(body["permission_overwrites"], list):
                    raise ValueError("Liste de permissions attendue")
                for overwrite in body["permission_overwrites"]:
                    if set(overwrite) != {"id", "type", "allow", "deny"} or overwrite["type"] not in (0, 1):
                        raise ValueError("Permission spécifique invalide")
                    if not str(overwrite["allow"]).isdecimal() or not str(overwrite["deny"]).isdecimal() or int(overwrite["allow"]) & int(overwrite["deny"]):
                        raise ValueError("Masques invalides ou contradictoires")
            if action.startswith("creer_") and not 1 <= len(p.get("name", "")) <= 100:
                raise ValueError("Le nom doit contenir 1 à 100 caractères")
            if action == "creer_salon" and p["type"] not in (0, 2, 4, 5, 13, 15):
                raise ValueError("Type de salon non pris en charge")
            if action == "permissions_salon":
                if p["type"] not in (0, 1) or int(p["allow"]) < 0 or int(p["deny"]) < 0 or int(p["allow"]) & int(p["deny"]):
                    raise ValueError("Permissions invalides ou contradictoires")
            if action in ("envoyer_message", "modifier_message"):
                body = p if action == "envoyer_message" else p["data"]
                if action == "envoyer_message" and not p.get("salon_id"):
                    raise ValueError("salon_id requis")
                if len(body.get("content", "")) > 2000:
                    raise ValueError("Message supérieur à 2000 caractères")
                embeds = body.get("embeds", [])
                if not isinstance(embeds, list) or len(embeds) > 10:
                    raise ValueError("Maximum 10 embeds")
                total = 0
                for e in embeds:
                    if not isinstance(e, dict) or set(e) - {"title", "description", "color", "url", "fields", "footer", "author", "image", "thumbnail", "timestamp"}:
                        raise ValueError("Embed invalide")
                    if len(e.get("title", "")) > 256 or len(e.get("description", "")) > 4096 or len(e.get("fields", [])) > 25:
                        raise ValueError("Embed trop long")
                    for f in e.get("fields", []):
                        if not f.get("name") or not f.get("value") or len(f["name"]) > 256 or len(f["value"]) > 1024:
                            raise ValueError("Champ embed invalide")
                    total += len(e.get("title", "")) + len(e.get("description", ""))
                    total += sum(len(f["name"]) + len(f["value"]) for f in e.get("fields", []))
                    total += len(e.get("footer", {}).get("text", "")) + len(e.get("author", {}).get("name", ""))
                if total > 6000:
                    raise ValueError("Les embeds dépassent 6000 caractères")
                if action == "envoyer_message" and not body.get("content") and not embeds:
                    raise ValueError("Message vide")
            if "ref" in op:
                if action not in ("creer_salon", "creer_role", "envoyer_message") or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", op["ref"]) or op["ref"] in refs:
                    raise ValueError("Référence invalide ou dupliquée")
                refs.add(op["ref"])

    def context(self, operations, state):
        context = {"membres": {}, "messages": {}, "salons_supprimes": {}}
        roles = {r["id"]: r for r in state["roles"]}
        for op in operations:
            p, action = op["params"], op["action"]
            # Check the guild again: an ID alone isn't an invitation.
            for key in ("salon_id", "parent_id"):
                if p.get(key) and not p[key].startswith("@"):
                    channel = self.channel(p[key])
                    if key == "salon_id" and action == "supprimer_salon":
                        # A new message after approval changes what the deletion would destroy.
                        context["salons_supprimes"][p[key]] = select(channel, {"name", "type", "last_message_id"})
            if p.get("role_id") and not p["role_id"].startswith("@"):
                role = roles.get(p["role_id"])
                if role is None:
                    raise ValueError("Rôle hors du serveur configuré")
                if role.get("managed") or (p["role_id"] == self.guild and action != "modifier_role"):
                    raise ValueError("Rôle protégé")
            if p.get("membre_id"):
                context["membres"][p["membre_id"]] = self.member(p["membre_id"])
            if p.get("message_id") and not p["message_id"].startswith("@"):
                context["messages"][p["message_id"]] = self.message(p["salon_id"], p["message_id"])
        return context

    def context_fingerprint(self, ctx):
        return digest({"membres": {k: select(v, {"roles", "nick", "communication_disabled_until"}) for k, v in ctx["membres"].items()},
                       "messages": {k: select(v, {"content", "embeds", "attachments", "pinned"}) for k, v in ctx["messages"].items()},
                       "salons_supprimes": ctx.get("salons_supprimes", {})})

    def preview(self, title, operations):
        operations = copy.deepcopy(operations)
        self.validate(operations)
        state = self.state()
        ctx = self.context(operations, state)
        plan_id = uuid.uuid4().hex
        payload = {"schema": SCHEMA, "id": plan_id, "guild_id": self.guild,
                   "serveur": state["serveur"]["name"], "titre": title[:200], "created": time.time(),
                   "operations": operations, "fingerprint": self.fingerprint(state),
                   "context_fingerprint": self.context_fingerprint(ctx), "limites": LIMITS,
                   "avant": {"serveur": select(state["serveur"], GUILD_FIELDS),
                             "salons": [dict(id=c["id"], **select(c, CHANNEL_FIELDS)) for c in state["salons"]],
                             "roles": [dict(id=r["id"], **select(r, ROLE_FIELDS)) for r in state["roles"]],
                             "salons_supprimes": ctx["salons_supprimes"],
                             "membres_cibles": {k: select(v, {"roles", "nick", "communication_disabled_until"}) for k, v in ctx["membres"].items()},
                             "messages_cibles": {k: select(v, {"content", "embeds"}) for k, v in ctx["messages"].items()}}}
        plan = {"payload": payload, "sha256": digest(payload), "status": "pending"}
        self.save("plans", plan_id, plan)
        return {"mode": "APERCU", "plan_id": plan_id, "sha256": plan["sha256"],
                "titre": title, "actions": operations, "avant": payload["avant"], "limites": LIMITS,
                "suite": "Montrer ce plan à l'utilisateur. Après son accord, ouvrir_approbation. Seul le bouton local Approuver autorise executer_plan."}

    def plan(self, plan_id):
        plan = self.read("plans", plan_id)
        if digest(plan["payload"]) != plan["sha256"] or plan["payload"]["guild_id"] != self.guild:
            raise ValueError("Plan altéré ou serveur différent")
        return plan

    def backup(self, label="Sauvegarde manuelle", state=None, context=None):
        item = uuid.uuid4().hex
        self.save("backups", item, {"schema": SCHEMA, "id": item, "guild_id": self.guild,
                                   "created": time.time(), "label": label, "state": state or self.state(),
                                   "context": context or {"membres": {}, "messages": {}}})
        return {"backup_id": item, "limites": LIMITS}

    def resolve(self, data, refs, key=""):
        if isinstance(data, dict):
            return {k: self.resolve(v, refs, k) for k, v in data.items()}
        if isinstance(data, list):
            return [self.resolve(v, refs, key) for v in data]
        if (key.endswith("_id") or key == "id") and isinstance(data, str) and re.fullmatch(r"@[A-Za-z][A-Za-z0-9_]{0,39}", data) and data[1:] in refs:
            return refs[data[1:]]
        return data

    def execute_operation(self, op, reason):
        action, params = op["action"], op["params"]
        guild_path = f"/guilds/{self.guild}"
        if "salon_id" in params:
            self.channel(params["salon_id"])
        if action == "creer_salon":
            if params.get("parent_id"):
                if self.channel(params["parent_id"])["type"] != 4:
                    raise ValueError("parent_id doit désigner une catégorie")
            method, path, body = "POST", guild_path + "/channels", params
        elif action == "modifier_salon":
            if params["data"].get("parent_id"):
                if self.channel(params["data"]["parent_id"])["type"] != 4:
                    raise ValueError("Catégorie invalide")
            method, path, body = "PATCH", "/channels/" + params["salon_id"], params["data"]
        elif action == "supprimer_salon":
            method, path, body = "DELETE", "/channels/" + params["salon_id"], None
        elif action == "creer_role":
            method, path, body = "POST", guild_path + "/roles", params
        elif action in ("modifier_role", "supprimer_role", "position_role"):
            roles = self.api.request("GET", guild_path + "/roles")
            role = next((r for r in roles if r["id"] == params["role_id"]), None)
            if role is None or role.get("managed") or (action != "modifier_role" and role["id"] == self.guild):
                raise ValueError("Rôle inexistant ou protégé")
            if action == "position_role":
                method, path, body = "PATCH", guild_path + "/roles", [{"id": params["role_id"], "position": params["position"]}]
            else:
                method, path, body = ("PATCH" if action == "modifier_role" else "DELETE"), guild_path + "/roles/" + params["role_id"], params.get("data")
        elif action in ("permissions_salon", "retirer_permissions"):
            method = "PUT" if action == "permissions_salon" else "DELETE"
            path = f"/channels/{params['salon_id']}/permissions/{params['cible_id']}"
            body = select(params, {"type", "allow", "deny"}) if method == "PUT" else None
        elif action in ("ajouter_role", "retirer_role"):
            method = "PUT" if action == "ajouter_role" else "DELETE"
            path, body = f"{guild_path}/members/{params['membre_id']}/roles/{params['role_id']}", None
        elif action == "modifier_membre":
            method, path, body = "PATCH", guild_path + "/members/" + params["membre_id"], params["data"]
        elif action in ("envoyer_message", "modifier_message", "supprimer_message"):
            path = "/channels/" + params["salon_id"] + "/messages"
            if action != "envoyer_message":
                path += "/" + params["message_id"]
            method = {"envoyer_message": "POST", "modifier_message": "PATCH", "supprimer_message": "DELETE"}[action]
            body = select(params, {"content", "embeds"}) if action == "envoyer_message" else copy.deepcopy(params.get("data"))
            if body is not None:
                body["allowed_mentions"] = {"parse": []}
        elif action == "modifier_serveur":
            method, path, body = "PATCH", guild_path, params["data"]
        else:
            raise ValueError("Action non prise en charge")
        return self.api.request(method, path, body, reason)

    def execute(self, plan_id):
        with self.execution_lock():
            plan = self.plan(plan_id)
            if plan["status"] != "pending":
                raise ValueError("Plan déjà consommé ou annulé")
            if not self.path("approvals", plan_id).exists():
                raise ValueError("Approbation humaine locale requise. Aucune modification effectuée.")
            approval = self.read("approvals", plan_id)
            if approval.get("sha256") != plan["sha256"] or approval.get("decision") != "approved" or not 0 <= time.time() - approval["at"] < 600:
                raise ValueError("Approbation absente, refusée, expirée ou ne correspondant plus au plan")
            payload = plan["payload"]
            self.validate(payload["operations"])
            state = self.state()
            ctx = self.context(payload["operations"], state)
            if self.fingerprint(state) != payload["fingerprint"] or self.context_fingerprint(ctx) != payload["context_fingerprint"]:
                raise ValueError("Le serveur ou une cible a changé depuis l'aperçu. Créer un nouveau plan.")
            # No backup, no massacre.
            backup = self.backup(payload["titre"], state, ctx)
            run_id = uuid.uuid4().hex
            run = {"id": run_id, "guild_id": self.guild, "plan_id": plan_id, "backup_id": backup["backup_id"],
                   "created": time.time(), "status": "running", "steps": [], "refs": {}}
            self.save("runs", run_id, run)
            # Consume before the first request, including if Discord ghosts us.
            plan["status"] = "consumed"
            self.save("plans", plan_id, plan)
            for operation in payload["operations"]:
                resolved = copy.deepcopy(operation)
                resolved["params"] = self.resolve(operation["params"], run["refs"])
                step = {"operation": resolved, "status": "started"}
                run["steps"].append(step)
                self.save("runs", run_id, run)
                try:
                    result = self.execute_operation(resolved, f"Veilleur plan {plan_id} : {payload['titre']}")
                    step.update(status="done", result=result)
                    if "ref" in operation:
                        run["refs"][operation["ref"]] = result["id"]
                except Exception as error:
                    step.update(status="failed_or_uncertain", error=str(error))
                    run["status"] = "partial_failure"
                    self.save("runs", run_id, run)
                    return {"run_id": run_id, "status": run["status"], "backup_id": run["backup_id"], "error": str(error),
                            "suite": "Consulter le journal ; préparer un retour arrière. Ne pas rejouer le plan."}
                self.save("runs", run_id, run)
            run["status"] = "completed"
            self.save("runs", run_id, run)
            return {"run_id": run_id, "status": "completed", "backup_id": run["backup_id"], "resultats": run["refs"], "actions": len(run["steps"])}

    def history(self, kind, limit=20):
        if kind not in ("plans", "backups", "runs"):
            raise ValueError("Type attendu : plans, backups ou runs")
        result = []
        for path in sorted((self.data / kind).glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:max(1, min(100, limit))]:
            item = json.loads(path.read_text(encoding="utf-8"))
            p = item.get("payload", item)
            result.append({"id": p["id"], "titre": p.get("titre", p.get("label", "")), "created": p.get("created"), "status": item.get("status"), "backup_id": item.get("backup_id")})
        return result

    def restoration(self, backup_id, run_id=None):
        backup = self.read("backups", backup_id)
        if backup["guild_id"] != self.guild:
            raise ValueError("Sauvegarde d'un autre serveur")
        old, now = backup["state"], self.state()
        operations, role_map, channel_map = [], {}, {}
        current_roles = {r["id"]: r for r in now["roles"]}
        current_channels = {c["id"]: c for c in now["salons"]}
        def op(action, params, ref=None):
            item = {"action": action, "params": params}
            if ref:
                item["ref"] = ref
            operations.append(item)
        for role in old["roles"]:
            rid = role["id"]
            if role.get("managed"):
                if rid in current_roles:
                    role_map[rid] = rid
                continue
            if rid in current_roles:
                role_map[rid] = rid
                if select(role, ROLE_FIELDS) != select(current_roles[rid], ROLE_FIELDS):
                    op("modifier_role", {"role_id": rid, "data": select(role, ROLE_FIELDS)})
            else:
                ref = "role" + rid
                role_map[rid] = "@" + ref
                op("creer_role", select(role, ROLE_FIELDS), ref)
        # Bring the parents back before sending their children home.
        for channel in sorted(old["salons"], key=lambda c: c["type"] != 4):
            cid = channel["id"]
            if cid in current_channels:
                channel_map[cid] = cid
            else:
                ref = "salon" + cid
                channel_map[cid] = "@" + ref
                op("creer_salon", {"name": channel["name"], "type": channel["type"]}, ref)
        for channel in old["salons"]:
            cid = channel["id"]
            data = select(channel, CHANNEL_FIELDS - {"type"})
            if data.get("parent_id"):
                data["parent_id"] = channel_map.get(data["parent_id"], data["parent_id"])
            for overwrite in data.get("permission_overwrites", []):
                if overwrite["type"] == 0:
                    if overwrite["id"] not in role_map:
                        raise ValueError("Un rôle géré disparu empêche la restauration des permissions")
                    overwrite["id"] = role_map[overwrite["id"]]
            if cid not in current_channels or data != select(current_channels[cid], CHANNEL_FIELDS - {"type"}):
                op("modifier_salon", {"salon_id": channel_map[cid], "data": data})
        for role in sorted(old["roles"], key=lambda r: r["position"]):
            rid = role["id"]
            if not role.get("managed") and rid != self.guild and (rid not in current_roles or current_roles[rid]["position"] != role["position"]):
                op("position_role", {"role_id": role_map[rid], "position": role["position"]})
        guild_data = select(old["serveur"], GUILD_FIELDS)
        for key in ("afk_channel_id", "system_channel_id"):
            if guild_data.get(key):
                guild_data[key] = channel_map.get(guild_data[key], guild_data[key])
        if guild_data != select(now["serveur"], GUILD_FIELDS):
            op("modifier_serveur", {"data": guild_data})
        for mid, member in backup["context"]["membres"].items():
            current = self.member(mid)
            desired_roles = {role_map.get(r, r) for r in member["roles"]}
            for rid in sorted(desired_roles - set(current["roles"])):
                op("ajouter_role", {"membre_id": mid, "role_id": rid})
            for rid in sorted(set(current["roles"]) - desired_roles):
                if rid in current_roles and not current_roles[rid].get("managed"):
                    op("retirer_role", {"membre_id": mid, "role_id": rid})
            if select(member, MEMBER_FIELDS) != select(current, MEMBER_FIELDS):
                data = select(member, MEMBER_FIELDS)
                timeout = data.get("communication_disabled_until")
                if timeout:
                    from datetime import datetime, timezone
                    if datetime.fromisoformat(timeout).astimezone(timezone.utc) < datetime.now(timezone.utc):
                        data["communication_disabled_until"] = None
                op("modifier_membre", {"membre_id": mid, "data": data})
        if run_id:
            run = self.read("runs", run_id)
            if run["backup_id"] != backup_id or run["status"] == "running" or any(s["status"] != "done" for s in run["steps"]):
                raise ValueError("Exécution interrompue ou incertaine : examiner le journal et restaurer la sauvegarde explicitement")
            for step in reversed(run["steps"]):
                a, p, result = step["operation"]["action"], step["operation"]["params"], step["result"]
                if a == "envoyer_message":
                    if p["salon_id"] in current_channels:
                        op("supprimer_message", {"salon_id": p["salon_id"], "message_id": result["id"]})
                elif a == "creer_salon" and result["id"] in current_channels:
                    op("supprimer_salon", {"salon_id": result["id"]})
                elif a == "creer_role" and result["id"] in current_roles:
                    op("supprimer_role", {"role_id": result["id"]})
                elif a == "modifier_message":
                    original = copy.deepcopy(backup["context"]["messages"][p["message_id"]])
                    for embed in original.get("embeds", []):
                        for key in list(embed):
                            if key not in {"title", "description", "color", "url", "fields", "footer", "author", "image", "thumbnail", "timestamp"}:
                                del embed[key]
                    op("modifier_message", {"salon_id": p["salon_id"], "message_id": p["message_id"],
                                            "data": select(original, {"content", "embeds"})})
        if not operations:
            return {"mode": "APERCU", "actions": [], "info": "La structure correspond déjà à la sauvegarde"}
        return self.preview("Restauration " + backup_id, operations)
