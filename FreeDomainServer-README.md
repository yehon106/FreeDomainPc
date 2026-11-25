# FreeDomain Server

FreeDomain Server is a Windows desktop DNS manager for domains and DNS zones you already control. It manages DNS through supported provider APIs. It does not host website files or create arbitrary public domain endings.

## Download

The published Windows installer is a single file named **FD.msi**. Open the repository's **Releases** page and download `FD.msi`. Double-click it to open the standard Windows Installer setup wizard. The wizard installs the complete app and creates a Start menu shortcut. No Python, command prompt, or separate EXE is required on the computer where the app is installed.

## Build and publish

The GitHub Actions workflow builds the app on a Windows runner and attaches only `FD.msi` to the GitHub Release `v1.0.0`. After uploading these files to your repository, open **Actions → Build and publish FD.msi → Run workflow**. When the run succeeds, open **Releases** and download `FD.msi`. The MSI itself is a single file; GitHub may display it under the release assets.

## DNS providers

- **Cloudflare:** lists zones and manages DNS records through an API token.
- **deSEC:** lists domains and manages DNS RRsets through an API token.
- **DuckDNS:** supports updating the IP for a DuckDNS hostname only; it is not a general DNS zone editor.

The UI includes A, AAAA, CNAME, TXT, MX, NS, SRV, CAA, HTTPS, SVCB, TLSA, SSHFP, and NAPTR record types. Actual record support depends on the selected DNS provider.

TXT record names with underscores are supported, including `_acme-challenge`, `_dmarc`, `_vercel`, and `_smtp._tls`. Root (`@`), wildcard (`*`), and multiple TXT records are supported where the provider allows them.

## Connect a site to Vercel

1. Add your domain in your Vercel project settings.
2. Read the exact DNS instructions Vercel displays.
3. Select the matching DNS zone in this app.
4. Add the exact A, CNAME, and TXT records Vercel requests.
5. Wait for DNS propagation and verify the domain in Vercel.

The quick setup action provides common Vercel targets only. Use project-specific values shown by Vercel if they differ.

## Important limitations

- This app cannot register arbitrary `.com`, `.net`, `.dev`, or other public top-level domains.
- You must own a domain or have a delegated namespace and use a supported DNS provider.
- Provider signup, domain approval, DNS delegation, and provider limits still apply.
- DNS record support differs by provider.
- The app does not turn your home PC into a public authoritative DNS service.

## API token security

Tokens are currently stored in `%APPDATA%\\FreeDomainServer\\config.json` without encryption. Use narrowly scoped API tokens and do not share this file. Windows Credential Manager integration is not included in this version.
