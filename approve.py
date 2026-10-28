"""Local human approval UI. No Discord token, no Discord API calls."""
import json
import sys
import time
import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
from pathlib import Path

from core import digest


ACTION_LABELS = {
    "creer_salon": "Créer un salon", "modifier_salon": "Modifier un salon",
    "supprimer_salon": "Supprimer un salon", "creer_role": "Créer un rôle",
    "modifier_role": "Modifier un rôle", "supprimer_role": "Supprimer un rôle",
    "position_role": "Déplacer un rôle", "permissions_salon": "Modifier les permissions du salon",
    "retirer_permissions": "Retirer une dérogation de permissions", "ajouter_role": "Ajouter un rôle à un membre",
    "retirer_role": "Retirer un rôle à un membre", "modifier_membre": "Modifier un membre",
    "envoyer_message": "Envoyer un message", "modifier_message": "Modifier un message",
    "supprimer_message": "Supprimer un message", "modifier_serveur": "Modifier le serveur",
}
FIELD_LABELS = {"name": "Nom", "topic": "Sujet", "parent_id": "Catégorie", "permissions": "Permissions",
                "position": "Position", "color": "Couleur", "nsfw": "Contenu adulte", "hoist": "Affichage séparé",
                "mentionable": "Mentionnable", "content": "Message", "embeds": "Embeds",
                "permission_overwrites": "Dérogations de permissions", "nick": "Surnom",
                "communication_disabled_until": "Timeout jusqu'au"}


def format_plan(payload):
    """Describe the actions without hiding the underlying plan."""
    before = payload.get("avant", {})
    channels = {c["id"]: c for c in before.get("salons", [])}
    roles = {r["id"]: r for r in before.get("roles", [])}
    refs = {}

    def target(value):
        if not value:
            return "aucune"
        if value in refs:
            return refs[value] + " (à créer)"
        item = channels.get(value) or roles.get(value)
        return f"{item['name']} ({value})" if item else str(value)

    lines = []
    for index, operation in enumerate(payload["operations"], 1):
        action, params = operation["action"], operation["params"]
        lines.append(f"{index}. {ACTION_LABELS.get(action, action)}")
        for key, label in (("salon_id", "Salon"), ("role_id", "Rôle"), ("membre_id", "Membre"),
                           ("cible_id", "Cible"), ("message_id", "Message"), ("parent_id", "Catégorie")):
            if key in params:
                lines.append(f"   {label} : {target(params[key])}")
        if "name" in params:
            lines.append(f"   Nom : {params['name']}")
        if action == "creer_salon":
            labels = {0: "texte", 2: "vocal", 4: "catégorie", 5: "annonces", 13: "scène", 15: "forum"}
            lines.append(f"   Type : {labels.get(params['type'], params['type'])}")
        if action == "supprimer_salon":
            details = before.get("salons_supprimes", {}).get(params.get("salon_id"), {})
            if details.get("type") != 4:
                lines.append("   ATTENTION : les messages de ce salon seront supprimés avec lui.")
                lines.append("   Des messages peuvent être présents, même si le dernier ID n'est pas disponible.")
            else:
                lines.append("   Vérifie aussi les salons rangés dans cette catégorie.")
        if action == "supprimer_role":
            lines.append("   ATTENTION : les attributions de ce rôle ne sont pas toutes sauvegardées.")
        if action == "supprimer_message":
            lines.append("   ATTENTION : le message supprimé ne peut pas être restauré à l'identique.")
        current = channels.get(params.get("salon_id"), roles.get(params.get("role_id"), {}))
        if action == "modifier_serveur":
            current = before.get("serveur", {})
        if action == "modifier_membre":
            current = before.get("membres_cibles", {}).get(params.get("membre_id"), {})
        if action == "modifier_message":
            current = before.get("messages_cibles", {}).get(params.get("message_id"), {})
        for key, value in params.get("data", {}).items():
            label = FIELD_LABELS.get(key, key)
            old = json.dumps(current.get(key), ensure_ascii=False)
            new = json.dumps(value, ensure_ascii=False)
            lines.append(f"   {label} : {old} → {new}")
        if action == "permissions_salon":
            lines.append(f"   Type de cible : {'rôle' if params['type'] == 0 else 'membre'}")
            previous = next((o for o in current.get("permission_overwrites", [])
                             if o.get("id") == params["cible_id"] and o.get("type") == params["type"]), None)
            if previous:
                lines.append(f"   Avant : autoriser {previous['allow']}, refuser {previous['deny']}")
            else:
                lines.append("   Avant : aucune dérogation enregistrée dans l'aperçu")
            lines.append(f"   Masques : autoriser {params['allow']}, refuser {params['deny']} (remplace la dérogation)")
        if action == "envoyer_message":
            if params.get("content"):
                lines.append("   Texte : " + params["content"])
            if params.get("embeds"):
                lines.append("   Embeds : " + json.dumps(params["embeds"], ensure_ascii=False))
        if operation.get("ref"):
            refs["@" + operation["ref"]] = params.get("name", action)
        lines.append("")
    return "\n".join(lines)


def main():
    root_path = Path(__file__).resolve().parent
    plan_id = sys.argv[1]
    from core import Service
    # Service only requires a guild ID for local plan loading.
    config = json.loads((root_path / "config.json").read_text(encoding="utf-8-sig"))
    service = Service(root_path, str(config["guild_id"]), None)
    plan = service.plan(plan_id)
    if plan["status"] != "pending":
        raise ValueError("Plan déjà consommé ou annulé")
    root = tk.Tk()
    root.title("Veilleur — Validation humaine Discord")
    root.geometry("960x760")
    root.minsize(700, 500)
    payload = plan["payload"]
    tk.Label(root, text=f"{payload['serveur']} — {payload['titre']}", font=("Segoe UI", 14, "bold"), wraplength=900).pack(padx=16, pady=12)
    tk.Label(root, text=f"{len(payload['operations'])} actions • Plan {plan_id}\nL'approbation autorise uniquement ce plan pendant 10 minutes.", wraplength=900).pack()
    text = ScrolledText(root, wrap="word", font=("Consolas", 10))
    text.pack(fill="both", expand=True, padx=16, pady=12)
    summary = "ACTIONS À EXÉCUTER\n\n" + format_plan(payload)
    text.insert("1.0", summary + "\n\nLIMITES\n\n" + "\n".join(payload["limites"]) +
                "\n\nPLAN EXACT ET ÉTAT AVANT MODIFICATION\n\n" + json.dumps(payload, ensure_ascii=False, indent=2))
    text.configure(state="disabled")
    checked = tk.BooleanVar(value=False)
    tk.Checkbutton(root, text="J'ai lu les actions et leurs limites, et j'approuve leur exécution sur ce serveur.", variable=checked).pack(padx=12)
    button_row = tk.Frame(root)
    button_row.pack(pady=16)

    def decide(decision):
        current = service.plan(plan_id)
        if current["sha256"] != plan["sha256"] or current["status"] != "pending" or digest(payload) != plan["sha256"]:
            messagebox.showerror("Veilleur", "Le plan a changé. Fermez cette fenêtre et demandez un nouvel aperçu.")
            return
        if decision == "approved" and not checked.get():
            messagebox.showinfo("Veilleur", "Lisez le plan puis cochez la case pour approuver.")
            return
        service.save("approvals", plan_id, {"sha256": plan["sha256"], "decision": decision, "at": time.time()})
        root.destroy()

    tk.Button(button_row, text="Refuser", command=lambda: decide("rejected"), width=18).pack(side="left", padx=12)
    tk.Button(button_row, text="Approuver ce plan", command=lambda: decide("approved"), width=22).pack(side="left", padx=12)
    root.mainloop()


if __name__ == "__main__":
    main()
