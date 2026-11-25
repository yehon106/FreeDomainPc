# FreeDomain Server

FreeDomain Server is a Windows desktop DNS manager. Its **Get a Free Domain** window lets users register and connect supported free hostnames from inside the application.

## Get a free hostname

### deSEC / dedyn.io

The app includes the official deSEC registration flow:

1. Enter an email, password, and desired hostname prefix.
2. Load and solve the CAPTCHA inside the app.
3. Submit the registration request for `yourname.dedyn.io`.
4. Open the verification email and paste the activation link into the app.
5. The app activates the account, signs in, stores the API token in Windows Credential Manager, and loads the registered domain.

deSEC limits dedyn.io registrations to one domain per account. Email verification and CAPTCHA are required by the provider; they cannot be skipped.

### dynv6 / dynv6.net

The app can create a hostname through the dynv6 REST API after you supply an API token. dynv6 does not expose account registration through that API, so a dynv6 account must already exist. The app cannot bypass this provider requirement.

### Other providers

- **Cloudflare:** manage DNS zones and records through an API token.
- **deSEC:** manage DNS zones and records after connecting.
- **DuckDNS:** update the IP address for an existing DuckDNS hostname.

## DNS records

The app supports A, AAAA, CNAME, TXT, MX, NS, SRV, CAA, HTTPS, SVCB, TLSA, SSHFP, and NAPTR record types where supported by the provider. Underscore labels such as `_acme-challenge`, root (`@`), and wildcard labels are supported where the provider allows them.

## Website hosting

The app manages DNS; it does not host website files or register arbitrary public top-level domains. To connect a hostname to Vercel or another host, use the exact DNS targets supplied by that hosting provider. Free hostnames remain subject to the issuing provider's terms and limits.

## Installer

The GitHub Actions workflow builds a single `FD.msi` Windows Installer package. Run **Actions → Build and publish FD.msi → Run workflow**, then download `FD.msi` from the latest GitHub Release.

## Credential storage

New API tokens are stored using the Windows Credential Manager through Python keyring. Legacy tokens in the old JSON config are migrated to Credential Manager the next time that provider is used. The app does not save account passwords.
