import httpx
import re
import json

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

with httpx.Client(follow_redirects=True, timeout=15, headers=headers) as c:
    # 1. public-search: the param is 'q', not 'query'
    r = c.get("https://gamma-api.polymarket.com/public-search?q=Pedro-Messi")
    data = r.json()
    print("public-search keys:", list(data.keys()))
    print()

    # 2. Try profiles endpoint without auth (public slugs)
    for url in [
        "https://gamma-api.polymarket.com/profiles?slugs=Pedro-Messi",
        "https://strapi-lb-ext.polymarket.com/profiles?slug=Pedro-Messi",
    ]:
        r2 = c.get(url)
        print(url, r2.status_code, r2.text[:300])
        print()

    # 3. Fetch profile page HTML and find proxyWallet
    r3 = c.get("https://polymarket.com/profile/@Pedro-Messi")
    html = r3.text

    # All labelled addresses
    for pattern, label in [
        (r'"proxyWallet"\s*:\s*"(0x[0-9a-fA-F]{40})"', "proxyWallet"),
        (r'"walletAddress"\s*:\s*"(0x[0-9a-fA-F]{40})"', "walletAddress"),
    ]:
        m = re.findall(pattern, html, re.IGNORECASE)
        if m:
            print(f"{label} in page:", m[:5])

    # Context around 'pedro-messi' username reference
    idx = html.lower().find('"pedro-messi"')
    if idx >= 0:
        ctx = html[max(0, idx - 400): idx + 800]
        print("\nContext around pedro-messi reference in HTML:")
        print(ctx)
    else:
        print("'pedro-messi' string not found in page HTML")
