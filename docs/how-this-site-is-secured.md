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
