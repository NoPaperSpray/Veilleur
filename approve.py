"""Local human approval UI. No Discord token, no Discord API calls."""
import json
import sys
import time
import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
from pathlib import Path

from core import digest


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
    summary = "ACTIONS À EXÉCUTER\n\n" + "\n".join(
        f"{i}. {op['action']} : {json.dumps(op['params'], ensure_ascii=False)}"
        for i, op in enumerate(payload["operations"], 1))
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
