"""In-app free hostname registration and management."""
from __future__ import annotations
import re, tkinter as tk, webbrowser, requests, keyring
from tkinter import ttk, messagebox
from urllib.parse import urlparse

DESEC="https://desec.io/api/v1"
DYNV6="https://dynv6.com/api/v2"
SERVICE="FreeDomainServer"

class FreeDomainError(RuntimeError): pass

def request(method,url,**kwargs):
    try: r=requests.request(method,url,timeout=25,**kwargs)
    except requests.RequestException as e: raise FreeDomainError(f"Network error: {e}") from e
    try: data=r.json() if r.content else {}
    except ValueError: data={"detail":r.text[:400]}
    if not r.ok:
        detail=data.get("detail",data.get("message",f"HTTP {r.status_code}")) if isinstance(data,dict) else str(data)
        raise FreeDomainError(str(detail))
    return data

def get_captcha():
    data=request("POST",DESEC+"/captcha/")
    if not data.get("id") or not data.get("challenge"): raise FreeDomainError("Provider did not return a CAPTCHA.")
    return data

def register(email,password,captcha_id,solution,hostname):
    return request("POST",DESEC+"/auth/",json={"email":email,"password":password,"captcha":{"id":captcha_id,"solution":solution},"domain":hostname},headers={"Content-Type":"application/json"})

def activate(link):
    p=urlparse(link.strip())
    if p.scheme!="https" or p.netloc.lower() not in ("desec.io","www.desec.io"): raise FreeDomainError("Paste the HTTPS activation link from desec.io.")
    m=re.search(r"/v/activate-account/([^/]+)/?",p.path)
    if not m: raise FreeDomainError("The activation link format was not recognized.")
    return request("POST",f"{DESEC}/v/activate-account/{m.group(1)}/")

def login(email,password):
    data=request("POST",DESEC+"/auth/login/",json={"email":email,"password":password},headers={"Content-Type":"application/json"})
    token=data.get("token")
    if not token: raise FreeDomainError("Login did not return an API token.")
    keyring.set_password(SERVICE,"desec:"+email.lower(),token)
    return token

def list_desec(token):
    return request("GET",DESEC+"/domains/",headers={"Authorization":"Token "+token})

def create_dynv6(token,name):
    return request("POST",DYNV6+"/zones",headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"},json={"name":name})

class FreeDomainsWindow:
    def __init__(self,parent,app=None):
        self.app=app; self.win=tk.Toplevel(parent); self.win.title("Get a Free Domain"); self.win.geometry("700x620"); self.win.minsize(630,550); self.win.transient(parent); self.captcha=None; self.photo=None
        outer=ttk.Frame(self.win,padding=18); outer.pack(fill="both",expand=True)
        ttk.Label(outer,text="Get a Free Domain",font=("Segoe UI",18,"bold")).pack(anchor="w")
        ttk.Label(outer,text="Discover, register and connect free hostnames from inside FreeDomain Server.",foreground="#666").pack(anchor="w",pady=(3,12))
        tabs=ttk.Notebook(outer); tabs.pack(fill="both",expand=True)
        d=ttk.Frame(tabs,padding=14); y=ttk.Frame(tabs,padding=14); tabs.add(d,text="deSEC · dedyn.io"); tabs.add(y,text="dynv6 · dynv6.net")
        self._desec_ui(d); self._dyn_ui(y)

    def _desec_ui(self,p):
        ttk.Label(p,text="Register a free dedyn.io hostname",font=("Segoe UI",12,"bold")).pack(anchor="w")
        ttk.Label(p,text="deSEC allows one dedyn.io domain per account. Email verification is required.",wraplength=580).pack(anchor="w",pady=(4,10))
        self.email=tk.StringVar(); self.password=tk.StringVar(); self.prefix=tk.StringVar(); self.solution=tk.StringVar(); self.activation=tk.StringVar()
        for label,var,show in [("Email address",self.email,""),("Password",self.password,"*"),("Hostname prefix (without .dedyn.io)",self.prefix,"")]:
            ttk.Label(p,text=label).pack(anchor="w",pady=(5,2)); ttk.Entry(p,textvariable=var,show=show).pack(fill="x")
        ttk.Label(p,text="Your hostname will be prefix.dedyn.io",foreground="#666").pack(anchor="w",pady=3)
        row=ttk.Frame(p); row.pack(fill="x",pady=5)
        ttk.Button(row,text="Load CAPTCHA",command=self._captcha).pack(side="left")
        self.caplabel=ttk.Label(row,text="CAPTCHA not loaded"); self.caplabel.pack(side="left",padx=10)
        ttk.Label(p,text="CAPTCHA solution").pack(anchor="w")
        ttk.Entry(p,textvariable=self.solution).pack(fill="x")
        ttk.Button(p,text="Register account and hostname",command=self._register,style="Action.TButton").pack(fill="x",pady=10)
        ttk.Separator(p).pack(fill="x",pady=7)
        ttk.Label(p,text="After submitting, open the verification email and paste its activation link:").pack(anchor="w")
        ttk.Entry(p,textvariable=self.activation).pack(fill="x",pady=5)
        ttk.Button(p,text="Activate, sign in and connect domain",command=self._activate).pack(fill="x")
        ttk.Label(p,text="Your password is not saved. The API token is stored in Windows Credential Manager.",foreground="#666",wraplength=580).pack(anchor="w",pady=10)

    def _captcha(self):
        try:
            self.captcha=get_captcha(); self.photo=tk.PhotoImage(data=self.captcha["challenge"]); self.caplabel.configure(image=self.photo,text="")
        except Exception as e: messagebox.showerror("CAPTCHA error",str(e),parent=self.win)

    def _register(self):
        email=self.email.get().strip(); password=self.password.get(); prefix=self.prefix.get().strip().lower()
        if not email or "@" not in email or not password: messagebox.showerror("Missing details","Enter an email and password.",parent=self.win); return
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?",prefix): messagebox.showerror("Invalid hostname","Use 1–63 lowercase letters, numbers or hyphens.",parent=self.win); return
        if not self.captcha or not self.solution.get().strip(): messagebox.showerror("CAPTCHA required","Load and solve the CAPTCHA first.",parent=self.win); return
        try:
            register(email,password,self.captcha["id"],self.solution.get().strip(),prefix+".dedyn.io")
            messagebox.showinfo("Check your email","Registration submitted. Verify your email, then paste the activation link below.",parent=self.win)
        except Exception as e: messagebox.showerror("Registration failed",str(e),parent=self.win)

    def _activate(self):
        email=self.email.get().strip(); password=self.password.get()
        try:
            activate(self.activation.get()); token=login(email,password); domains=list_desec(token)
            names=[x.get("name","") for x in domains]
            messagebox.showinfo("Connected","deSEC account connected. Domains:\n"+("\n".join(names) if names else "No domain returned yet."),parent=self.win)
            if self.app:
                self.app.cfg.setdefault("providers",{})["deSEC"]={"credential_key":"desec:"+email.lower(),"account":email}
                self.app.refresh_providers(); self.app.active_provider.set("deSEC"); self.app.refresh_zones()
        except Exception as e: messagebox.showerror("Activation or login failed",str(e),parent=self.win)

    def _dyn_ui(self,p):
        ttk.Label(p,text="Create a free dynv6 hostname",font=("Segoe UI",12,"bold")).pack(anchor="w")
        ttk.Label(p,text="dynv6's API can create hostnames, but does not provide account signup. Create an account first, then paste its API token here.",wraplength=580).pack(anchor="w",pady=(5,12))
        self.dtoken=tk.StringVar(); self.dname=tk.StringVar()
        ttk.Label(p,text="dynv6 API token").pack(anchor="w"); ttk.Entry(p,textvariable=self.dtoken,show="*").pack(fill="x",pady=(3,10))
        ttk.Label(p,text="Full hostname (example: myserver.dynv6.net)").pack(anchor="w"); ttk.Entry(p,textvariable=self.dname).pack(fill="x",pady=(3,10))
        ttk.Button(p,text="Create hostname",command=self._create_dyn,style="Action.TButton").pack(fill="x")
        self.dstatus=ttk.Label(p,text=""); self.dstatus.pack(anchor="w",pady=10)
        ttk.Button(p,text="Open dynv6 account page",command=lambda:webbrowser.open("https://dynv6.com/")).pack(anchor="w",pady=8)

    def _create_dyn(self):
        token=self.dtoken.get().strip(); name=self.dname.get().strip().lower()
        if not token or not re.fullmatch(r"[a-z0-9-]+\.dynv6\.net",name): messagebox.showerror("Invalid details","Enter a token and a hostname ending in .dynv6.net.",parent=self.win); return
        try:
            result=create_dynv6(token,name); keyring.set_password(SERVICE,"dynv6:api-token",token)
            self.dstatus.configure(text="Created: "+result.get("name",name))
            messagebox.showinfo("Hostname created",result.get("name",name)+" was created.",parent=self.win)
        except Exception as e: messagebox.showerror("Could not create hostname",str(e),parent=self.win)
