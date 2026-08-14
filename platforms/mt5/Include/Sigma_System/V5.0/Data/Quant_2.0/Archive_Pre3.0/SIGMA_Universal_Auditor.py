import pandas as pd
import numpy as np
import os
import glob
import math

# ==========================================
# UNIVERSAL QUANT AUDITOR (PHASES 0-3)
# ==========================================
# Consolidates logic from:
# - verify_significance.py
# - phase3_vector_analysis.py
# - Phase 0.5/0.75 Analyses
# ==========================================

class SigmaConf:
    BASE_DIR = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\Common\Files\SIGMA_Quant\Trades"
    OUTPUT_DIR = r"c:\Users\User\.gemini\antigravity\brain\39397e71-a32d-42a1-bc1d-8c720bb93115"
    REPORT_FILE = os.path.join(OUTPUT_DIR, "SIGMA_Unified_Quant_Report.md")

class QuantStats:
    @staticmethod
    def calculate_significance_z(n1, p1, n2, p2):
        """Calculates Z-Score and P-Value for difference in proportions."""
        if n1 == 0 or n2 == 0: return 0, 1.0
        p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)
        se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
        if se == 0: return 0, 1.0
        z = (p1 - p2) / se
        p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
        return z, p_value

    @staticmethod
    def get_star_rating(p_value):
        if p_value < 0.001: return "*** (Highly Significant)"
        if p_value < 0.01: return "** (Significant)"
        if p_value < 0.05: return "* (Marginal)"
        return "ns (Not Significant)"

class QuantLoader:
    @staticmethod
    def load_latest_data():
        search_path = os.path.join(SigmaConf.BASE_DIR, 'QUANT_TRADES_*.csv')
        files = glob.glob(search_path)
        if not files:
            print(f"No Data Found in {search_path}")
            return None
        
        latest_file = max(files, key=os.path.getctime)
        print(f"Loading: {latest_file}")
        try:
            df = pd.read_csv(latest_file)
            return df
        except Exception as e:
            print(f"Error loading CSV: {e}")
            return None

    @staticmethod
    def enrich_data(df):
        # 1. Parse Vectors
        if 'vector_signature' in df.columns:
            vectors = df['vector_signature'].str.split(':', expand=True)
            if vectors.shape[1] >= 5:
                vectors.columns = ['V_H1', 'V_H4', 'V_D1', 'V_W1', 'V_MN1']
                for col in vectors.columns:
                    vectors[col] = pd.to_numeric(vectors[col], errors='coerce').fillna(0).astype(int)
                df = pd.concat([df, vectors], axis=1)
                
                # Direction Code
                df['dir_code'] = df['direction'].map({'BUY': 1, 'SELL': -1}).fillna(0).astype(int)
                
                # Alignments
                for tf in ['H1', 'H4', 'D1', 'W1', 'MN1']:
                    col = f'V_{tf}'
                    df[f'Align_{tf}'] = df['dir_code'] * df[col]

        # 2. Parse Age
        # Assuming 'zone_age_bars' column exists or can be derived. 
        # If not, we might need 'entry_time' - 'zone_creation_time'. 
        # For now, we'll check if exists.
        
        return df

class Phase0_Analyzer:
    """The Legend Curve (Age Analysis)"""
    @staticmethod
    def analyze(df):
        if 'zone_age_bars' not in df.columns:
            return "**Phase 0 Skipped (No Age Data)**\n\n"
        
        md = "## Phase 0: The Legend Curve (Age Physics)\n\n"
        
        # age buckets
        bins = [-1, 7, 21, 50, 200, 99999]
        labels = ['Toxic (0-7)', 'Waking (8-21)', 'Prime (22-50)', 'Veteran (51-200)', 'Legend (>200)']
        df['AgeGroup'] = pd.cut(df['zone_age_bars'], bins=bins, labels=labels)
        
        stats = df.groupby('AgeGroup').apply(lambda x: pd.Series({
            'Count': len(x),
            'WinRate': (x['result'] == 'WIN').mean() * 100,
            'ExpR': x['r_multiple'].mean()
        }))
        
        md += stats.to_markdown() + "\n\n"
        return md

class Phase075_Analyzer:
    """Fractal Resonance (Parent Analysis)"""
    @staticmethod
    def analyze(df):
        md = "## Phase 0.75: Fractal Resonance\n\n"
        
        # Check for parent columns
        has_parent = [c for c in df.columns if 'parent_id' in c]
        if not has_parent:
             return "**Phase 0.75 Skipped (No Parent Data)**\n\n"
             
        # Logic: If any parent_id > 0, it is Fractal.
        # Assuming 'parent_zone_id' or similar. using 'fractal_parent_id' if available or deriving.
        # Let's assume 'h4_parent_id' exists based on previous convos, or 'parent_count'.
        
        is_fractal = pd.Series([False] * len(df))
        if 'parent_count' in df.columns:
            is_fractal = df['parent_count'] > 0
        elif 'h4_parent_id' in df.columns:
             is_fractal = df['h4_parent_id'] > 0
             
        df['IsFractal'] = is_fractal
        
        fractal_wr = (df[df['IsFractal']]['result'] == 'WIN').mean()
        orphan_wr = (df[~df['IsFractal']]['result'] == 'WIN').mean()
        
        md += f"- **Fractal Win Rate:** {fractal_wr:.2%}\n"
        md += f"- **Orphan Win Rate:** {orphan_wr:.2%}\n"
        md += f"- **Delta:** {(fractal_wr - orphan_wr)*100:.2f} pts\n\n"
        
        return md

class Phase3_Analyzer:
    """Vector Analysis"""
    @staticmethod
    def analyze(df):
        if 'Align_H1' not in df.columns:
            return "**Phase 3 Skipped (No Vector Data)**\n\n"

        md = "## Phase 3: Vector Alignment (Royal Flush)\n\n"
        
        def categorize(row):
            h1, h4, d1, w1 = row['Align_H1'], row['Align_H4'], row['Align_D1'], row['Align_W1']
            if h1==1 and h4==1 and d1==1 and w1==1: return "ROYAL_FLUSH"
            if h1==1 and h4==1 and d1==1: return "CONSENSUS"
            if h1==1 and h4==1: return "LOCAL_FLOW"
            if h1==1 and d1==1: return "D1_SPECIALIST"
            if h1==1 and h4==-1: return "REBEL"
            return "OTHER"

        df['VectorCat'] = df.apply(categorize, axis=1)
        
        stats = df.groupby('VectorCat').apply(lambda x: pd.Series({
            'Count': len(x),
            'WinRate': (x['result'] == 'WIN').mean() * 100,
            'ExpR': x['r_multiple'].mean()
        })).sort_values('ExpR', ascending=False)
        
        md += stats.to_markdown() + "\n\n"
        
        # Significance Check
        # Royal Flush vs Others
        rf = stats.loc['ROYAL_FLUSH'] if 'ROYAL_FLUSH' in stats.index else None
        others = stats.loc['OTHER'] if 'OTHER' in stats.index else None
        
        if rf is not None and others is not None:
             z, p = QuantStats.calculate_significance_z(rf['Count'], rf['WinRate']/100, others['Count'], others['WinRate']/100)
             sig = QuantStats.get_star_rating(p)
             md += f"### Statistical Audit\n"
             md += f"- **Royal Flush vs Other:** Z={z:.2f}, P={p:.4f} {sig}\n\n"
        
        return md

def main():
    print("--- SIGMA Universal Quant Auditor (V1.0) ---")
    
    # 1. Load
    df = QuantLoader.load_latest_data()
    if df is None: return
    
    # 2. Enrich
    df = QuantLoader.enrich_data(df)
    
    # 3. Analyze
    report = "# SIGMA Unified Quant Audit\n\n"
    report += f"**Data Source:** {len(df)} Trades\n\n"
    
    report += Phase0_Analyzer.analyze(df)
    report += Phase075_Analyzer.analyze(df)
    report += Phase3_Analyzer.analyze(df)
    
    # 4. Save
    with open(SigmaConf.REPORT_FILE, 'w') as f:
        f.write(report)
    
    print(f"Report Generated: {SigmaConf.REPORT_FILE}")

if __name__ == "__main__":
    main()
