"""DNS provider adapters. Tokens are stored locally in the user's config directory."""
from __future__ import annotations
import requests

TIMEOUT = 20

class ProviderError(RuntimeError):
    pass

class Cloudflare:
    name = "Cloudflare"
    def __init__(self, token: str):
        self.token = token.strip()
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
    def _request(self, method, url, **kwargs):
        try:
            r = self.s.request(method, url, timeout=TIMEOUT, **kwargs)
            data = r.json() if r.content else {}
        except requests.RequestException as e:
            raise ProviderError(f"Cloudflare connection failed: {e}") from e
        except ValueError:
            raise ProviderError("Cloudflare returned an unreadable response.")
        if not r.ok or (isinstance(data, dict) and data.get("success") is False):
            errors = data.get("errors", []) if isinstance(data, dict) else []
            msg = "; ".join(x.get("message", str(x)) for x in errors) or f"HTTP {r.status_code}"
            raise ProviderError(msg)
        return data
    def list_zones(self):
        data = self._request("GET", "https://api.cloudflare.com/client/v4/zones", params={"per_page": 50})
        return [{"id":z["id"],"name":z["name"],"status":z.get("status","")} for z in data.get("result",[])]
    def list_records(self, zone_id):
        data = self._request("GET", f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records", params={"per_page":100})
        return data.get("result",[])
    def upsert_record(self, zone_id, record):
        existing = self.list_records(zone_id)
        for item in existing:
            if item.get("type")==record["type"] and item.get("name")==record["name"] and item.get("content")==record["content"]:
                return item,"already exists"
        data = self._request("POST", f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records", json=record)
        return data.get("result",{}),"created"
    def delete_record(self, zone_id, record_id):
        self._request("DELETE", f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}")
        return True

class DeSEC:
    name = "deSEC"
    def __init__(self, token: str):
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Token {token.strip()}", "Content-Type": "application/json"})
    def _request(self, method, url, **kwargs):
        try:
            r = self.s.request(method,url,timeout=TIMEOUT,**kwargs)
            data = r.json() if r.content else {}
        except requests.RequestException as e:
            raise ProviderError(f"deSEC connection failed: {e}") from e
        except ValueError:
            raise ProviderError("deSEC returned an unreadable response.")
        if not r.ok:
            detail = data.get("detail",data.get("message",f"HTTP {r.status_code}")) if isinstance(data,dict) else f"HTTP {r.status_code}"
            raise ProviderError(str(detail))
        return data
    def list_zones(self):
        data = self._request("GET","https://desec.io/api/v1/domains/")
        return [{"id":z["name"],"name":z["name"],"status":"active"} for z in data]
    def list_records(self, zone_id):
        data = self._request("GET",f"https://desec.io/api/v1/domains/{zone_id}/rrsets/")
        out=[]
        for rr in data:
            for value in rr.get("records",[]):
                out.append({"id":f'{rr["subname"]}|{rr["type"]}|{value}',"type":rr["type"],"name":rr["subname"] or "@","content":value,"ttl":rr.get("ttl") or 3600,"proxied":False})
        return out
    def upsert_record(self, zone_id, record):
        name=record["name"].strip().rstrip(".")
        if name=="@": name=""
        elif name==zone_id or name.endswith("."+zone_id): name=name[:-len(zone_id)].rstrip(".")
        current=self._request("GET",f"https://desec.io/api/v1/domains/{zone_id}/rrsets/",params={"subname":name,"type":record["type"]})
        records=list(current[0].get("records",[])) if current else []
        if record["content"] not in records: records.append(record["content"])
        payload=[{"subname":name,"type":record["type"],"ttl":int(record.get("ttl",3600)),"records":records}]
        self._request("PUT",f"https://desec.io/api/v1/domains/{zone_id}/rrsets/",json=payload)
        return {"name":record["name"],"type":record["type"],"content":record["content"]},"saved"
    def delete_record(self, zone_id, record_id):
        subname,rtype,content=record_id.split("|",2)
        current=self._request("GET",f"https://desec.io/api/v1/domains/{zone_id}/rrsets/",params={"subname":subname,"type":rtype})
        if not current: return True
        remaining=[v for v in current[0].get("records",[]) if v!=content]
        url=f"https://desec.io/api/v1/domains/{zone_id}/rrsets/"
        if remaining:
            self._request("PUT",url,json=[{"subname":subname,"type":rtype,"ttl":current[0].get("ttl") or 3600,"records":remaining}])
        else: self._request("DELETE",url,params={"subname":subname,"type":rtype})
        return True

class DuckDNS:
    """DuckDNS only updates its assigned hostname's address; it is not a general DNS zone editor."""
    name="DuckDNS"
    def __init__(self, token: str): self.token=token.strip()
    def update_ip(self, hostname: str, ip: str=""):
        try:
            r=requests.get("https://www.duckdns.org/update",params={"domains":hostname.split(".")[0],"token":self.token,"ip":ip,"verbose":"true"},timeout=TIMEOUT)
            r.raise_for_status()
            if "OK" not in r.text: raise ProviderError(f"DuckDNS update failed: {r.text.strip()}")
            return r.text.strip()
        except requests.RequestException as e:
            raise ProviderError(f"DuckDNS connection failed: {e}") from e
