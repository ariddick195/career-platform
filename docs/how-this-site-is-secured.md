# How This Site Is Secured

This document records the HTTPS setup completed for the site in Exercise 04, based on the verified configuration and command output provided for that work.

## Domain and DNS

The site is available at `adamriddick.me` and `www.adamriddick.me`. Both DNS names resolve to the Azure VM public IP `9.205.27.2`. Cloudflare DNS is set to **DNS only**, so it resolves the names without proxying the web traffic.

## Network access

The Azure network security rules expose these ports:

| Port | Access | Purpose |
| --- | --- | --- |
| TCP 22 | Restricted to the owner's laptop public IP as a `/32` | SSH administration |
| TCP 80 | Open to Any | HTTP requests, which Nginx redirects to HTTPS |
| TCP 443 | Open to Any | Public HTTPS requests |
| TCP 8000 | Not publicly open | Private application listener |

Nginx listens publicly on ports 80 and 443. Uvicorn listens only on `127.0.0.1:8000`, so the application port is reachable locally by Nginx and is not exposed directly to the internet.

## HTTPS and request path

Certbot obtained a certificate from Let's Encrypt. It covers both `adamriddick.me` and `www.adamriddick.me`, and Certbot deployed it to Nginx. The certificate's recorded validity period is:

- **Not before:** Oct  8 21:06:23 2026 GMT
- **Not after:** Jan  6 21:06:22 2027 GMT

Visitors connect to Nginx over HTTPS on port 443. TLS encryption starts between the visitor's browser/client and Nginx, where Nginx presents the certificate. Nginx then proxies the request to Uvicorn at `http://127.0.0.1:8000`; that local Nginx-to-Uvicorn connection uses HTTP and is not TLS-encrypted. The app listener is loopback-only.

Requests received over HTTP on port 80 redirect to HTTPS. A PowerShell check confirmed:

```text
curl.exe -I http://adamriddick.me

HTTP/1.1 301 Moved Permanently
Location: https://adamriddick.me/
```

An HTTPS GET check returned success:

```text
curl.exe -i https://adamriddick.me

HTTP/1.1 200 OK
```

## Browser verification

The site was opened at `https://adamriddick.me` in Microsoft Edge, which reported that the connection is secure.

## Certificate verification and renewal

The certificate was inspected with OpenSSL using SNI for `adamriddick.me`:

```text
echo | openssl s_client -connect adamriddick.me:443 -servername adamriddick.me 2>/dev/null | openssl x509 -noout -subject -issuer -dates

subject=CN = adamriddick.me
issuer=C = US, O = Let's Encrypt, CN = YE1
notBefore=Oct  8 21:06:23 2026 GMT
notAfter=Jan  6 21:06:22 2027 GMT
```

Certbot configured automatic renewal. A renewal simulation completed successfully with:

```text
sudo certbot renew --dry-run

Congratulations, all simulated renewals succeeded:
  /etc/letsencrypt/live/adamriddick.me/fullchain.pem (success)
```

## Nginx configuration validation

After certificate deployment, `sudo nginx -t` reported:

```text
syntax is ok
test is successful
```

## After the move to Railway (October 23, 2026)

*Written October 25, 2026, from my notes with help from an AI assistant. The Azure setup above is kept as history.*

**1. DNS finds the site.** DNS is like a phone book. When someone types `adamriddick.me`, Cloudflare (my DNS host) answers with where to connect, then steps aside. My record points to Railway and is **Proxied**, so visitors get Cloudflare's address and my server stays hidden.

**2. The browser checks the certificate.** The browser connects to Cloudflare on port 443 and gets a certificate for `adamriddick.me`. It checks that a trusted authority signed it, that the name matches, and that it has not expired. Then both sides create secret keys, and **everything after that is encrypted**.

| Issued to | Issued by | Valid from | Expires |
|---|---|---|---|
| `adamriddick.me` | Let's Encrypt (YE2) | Oct 8, 2026, 1:41:50 PM PDT | Jan 6, 2027, 12:41:49 PM PST |

Checked in Microsoft Edge on October 25, 2026, with the record Proxied, so this is the certificate Cloudflare presents to visitors. Cloudflare manages and renews it automatically, so I no longer run Certbot.

**3. Where it is encrypted.**

| Step | Protected by |
|---|---|
| Browser to Cloudflare | TLS encryption |
| Cloudflare to Railway | HTTPS encryption |
| Railway to my app and database | Railway's private network (not reachable from the internet) |

Someone on the same Wi-Fi can see the site name, but not the pages or anything typed. The database password is a Railway variable, never in my code.

**4. No plain HTTP.** `http://` and `www` addresses redirect (301) to `https://adamriddick.me/`.

**5. How you can check it.** In Chrome or Edge, click the icon left of the address, then **Connection is secure**, then **Certificate is valid** (Edge: **Certificate details**).

**6. Why it is Proxied for now.** The course setup is DNS only, so Railway issues its own certificate. When I tried that on October 23, Railway hit a Let's Encrypt rate limit, so I switched back to Proxied to keep the site secure. On October 25 the record was found DNS only again and the site failed the same way, so I set it back to Proxied ([details](evidence/railway-migration.md#5-investigated-failure-tls-certificate-after-switching-to-dns-only)). I will retry DNS only after the limit clears.

```text
> curl.exe -si https://adamriddick.me      (October 25, 2026, 4:49 PM)
HTTP/1.1 200 OK
Server: cloudflare
x-railway-request-id: PQglUYIwTreMO0cYg4a9AQ
x-railway-edge: lax1
```

