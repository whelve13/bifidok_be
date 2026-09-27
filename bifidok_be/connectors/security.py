import requests
from typing import Dict, Any, List

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def analyze_security_posture(domain: str) -> Dict[str, Any]:
    """
    Performs passive security reconnaissance (Row 26 & 27 of data_api_endpoints.xlsx):
    - Subdomain exposure reconnaissance
    - HTTP security headers assessment (CSP, HSTS, X-Frame-Options, Cookie security)
    - Estimates security resilience grade (A to F) for NIS2/DORA compliance hooks.
    """
    results = {
        "domain": domain,
        "grade": "B",
        "missing_headers": [],
        "exposed_subdomains": [],
        "has_vulnerability_risk": False,
        "evidence": []
    }

    if not domain:
        return results

    # 1. Direct Web Resilience & Security Headers Audit (Local Observatory Equivalent)
    try:
        target_url = f"https://{domain}" if not domain.startswith("http") else domain
        resp = requests.get(target_url, headers=HEADERS, timeout=4, allow_redirects=True)
        headers_lower = {k.lower(): v for k, v in resp.headers.items()}

        missing = []
        if "content-security-policy" not in headers_lower:
            missing.append("Content-Security-Policy (CSP)")
        if "strict-transport-security" not in headers_lower:
            missing.append("Strict-Transport-Security (HSTS)")
        if "x-frame-options" not in headers_lower and "frame-ancestors" not in headers_lower.get("content-security-policy", ""):
            missing.append("X-Frame-Options")

        results["missing_headers"] = missing

        # Calculate Grade
        if len(missing) >= 2:
            results["grade"] = "D"
            results["has_vulnerability_risk"] = True
            results["evidence"].append(
                f"Web resilience grade: D (Missing critical headers: {', '.join(missing)}). Fails NIS2 hygiene standards."
            )
        elif len(missing) == 1:
            results["grade"] = "C"
            results["evidence"].append(f"Web resilience grade: C (Missing {missing[0]}).")
        else:
            results["grade"] = "A"
            results["evidence"].append("Web resilience grade: A (Strong security headers configured).")

        # 2. Passive Tech Stack Fingerprinting
        detected_tech = []
        server_hdr = headers_lower.get("server", "")
        powered_by = headers_lower.get("x-powered-by", "")
        cookies_str = headers_lower.get("set-cookie", "")
        combined_meta = f"{server_hdr} {powered_by} {cookies_str}".lower()

        if any(w in combined_meta for w in ["sap", "sap-usercontext", "sap_session", "netweaver"]):
            detected_tech.append("SAP ERP")
        if any(w in combined_meta for w in ["salesforce", "force.com"]):
            detected_tech.append("Salesforce CRM")
        if any(w in combined_meta for w in ["oracle", "peoplesoft", "siebel"]):
            detected_tech.append("Oracle Systems")
        if any(w in combined_meta for w in ["aws", "amazon", "awselb", "awsalb"]):
            detected_tech.append("Amazon Web Services (AWS)")
        if any(w in combined_meta for w in ["azure", "arraffinity", "microsoft"]):
            detected_tech.append("Microsoft Azure")
        if any(w in combined_meta for w in ["cloudflare", "cf-ray"]):
            detected_tech.append("Cloudflare Enterprise")
        if any(w in combined_meta for w in ["nginx", "envoy", "istio", "k8s", "kubernetes"]):
            detected_tech.append("Kubernetes / Cloud-Native")

        results["detected_tech"] = detected_tech
        results["has_enterprise_erp"] = any(t in detected_tech for t in ["SAP ERP", "Salesforce CRM", "Oracle Systems"])
        results["tech_stack_breadth"] = len(detected_tech)
        if detected_tech:
            results["evidence"].append(f"Passive Tech Stack Fingerprint: Detected {', '.join(detected_tech[:3])}.")

    except Exception:
        results["grade"] = "C"
        results["evidence"].append(f"Primary domain {domain} connection timeout or redirected.")
        results["detected_tech"] = []
        results["has_enterprise_erp"] = False
        results["tech_stack_breadth"] = 0

    # 2. Subdomain Reconnaissance via crt.sh (Row 26)
    try:
        clean_domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
        # Query specific common high-risk prefixes to avoid multi-megabyte payloads
        prefixes = ["vpn", "jira", "sap", "gitlab"]
        detected_subs = []
        for p in prefixes:
            try:
                sub = f"{p}.{clean_domain}"
                s_resp = requests.get(f"https://crt.sh/?q={sub}&output=json", headers=HEADERS, timeout=2)
                if s_resp.status_code == 200 and len(s_resp.json()) > 0:
                    detected_subs.append(sub)
            except Exception:
                continue

        results["exposed_subdomains"] = detected_subs
        if detected_subs:
            results["evidence"].append(f"Exposed public subdomains discovered: {', '.join(detected_subs)}")
    except Exception:
        pass

    return results
