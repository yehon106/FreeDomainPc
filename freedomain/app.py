from __future__ import annotations
import json
import os
import re
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
from .providers import Cloudflare, DeSEC, DuckDNS, ProviderError
from .free_domains import FreeDomainsWindow
import keyring

APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "FreeDomainServer"
CONFIG = APP_DIR / "config.json"
RECORD_TYPES = ["A", "AAAA", "CNAME", "TXT", "MX", "NS", "SRV", "CAA", "HTTPS", "SVCB", "TLSA", "SSHFP", "NAPTR"]
HELP = """FreeDomain Server

This app manages DNS records for domains you already control through supported providers.
It does not create public top-level domains or register arbitrary .com/.net/.dev names.

Supported integrations:
• Cloudflare: zones and DNS records through an API token.
• deSEC: zones and DNS RRsets through an API token.
• DuckDNS: update a DuckDNS hostname's IP only (not a general DNS editor).

For Vercel, add your domain to your Vercel project first, then use the DNS instructions Vercel displays.
The app can create the corresponding DNS records in a connected Cloudflare/deSEC zone.
"""

def load_config():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG.exists():
        try:
            return json.loads(CONFIG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"providers": {}}

def save_config(data):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(data, indent=2), encoding="utf-8")

def valid_name(name):
    name = name.strip()
    if not name:
        return False
    if name == "@":
        return True
    if len(name) > 253:
        return False
    labels = name.rstrip(".").split(".")
    return all(label == "*" or re.fullmatch(r"[A-Za-z0-9_-]{1,63}", label) for label in labels)

class App:
    def __init__(self, root):
        self.root = root
        root.title("FreeDomain Server")
        root.geometry("1040x680")
        root.minsize(900, 580)
        self.cfg = load_config()
        self.zones = []
        self.active_provider = tk.StringVar(value="Cloudflare")
        self.active_zone = tk.StringVar()
        self.status = tk.StringVar(value="Connect a DNS provider to get started.")
        self._style()
        self._ui()
        self.refresh_providers()

    def _style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Sub.TLabel", font=("Segoe UI", 10))
        style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=8)
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _ui(self):
        shell = ttk.Frame(self.root, padding=18)
        shell.pack(fill="both", expand=True)
        top = ttk.Frame(shell)
        top.pack(fill="x")
        ttk.Label(top, text="FreeDomain Server", style="Title.TLabel").pack(side="left")
        ttk.Label(top, text="DNS management made simple", style="Sub.TLabel").pack(side="left", padx=14, pady=(10, 0))
        ttk.Button(top, text="Help", command=lambda: messagebox.showinfo("About FreeDomain Server", HELP)).pack(side="right")
        ttk.Separator(shell).pack(fill="x", pady=14)
        provider_box = ttk.LabelFrame(shell, text="1. DNS provider", padding=12)
        provider_box.pack(fill="x")
        ttk.Label(provider_box, text="Provider").grid(row=0, column=0, sticky="w")
        self.provider_combo = ttk.Combobox(provider_box, textvariable=self.active_provider,
            values=["Cloudflare", "deSEC", "DuckDNS"], state="readonly", width=18)
        self.provider_combo.grid(row=0, column=1, padx=8, sticky="w")
        ttk.Button(provider_box, text="Connect / Configure", command=self.configure_provider).grid(row=0, column=2, padx=4)
        ttk.Button(provider_box, text="Refresh domains", command=self.refresh_zones).grid(row=0, column=3, padx=4)
        self.provider_state = ttk.Label(provider_box, text="Not connected")
        self.provider_state.grid(row=0, column=4, padx=12, sticky="w")
        domain_box = ttk.LabelFrame(shell, text="2. Choose a domain", padding=12)
        domain_box.pack(fill="x", pady=12)
        ttk.Label(domain_box, text="Domain / zone").pack(side="left")
        self.zone_combo = ttk.Combobox(domain_box, textvariable=self.active_zone, state="readonly", width=38)
        self.zone_combo.pack(side="left", padx=10)
        self.zone_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_records())
        ttk.Button(domain_box, text="Load DNS records", command=self.refresh_records).pack(side="left")
        rec_box = ttk.LabelFrame(shell, text="3. DNS records", padding=12)
        rec_box.pack(fill="both", expand=True)
        cols = ("type", "name", "content", "ttl", "proxied")
        self.tree = ttk.Treeview(rec_box, columns=cols, show="headings", selectmode="browse")
        for col, width in [("type", 90), ("name", 240), ("content", 390), ("ttl", 90), ("proxied", 90)]:
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(rec_box, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        actions = ttk.Frame(shell)
        actions.pack(fill="x", pady=12)
        ttk.Button(actions, text="＋ Add record", style="Action.TButton", command=self.add_record).pack(side="left")
        ttk.Button(actions, text="Delete selected", command=self.delete_record).pack(side="left", padx=8)
        ttk.Button(actions, text="Vercel quick setup", command=self.vercel_setup).pack(side="left", padx=8)
        ttk.Button(actions, text="Get a Free Domain", style="Action.TButton", command=lambda: FreeDomainsWindow(self.root, self)).pack(side="left", padx=8)
        ttk.Label(actions, textvariable=self.status).pack(side="right")
        ttk.Label(shell, text="Your websites can be hosted anywhere. This app manages DNS; it does not host website files.",
            foreground="#666").pack(anchor="w")

    def provider_client(self, name=None):
        name = name or self.active_provider.get()
        item = self.cfg["providers"].get(name)
        token = (keyring.get_password("FreeDomainServer", item.get("credential_key")) if item and item.get("credential_key") else (item.get("token") if item else None))
        if not token:
            raise ProviderError(f"{name} is not configured yet. Click Connect / Configure.")
        if name == "Cloudflare": return Cloudflare(token)
        if name == "deSEC": return DeSEC(token)
        if name == "DuckDNS": return DuckDNS(token)
        raise ProviderError("Unknown provider.")

    def refresh_providers(self):
        p = self.active_provider.get()
        item = self.cfg["providers"].get(p, {})
        configured = bool(item.get("token") or (item.get("credential_key") and keyring.get_password("FreeDomainServer", item["credential_key"])))
        self.provider_state.config(text="Configured" if configured else "Not connected")

    def configure_provider(self):
        name = self.active_provider.get()
        instructions = {
            "Cloudflare": "Create an API token with Zone:Read and DNS:Edit permissions. Limit it to the zones you want this app to manage.",
            "deSEC": "Create an API token in your deSEC account.",
            "DuckDNS": "Copy your DuckDNS token from your DuckDNS account. DuckDNS only supports updating the IP for a hostname."
        }[name]
        messagebox.showinfo(f"Connect {name}", instructions)
        token = simpledialog.askstring(f"{name} API token", "Paste your API token:", show="*")
        if not token: return
        self.cfg["providers"][name] = {"token": token.strip()}
        save_config(self.cfg)
        self.refresh_providers()
        self.status.set(f"{name} credentials saved locally.")
        if name != "DuckDNS": self.refresh_zones()

    def refresh_zones(self):
        try:
            client = self.provider_client()
            if self.active_provider.get() == "DuckDNS":
                messagebox.showinfo("DuckDNS", "DuckDNS does not provide a zone-list or full DNS record API. Use its IP update feature from the provider settings.")
                return
            self.zones = client.list_zones()
            names = [z["name"] for z in self.zones]
            self.zone_combo["values"] = names
            if names:
                if self.active_zone.get() not in names: self.active_zone.set(names[0])
                self.refresh_records()
                self.status.set(f"Loaded {len(names)} domain(s).")
            else:
                self.active_zone.set("")
                self.tree.delete(*self.tree.get_children())
                self.status.set("No domains found in this provider account.")
        except Exception as e:
            messagebox.showerror("Could not load domains", str(e))
            self.status.set("Provider connection failed.")

    def selected_zone(self):
        name = self.active_zone.get()
        for z in self.zones:
            if z["name"] == name: return z
        raise ProviderError("Choose a domain first.")

    def refresh_records(self):
        if not self.active_zone.get(): return
        try:
            zone = self.selected_zone()
            records = self.provider_client().list_records(zone["id"])
            self.tree.delete(*self.tree.get_children())
            for r in records:
                self.tree.insert("", "end", iid=str(r.get("id", "")) or None,
                    values=(r.get("type", ""), r.get("name", "@"), r.get("content", ""),
                            r.get("ttl", ""), r.get("proxied", False)))
            self.status.set(f"{len(records)} record(s) loaded.")
        except Exception as e:
            messagebox.showerror("Could not load DNS records", str(e))

    def add_record(self):
        if self.active_provider.get() == "DuckDNS":
            messagebox.showinfo("Limited provider support", "DuckDNS only updates its hostname's IP. Choose Cloudflare or deSEC for full DNS record editing.")
            return
        try:
            zone = self.selected_zone()
            client = self.provider_client()
        except Exception as e:
            messagebox.showerror("Choose a domain", str(e))
            return
        win = tk.Toplevel(self.root)
        win.title("Add DNS record")
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)
        frame = ttk.Frame(win, padding=18)
        frame.pack(fill="both", expand=True)
        rtype, name, content, ttl = tk.StringVar(value="TXT"), tk.StringVar(value="@"), tk.StringVar(), tk.StringVar(value="3600")
        proxied = tk.BooleanVar(value=False)
        fields = [
            ("Record type", ttk.Combobox(frame, textvariable=rtype, values=RECORD_TYPES, state="readonly", width=32)),
            ("Name (use @ for root; underscores are allowed)", ttk.Entry(frame, textvariable=name, width=36)),
            ("Value / target", ttk.Entry(frame, textvariable=content, width=36)),
            ("TTL (seconds)", ttk.Entry(frame, textvariable=ttl, width=36)),
        ]
        for i, (label, widget) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=i*2, column=0, sticky="w", pady=(7, 2))
            widget.grid(row=i*2+1, column=0, sticky="ew")
        if self.active_provider.get() == "Cloudflare":
            ttk.Checkbutton(frame, text="Proxy through Cloudflare (HTTP(S) records only)", variable=proxied).grid(row=8, column=0, sticky="w", pady=8)
        def save():
            n, c = name.get().strip(), content.get().strip()
            if not valid_name(n):
                messagebox.showerror("Invalid name", "Use a valid DNS name. Underscores are supported, for example _acme-challenge.")
                return
            if not c:
                messagebox.showerror("Missing value", "Enter a record value or target.")
                return
            try:
                ttl_value = int(ttl.get())
                if ttl_value < 60 or ttl_value > 86400: raise ValueError
            except ValueError:
                messagebox.showerror("Invalid TTL", "Enter a TTL from 60 to 86400 seconds.")
                return
            full_name = zone["name"] if n == "@" else (n if n == zone["name"] or n.endswith("." + zone["name"]) else f"{n}.{zone['name']}")
            payload = {"type": rtype.get(), "name": full_name, "content": c, "ttl": ttl_value}
            if self.active_provider.get() == "Cloudflare":
                payload["proxied"] = bool(proxied.get()) and rtype.get() in ("A", "AAAA", "CNAME")
            try:
                _, result = client.upsert_record(zone["id"], payload)
                win.destroy()
                self.refresh_records()
                self.status.set(f"Record {result}.")
            except Exception as e:
                messagebox.showerror("Could not save record", str(e))
        ttk.Button(frame, text="Save record", style="Action.TButton", command=save).grid(row=9, column=0, sticky="ew", pady=(14, 0))

    def delete_record(self):
        if self.active_provider.get() == "DuckDNS": return
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select a record", "Choose a DNS record first.")
            return
        if not messagebox.askyesno("Delete DNS record", "Delete the selected DNS record?"): return
        try:
            zone = self.selected_zone()
            self.provider_client().delete_record(zone["id"], selected[0])
            self.refresh_records()
            self.status.set("Record deleted.")
        except Exception as e:
            messagebox.showerror("Could not delete record", str(e))

    def vercel_setup(self):
        if self.active_provider.get() not in ("Cloudflare", "deSEC"):
            messagebox.showinfo("Choose a DNS provider", "Select Cloudflare or deSEC to create DNS records.")
            return
        try: zone = self.selected_zone()
        except Exception as e:
            messagebox.showerror("Choose a domain", str(e))
            return
        msg = ("First add the domain in your Vercel project and check the exact DNS instructions Vercel gives you.\n\n"
               "Typical configuration for a Vercel project is:\n"
               "• Root (@): A → 76.76.21.21\n"
               "• www: CNAME → cname.vercel-dns.com\n\n"
               "Vercel may provide different values for your project. Use its displayed values if they differ.")
        if not messagebox.askyesno("Vercel DNS setup", msg + "\n\nCreate these typical records now?"): return
        try:
            client = self.provider_client()
            if self.active_provider.get() == "Cloudflare":
                client.upsert_record(zone["id"], {"type":"A","name":zone["name"],"content":"76.76.21.21","ttl":1,"proxied":False})
                client.upsert_record(zone["id"], {"type":"CNAME","name":"www."+zone["name"],"content":"cname.vercel-dns.com","ttl":1,"proxied":False})
            else:
                client.upsert_record(zone["id"], {"type":"A","name":"@","content":"76.76.21.21","ttl":3600})
                client.upsert_record(zone["id"], {"type":"CNAME","name":"www","content":"cname.vercel-dns.com","ttl":3600})
            self.refresh_records()
            messagebox.showinfo("Records added", "Typical Vercel DNS records were added. Return to Vercel and verify the domain. If Vercel displayed different targets, edit these records to match.")
        except Exception as e:
            messagebox.showerror("Vercel setup failed", str(e))

def main():
    root = tk.Tk()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
