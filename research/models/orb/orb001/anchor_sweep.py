"""ORB-001 anchor/OR-window sweep task 15. IS ONLY. python research/models/orb/anchor_sweep.py"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from research.code.arctic_io import read_tick_month
from tqdm import tqdm
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from research.models.orb.orb001.orb_core import _tick_files, IS_END
from research.code.session_cache import session_files  # Layer A: read 07:00-22:00 session slice
SPREAD=2.0*0.10; IS_CUT=np.datetime64(IS_END); EOD_HOUR=21
NS_H=3_600_000_000_000; NS_M=60_000_000_000; NS_D=86_400_000_000_000
ANCHOR_HOURS=[8.0,8.5,9.0,10.0]; N_MINUTES=[3,5,10,15,30]
IS_BASE_REF=0.3114; IS_TRAIL_REF=0.7910; CONTROL_TOL=0.01
_OUT=REPO/"research"/"outputs"/"orb"/"anchor_sweep"


def _simulate_day(ts, mid, day0, anchor_hour, n_minutes):
    half=SPREAD*0.5; anchor=day0+int(anchor_hour*NS_H)
    or_end=anchor+n_minutes*NS_M; eod=day0+EOD_HOUR*NS_H
    in_or=(ts>=anchor)&(ts<or_end)
    if not in_or.any(): return None,None
    or_hi,or_lo=mid[in_or].max(),mid[in_or].min()
    rw=or_hi-or_lo
    if rw<=0: return None,None
    post=(ts>=or_end)&(ts<eod)
    if not post.any(): return None,None
    pmid=mid[post]
    up=pmid>=or_hi-half; dn=pmid<=or_lo+half
    i_up=int(np.argmax(up)) if up.any() else None
    i_dn=int(np.argmax(dn)) if dn.any() else None
    if i_up is None and i_dn is None: return None,None
    if i_dn is None or (i_up is not None and i_up<=i_dn):
        pdir,e,i_b=1.0,or_hi,i_up
    else:
        pdir,e,i_b=-1.0,or_lo,i_dn
    emid=pmid[i_b:]
    if len(emid)<2: return None,None
    g=pdir*(emid-e); ef_fill=emid-pdir*half; ef_adj=pdir*(ef_fill-e)/rw
    def first(mask): return int(np.argmax(mask)) if mask.any() else None
    i_stop=first(g<=-rw+half); i_tgt=first(g>=3*rw+half)
    cands=[(i,r) for i,r in [(i_tgt,3.0),(i_stop,-1.0)] if i is not None]
    if not cands: R_base=float(ef_adj[-1])
    else: i_b2,r_b=min(cands,key=lambda c:c[0]); R_base=r_b
    peak_g=np.maximum.accumulate(g); rel=g<=peak_g-rw+half
    i_x=first(rel)
    R_trail=float(ef_adj[i_x]) if i_x is not None else float(ef_adj[-1])
    meta={"range_w":rw}
    return ({**meta,"R":R_base},{**meta,"R":R_trail})


def _scan_cell(files,anchor_hour,n_minutes,desc=""):
    base_rows,trail_rows=[],[]
    for f in tqdm(files,desc=desc,leave=False):
        df=read_tick_month(f, columns=["ts_utc","bid","ask"])
        df=df[df["ts_utc"].values<IS_CUT]
        if df.empty: continue
        ts_all=df["ts_utc"].values.astype("datetime64[ns]").astype(np.int64)
        mid_all=(df["bid"].values+df["ask"].values)*0.5
        day_key=ts_all//NS_D
        for d in np.unique(day_key):
            mk=day_key==d
            b,t=_simulate_day(ts_all[mk],mid_all[mk],int(d)*NS_D,anchor_hour,n_minutes)
            if b is not None: base_rows.append(b)
            if t is not None: trail_rows.append(t)
    return base_rows,trail_rows


def _stats(rows,arm,anchor_hour,n_minutes):
    empty={"arm":arm,"anchor_hour":anchor_hour,"n_minutes":n_minutes,
           "n":0,"E_R":None,"SE_R":None,"t_stat":None,
           "win_pct":None,"dollar_per_trade":None}
    if not rows: return empty
    R=np.array([r["R"] for r in rows],dtype=float)
    rw=np.array([r["range_w"] for r in rows],dtype=float)
    n=len(R); mu=float(R.mean()); sd=float(R.std(ddof=1))
    se=sd/np.sqrt(n)
    t=mu/se if sd>0 and n>1 else float("nan")
    dpt=float((R*rw).mean())
    return {
        "arm":arm,"anchor_hour":anchor_hour,"n_minutes":n_minutes,
        "n":n,"E_R":round(mu,4),"SE_R":round(se,4),
        "t_stat":round(t,2),"win_pct":round(float((R>0).mean())*100,1),
        "dollar_per_trade":round(dpt,4)}


def _ah_str(ah):
    h,m=divmod(int(round(ah*60)),60)
    return f"{h:02d}:{m:02d}"


def _print_table(df_arm,arm_name):
    print("  === " + arm_name + " -- ranked by dollar/trade ===")
    print("  anchor   N       n    E[R]   SE_R      t   win%   dol/trade  note")
    for _,row in df_arm.iterrows():
        flag=""
        nv=int(row["n"]) if row["n"] is not None else 0
        if nv<200: flag="  **low-n"
        elif float(row["anchor_hour"])==8.0 and int(row["n_minutes"])==5: flag="  <-- incumbent"
        ah=_ah_str(float(row["anchor_hour"])); nm=int(row["n_minutes"])
        er=row["E_R"]; se=row["SE_R"]; ts=row["t_stat"]
        dp=row["dollar_per_trade"]; wp=row["win_pct"]
        er_s=f"{er:+.4f}" if er is not None else "   n/a"
        se_s=f"{se:.4f}"  if se is not None else "  n/a"
        ts_s=f"{ts:+.2f}" if ts is not None else "  n/a"
        dp_s=f"{dp:+.6f}" if dp is not None else "   n/a"
        wp_s=f"{wp:.1f}"  if wp is not None else " n/a"
        print(f"  {ah:>7}  {nm:>2}  {nv:>6}  {er_s:>7}  {se_s:>6}  {ts_s:>6}  {wp_s:>5}  {dp_s:>12}{flag}")


def main():
    _OUT.mkdir(parents=True,exist_ok=True)
    print("="*88)
    print("ORB-001 ANCHOR/OR-WINDOW SWEEP task 15 -- IS 2016->2024-05-02")
    print("Metric=dollar/trade  |  base_3R + trail_1R per cell")
    print(f"Grid: anchor_hour={ANCHOR_HOURS}  N_min={N_MINUTES}")
    tc=len(ANCHOR_HOURS)*len(N_MINUTES)
    print(f"Cells: {tc} x 2 arms = {tc*2} stat vectors")
    print("="*88)
    files=session_files(None)
    if not files: sys.exit("No session-cache files. Build first: python research/code/session_cache.py build")
    print("session-cache files: " + str(len(files)))
    print("[STEP 1] Control repro: anchor=08:00 N=5 ...")
    ctrl_base,ctrl_trail=_scan_cell(files,8.0,5,desc="control 08:00/N=5")
    ctrl_b=_stats(ctrl_base,"base_3R",8.0,5)
    ctrl_t=_stats(ctrl_trail,"trail_1R",8.0,5)
    er_b=ctrl_b["E_R"]; t_b=ctrl_b["t_stat"]; w_b=ctrl_b["win_pct"]
    n_b=ctrl_b["n"]; dp_b=ctrl_b["dollar_per_trade"]
    er_t=ctrl_t["E_R"]; t_t=ctrl_t["t_stat"]; w_t=ctrl_t["win_pct"]
    n_t=ctrl_t["n"]; dp_t=ctrl_t["dollar_per_trade"]
    print(f"  base_3R : E[R]={er_b:+.4f}  t={t_b:+.2f}  win={w_b:.1f}%  $/t={dp_b:+.4f}  n={n_b}")
    print(f"  trail_1R: E[R]={er_t:+.4f}  t={t_t:+.2f}  win={w_t:.1f}%  $/t={dp_t:+.4f}  n={n_t}")
    base_ok=er_b is not None and abs(er_b-IS_BASE_REF)<CONTROL_TOL
    trail_ok=er_t is not None and abs(er_t-IS_TRAIL_REF)<CONTROL_TOL*2
    lbl_b="OK" if base_ok else "*** MISMATCH"
    lbl_t="OK" if trail_ok else "*** MISMATCH"
    print(f"  base_3R  repro vs {IS_BASE_REF:+.4f}: {lbl_b}")
    print(f"  trail_1R repro vs {IS_TRAIL_REF:+.4f}: {lbl_t}")
    if not base_ok or not trail_ok:
        print("*** MISMATCH -- halting"); sys.exit(1)
    print("  Controls reproduced.")
    grid_cells=[(ah,nm) for ah in ANCHOR_HOURS for nm in N_MINUTES]
    all_rows=[ctrl_b,ctrl_t]
    print(f"[STEP 2] Full grid sweep ({len(grid_cells)} cells) ...")
    cell_bar=tqdm(grid_cells,desc="anchor x N grid",unit="cell")
    for anchor_hour,n_minutes in cell_bar:
        if anchor_hour==8.0 and n_minutes==5:
            cell_bar.write("  skip 08:00/N=5 -- already computed"); continue
        ah_s=_ah_str(anchor_hour)
        cell_bar.set_postfix(anchor=ah_s,N=n_minutes)
        cell_bar.write(f"  sweep {ah_s}/N={n_minutes:2d}min ...")
        br,tr=_scan_cell(files,anchor_hour,n_minutes,desc=f"{ah_s}/N={n_minutes}")
        b_st=_stats(br,"base_3R",anchor_hour,n_minutes)
        t_st=_stats(tr,"trail_1R",anchor_hour,n_minutes)
        all_rows.extend([b_st,t_st])
        nb=b_st["n"]; erb=b_st["E_R"]; dpb=b_st["dollar_per_trade"]; tsb=b_st["t_stat"]
        ert=t_st["E_R"]; dpt=t_st["dollar_per_trade"]; tst=t_st["t_stat"]
        low="  **low-n" if nb<200 else ""
        cell_bar.write(f"    base_3R : E[R]={erb:+.4f}  $/t={dpb:+.4f}  t={tsb:+.2f}  n={nb}{low}")
        cell_bar.write(f"    trail_1R: E[R]={ert:+.4f}  $/t={dpt:+.4f}  t={tst:+.2f}  n={nb}{low}")
    print("[STEP 3] Results grid ...")
    df=pd.DataFrame(all_rows)
    inc_row=df[(df["arm"]=="trail_1R")&(df["anchor_hour"]==8.0)&(df["n_minutes"]==5)].iloc[0]
    inc_dp=float(inc_row["dollar_per_trade"]); inc_se=float(inc_row["SE_R"])
    trail_df=df[df["arm"]=="trail_1R"].sort_values("dollar_per_trade",ascending=False)
    base_df=df[df["arm"]=="base_3R"].sort_values("dollar_per_trade",ascending=False)
    _print_table(trail_df,"trail_1R")
    _print_table(base_df,"base_3R")
    trail_valid=trail_df[trail_df["n"].fillna(0).astype(int)>=200]
    if trail_valid.empty: trail_valid=trail_df
    best=trail_valid.iloc[0]
    best_dp=float(best["dollar_per_trade"]); best_ah=float(best["anchor_hour"])
    best_nm=int(best["n_minutes"]); best_se=float(best["SE_R"])
    gap_dp=best_dp-inc_dp; within_1se=abs(gap_dp)<=best_se
    print("="*88)
    print("VERDICT")
    print(f"  Incumbent: 08:00/N=5 trail_1R  dollar/trade={inc_dp:+.4f}  SE_R={inc_se:.4f}")
    if best_ah==8.0 and best_nm==5:
        print("  Best cell IS the incumbent (08:00/N=5).")
        print("  08:00/N=5 confirmed IS-optimal. Anchor assumption validated.")
        decision="KEEP_INCUMBENT"
    elif within_1se:
        print(f"  Best: {_ah_str(best_ah)}/N={best_nm} $/t={best_dp:+.4f} gap={gap_dp:+.4f} best_SE_R={best_se:.4f}")
        print("  Gap within 1 SE -- KEEP incumbent (08:00/N=5).")
        decision="KEEP_INCUMBENT"
    else:
        print(f"  Best: {_ah_str(best_ah)}/N={best_nm} $/t={best_dp:+.4f} gap={gap_dp:+.4f} >SE={best_se:.4f}")
        print("  Gap exceeds 1 SE -- FLAG for OOS re-validation.")
        decision="FLAG_FOR_OOS"
    print("="*88)
    df.to_csv(_OUT/"anchor_sweep_grid.csv",index=False,encoding="utf-8")
    summary={
        "model":"ORB-001","analysis":"anchor_sweep_task15",
        "is_sealed":str(IS_END),"anchor_hours":ANCHOR_HOURS,"n_minutes_list":N_MINUTES,
        "control_repro":{"base_3R":ctrl_b,"trail_1R":ctrl_t,"base_ok":base_ok,"trail_ok":trail_ok},
        "incumbent":{"anchor_hour":8.0,"n_minutes":5,"trail_dpt":inc_dp,"trail_SE_R":inc_se},
        "best_trail_cell":{"anchor_hour":best_ah,"n_minutes":best_nm,
                           "dollar_per_trade":best_dp,"SE_R":best_se,
                           "gap_vs_incumbent":gap_dp,"within_1se":within_1se},
        "decision":decision,"grid_rows":all_rows};
    (_OUT/"anchor_sweep_summary.json").write_text(json.dumps(summary,indent=2,default=str),encoding="utf-8")
    print("Outputs -> " + str(_OUT))
    print("  anchor_sweep_grid.csv")
    print("  anchor_sweep_summary.json")

if __name__=="__main__": main()
