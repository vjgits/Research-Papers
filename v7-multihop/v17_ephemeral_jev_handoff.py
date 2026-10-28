#!/usr/bin/env python3
"""One-time RSA-OAEP handoff to a GitHub Actions runner. NO secrets in Git.

- Runner creates its own 3072-bit RSA private key in memory.
- Publishes ONLY its public key via authenticated GitHub Contents PUT.
- Polls for a public encrypted ciphertext committed by an authorized agent.
- Decrypts only in transient runner RAM (never to a file).
- Launches the official original SAG2/JEV runner with key in process ENV only.
- Key and private key are never saved into code, logs, source/artifacts, or GitHub.
- One-time job, max bill threshold USD 2.00 across pilot/full attempts.
"""
import base64,hashlib,json,os,pathlib,subprocess,sys,time,urllib.error,urllib.request
from cryptography.hazmat.primitives.asymmetric import rsa,padding
from cryptography.hazmat.primitives import serialization,hashes

REPO="vjgits/Research-Papers"
BRANCH="v17-hover-official-sag2-reproduction-2026-10-28"
RUN_ID=os.environ["GITHUB_RUN_ID"]
API=f"https://api.github.com/repos/{REPO}/contents"
DIR=f"v7-multihop/v17-ephemeral/{RUN_ID}"
WORKFLOW_GITHUB_TOKEN=os.environ.get("GITHUB_TOKEN","")
if not WORKFLOW_GITHUB_TOKEN:
    raise RuntimeError("Runner has no GitHub job token; do not proceed")

def request(path,method="GET",data=None):
    headers={"Authorization":f"Bearer {WORKFLOW_GITHUB_TOKEN}",
             "Accept":"application/vnd.github+json",
             "X-GitHub-Api-Version":"2022-11-28",
             "User-Agent":"pger-v17-secure-one-time-handoff"}
    q=urllib.request.Request(f"{API}/{path}",headers=headers,
       data=(json.dumps(data).encode() if data is not None else None),method=method)
    return urllib.request.urlopen(q,timeout=20)

private=rsa.generate_private_key(public_exponent=65537,key_size=3072)
pub=private.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo)
pub_sha=hashlib.sha256(pub).hexdigest()
path=f"{DIR}.pub.pem"
with request(path,"PUT",{
 "message":f"V17 ephemeral public key for only run {RUN_ID} (no secrets)",
 "branch":BRANCH,
 "content":base64.b64encode(pub).decode()}) as r:
    created=json.loads(r.read())
print("V17_EPHEMERAL_PUBLIC_KEY_READY",json.dumps({
    "run_id":RUN_ID,"path":path,"sha256":pub_sha,
    "source_api_commit":created.get("commit",{}).get("sha"),
    "private_key_ever_uploaded":False}),flush=True)

cipher_path=f"{DIR}.cipher.b64"
max_seconds=690
beg=time.monotonic()
ciphertext=None
while time.monotonic()-beg<max_seconds:
    try:
        with request(cipher_path+"?ref="+BRANCH) as r:
            contents=json.loads(r.read())
            cipher_text=base64.b64decode(contents["content"]).decode().strip()
            ciphertext=base64.b64decode(cipher_text,validate=True)
            break
    except urllib.error.HTTPError as e:
        if e.code!=404:raise
    if int(time.monotonic()-beg)%40<5:
        print("V17_EPHEMERAL_WAITING_CIPHERTEXT",json.dumps({"run_id":RUN_ID,
             "seconds_elapsed":int(time.monotonic()-beg)}),flush=True)
    time.sleep(5)
if ciphertext is None:raise RuntimeError("No encrypted handoff supplied. No paid requests made.")
if len(ciphertext)!=384:raise ValueError("Wrong RSA-3072 encrypted message length")
secret=private.decrypt(ciphertext,padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),label=None)).decode()
private=None
if not secret.startswith("sk-or-v1-") or not 45<len(secret)<250:
    raise ValueError("Decrypted payload does not have expected OpenRouter token format")
print("V17_EPHEMERAL_DECRYPTED",json.dumps({
    "key_bytes":len(secret),"secret_never_logged":True,
    "private_key_never_persisted":True}),flush=True)

env=os.environ.copy()
env["OPENROUTER_API_KEY"]=secret
secret="" # not logged and not retained by parent after spawn
runbase=["python","-u","benchmark_v17_original_jev.py","--paid-run"]
print("V17_JEV_PAID_PILOT_START",flush=True)
pilot=subprocess.run(runbase+["--max-cases","10","--budget-usd","2.00",
  "--out","results-v17-jev-ephemeral-pilot"],env=env,check=False)
if pilot.returncode:
    raise RuntimeError(f"Pilot JEV execution failed ({pilot.returncode}). STOP; no full run.")
sp=pathlib.Path("results-v17-jev-ephemeral-pilot/summary.json")
if not sp.is_file():raise RuntimeError("Pilot output missing; STOP")
pilot_data=json.loads(sp.read_text())
spent=float(pilot_data["jev_usage"]["usd_consumed"])
print("V17_JEV_PILOT_CHARGES",json.dumps({
  "n":pilot_data["n_completed"],"cost":spent,
  "provider_build":pilot_data["jev_actual_versions"]}),flush=True)
if spent >= 1.70:
    print("V17_JEV_STOP_BUDGET_RESERVE",spent,flush=True)
    sys.exit(0)
remaining=2.0-spent
# Full 120 covers the SAME first 10 to create comparable full-set
# results. Pilot spending is counted against original USD2 authorization.
print("V17_JEV_FULL_120_START",json.dumps({"remaining_budget_usd":round(remaining,4)}),flush=True)
full=subprocess.run(runbase+["--max-cases","120","--budget-usd",str(remaining),
  "--out","results-v17-jev-ephemeral-full"],env=env,check=False)
if full.returncode:
    raise RuntimeError(f"Full trial stopped with code {full.returncode}; inspect partial cases. Key stays uncommitted.")
fullpath=pathlib.Path("results-v17-jev-ephemeral-full/summary.json")
if fullpath.is_file():
    x=json.loads(fullpath.read_text())
    print("V17_JEV_COMBINED",json.dumps({
        "pilot_cost":spent,"full_cost":x["jev_usage"]["usd_consumed"],
        "total_cost":round(spent+x["jev_usage"]["usd_consumed"],6),
        "full_completed":x["n_completed"],"model_build":x["jev_actual_versions"]}),flush=True)
