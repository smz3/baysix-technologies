"""room_R screen v2 — EXPLORATORY. Fixes v1's two contaminations:
  (a) confirm_time is future-conditioned (non-null iff a later CF exists) -> BANNED. Anchor = bar_time.
  (b) room_R and P(hit 2R) share 1/R -> confound. Control by R tercile.
"""
import pandas as pd, numpy as np

R_DIR = "research/data/fob_payload/run_19"; K = 0.5; SETUP = "H4"
z = pd.read_parquet(f"{R_DIR}/zones.parquet")
e = pd.read_parquet(f"{R_DIR}/events.parquet")
c = pd.read_parquet(f"{R_DIR}/cycles.parquet")

cf = e[(e.label=="CF")&(e.setup_tf==SETUP)][["zone_id","cycle_id","cf_idx","direction","bar_time"]].merge(
     z[(z.source_label=="CF")&(z.setup_tf==SETUP)][["zone_id","l1","l2","realized_r","continued"]], on="zone_id")
vr = z[(z.source_label=="VR")&(z.setup_tf==SETUP)][["cycle_id","l1","l2","vr_fresh"]].rename(
     columns={"l1":"vr_l1","l2":"vr_l2"}).drop_duplicates("cycle_id")
cyc = c[["cycle_id","vr_time"]]
df = cf.merge(vr,on="cycle_id").merge(cyc,on="cycle_id")
df["bar_time"]=pd.to_datetime(df.bar_time); df["vr_time"]=pd.to_datetime(df.vr_time)
print(f"[1] joined {len(df):,}")
df = df[df.vr_time < df.bar_time].copy()          # causal: VR exists before the CF bar
print(f"[2] causal (vr_time < cf bar_time): {len(df):,}   (lost {(3561-len(df)):,})")
print("    cf_idx:", df.cf_idx.value_counts().sort_index().head(5).to_dict())

df["is_bull"] = df.direction.str.upper().eq("BUY")
band = (df.l1-df.l2).abs(); df = df[band>0].copy(); band = (df.l1-df.l2).abs()
df["R"] = band*(1+K); df["entry"] = df.l1
vr_lo = df[["vr_l1","vr_l2"]].min(axis=1); vr_hi = df[["vr_l1","vr_l2"]].max(axis=1)
near = np.where(df.is_bull, vr_lo, vr_hi)
df["room_R"] = np.where(df.is_bull, near-df.entry, df.entry-near)/df.R

print("\n[3] geometry: VR ahead of trade?")
print(f"    room_R>0: {(df.room_R>0).mean():.1%}   median room_R: {df.room_R.median():+.3f}")
print(f"    median R (price): {df.R.median():.2f}   median band: {band.median():.2f}")

print("\n[Q1] room_R + realized_r by cf_idx (all rows, causal)")
g = df[df.cf_idx.between(1,5)].groupby("cf_idx").agg(
    n=("room_R","size"), room_med=("room_R","median"),
    pct_ahead=("room_R", lambda s:(s>0).mean()),
    R_med=("R","median"), realized=("realized_r","mean"),
    win=("realized_r", lambda s:(s>0).mean()))
print(g.round(3).to_string())

# ---- Q2 with R-tercile control ----
d = df[(df.room_R>0)&df.cf_idx.between(1,3)].copy()
d["R_tercile"] = pd.qcut(d.R, 3, labels=["R_small","R_mid","R_large"])
d["wall_inside"] = d.room_R < 2.0
print(f"\n[4] confound check: corr(room_R, R) = {d.room_R.corr(d.R):+.3f}   "
      f"corr(1/R, room_R) = {(1/d.R).corr(d.room_R):+.3f}")
print("    mean realized_r by R_tercile (no room split):")
print(d.groupby("R_tercile", observed=False).realized_r.agg(["size","mean"]).round(3).to_string())

print("\n[Q2] mean realized_r: wall INSIDE 2R vs BEYOND, *within* R terciles (CF1+CF2)")
p = d[d.cf_idx.isin([1,2])]
rows=[]
for tk, sub in p.groupby("R_tercile", observed=False):
    for wk, s2 in sub.groupby("wall_inside"):
        n=len(s2); m=s2.realized_r.mean(); sd=s2.realized_r.std()
        t = m/(sd/np.sqrt(n)) if n>1 and sd>0 else np.nan
        rows.append((tk, "INSIDE 2R" if wk else "beyond 2R", n, round(m,3), f"{(s2.realized_r>0).mean():.1%}", round(t,2)))
print(pd.DataFrame(rows, columns=["R_tercile","wall","n","mean_R","win","t"]).to_string(index=False))

print("\n[Q2b] same, CF3 (the cohort we trade)")
p3 = d[d.cf_idx==3]; rows=[]
for tk, sub in p3.groupby("R_tercile", observed=False):
    for wk, s2 in sub.groupby("wall_inside"):
        n=len(s2); m=s2.realized_r.mean(); sd=s2.realized_r.std()
        t = m/(sd/np.sqrt(n)) if n>1 and sd>0 else np.nan
        rows.append((tk, "INSIDE 2R" if wk else "beyond 2R", n, round(m,3), f"{(s2.realized_r>0).mean():.1%}", round(t,2)))
print(pd.DataFrame(rows, columns=["R_tercile","wall","n","mean_R","win","t"]).to_string(index=False))

print("\n[Q3] does the wall bind? P(realized_r=+2 | room_R bucket), CF1+CF2, VR ahead")
p = d[d.cf_idx.isin([1,2])].copy()
p["bucket"]=pd.cut(p.room_R,[0,1,2,3,5,np.inf],labels=["0-1R","1-2R","2-3R","3-5R",">5R"])
out = p.groupby("bucket", observed=False).agg(n=("realized_r","size"),
        p_hit2R=("realized_r", lambda s:(s>=2).mean()), mean_R=("realized_r","mean"),
        R_med=("R","median"))
print(out.round(3).to_string())
