# FreeDomainPc

FreeDomainPc is a Windows desktop DNS manager for domains and DNS zones you control.

## Supported providers

- Cloudflare DNS
- deSEC DNS
- DuckDNS IP address updates

## DNS record types

A, AAAA, CNAME, TXT, MX, NS, SRV, CAA, HTTPS, SVCB, TLSA, SSHFP, and NAPTR, subject to provider support.

Underscore-prefixed labels (for example, _acme-challenge), the zone apex (@), and wildcard labels are supported where the provider allows them.

## Windows installer

The Windows build workflow creates a single `FD.msi` installer and publishes it as a GitHub Release asset when a version tag is pushed.

To build from source, run the Windows build workflow from the Actions tab.

## Important

You must own the domain or have permission to manage its DNS zone. This application manages DNS records; it does not create public top-level domains or host websites on your local PC.

API credentials are stored in the current user's application configuration. Protect your Windows account and configuration files accordingly.
