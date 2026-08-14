import pandas as pd
import numpy as np
import os
import glob

# ==========================================
# CONFIGURATION
# ==========================================
# Path to the "Trades" folder containing the harvested CSV
# NOTE: QuantLogger now uses FILE_COMMON, so data is in the Common Data Path
TRADES_DIR = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\Common\Files\SIGMA_Quant\Trades"

# Output Report Path
REPORT_PATH = r"c:\Users\User\.gemini\antigravity\brain\4f072d28-9c57-44af-82e8-61e9e605e9aa\Phase3_Vector_Analysis.md"

def load_latest_trade_log():
    """Finds and loads the most recent QUANT_TRADES csv."""
    list_of_files = glob.glob(os.path.join(TRADES_DIR, 'QUANT_TRADES_*.csv'))
    if not list_of_files:
        print("No QUANT_TRADES files found in:", TRADES_DIR)
        return None
    
    latest_file = max(list_of_files, key=os.path.getctime)
    print(f"Loading Data: {latest_file}")
    
    try:
        df = pd.read_csv(latest_file)
        return df
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return None

def parse_vector_signature(df):
    """
    Parses the 'vector_signature' column (e.g. '1:1:-1:0:0') into separate columns.
    Format: H1:H4:D1:W1:MN1
    Codes: 1 (Buy), -1 (Sell), 0 (None)
    """
    if 'vector_signature' not in df.columns:
        print("Error: 'vector_signature' column missing in CSV.")
        return df

    # Split signature
    # Assuming signature is always present. Dictionary comprehension for speed.
    vectors = df['vector_signature'].str.split(':', expand=True)
    
    # Rename columns (0=H1, 1=H4, 2=D1, 3=W1, 4=MN1)
    vectors.columns = ['V_H1', 'V_H4', 'V_D1', 'V_W1', 'V_MN1']
    
    # Convert to numeric
    for col in vectors.columns:
        vectors[col] = pd.to_numeric(vectors[col], errors='coerce').fillna(0).astype(int)

    return pd.concat([df, vectors], axis=1)

def analyze_permutations(df):
    """
    Analyzes Win Rate and Expectancy for key Vector Permutations.
    Context: We typically trade H1 Fractals.
    We want to know: Does H4 alignment matter? D1 alignment? Both?
    """
    
    # 1. Normalize Direction (We want relative alignment, not absolute Buy/Sell)
    # If Trade Direction is BUY (1), and Vector is 1 => Aligned
    # If Trade Direction is SELL (-1), and Vector is -1 => Aligned
    
    # Map text direction to int
    df['dir_code'] = df['direction'].map({'BUY': 1, 'SELL': -1}).fillna(0).astype(int)
    
    # Calculate Alignment Scores (1 = Aligned, -1 = Counter, 0 = Neutral)
    tfs = ['H1', 'H4', 'D1', 'W1', 'MN1']
    for tf in tfs:
        col = f'V_{tf}'
        # Alignment = TradeDir * VectorDir 
        # (1 * 1 = 1), (-1 * -1 = 1) -> Aligned
        # (1 * -1 = -1) -> Counter
        # (1 * 0 = 0) -> Neutral
        df[f'Align_{tf}'] = df['dir_code'] * df[col]

    # Define the Permutations we care about
    # "Royal Flush" = H1+H4+D1+W1 Aligned
    # "Structural Consensus" = H1+H4+D1 Aligned
    # "D1 Filter" = D1 Aligned (ignore H4)
    
    # Helper to categorize a trade
    def categorize_trade(row):
        # Basis: H1 is usually the signal source, so Align_H1 should be 1.
        # But let's look at the HIGHER Timeframes primarily.
        
        h1 = row['Align_H1']
        h4 = row['Align_H4']
        d1 = row['Align_D1']
        w1 = row['Align_W1']
        mn1 = row['Align_MN1']
        
        # CATEGORY 1: The Royal Flush (All Green)
        if h1==1 and h4==1 and d1==1 and w1==1:
            return "ROYAL_FLUSH (H1+H4+D1+W1)"
            
        # CATEGORY 2: The Consensus (H1+H4+D1)
        if h1==1 and h4==1 and d1==1:
            return "CONSENSUS (H1+H4+D1)"
            
        # CATEGORY 3: The Local Flow (H1+H4) - checking if D1 is counter
        if h1==1 and h4==1:
            if d1 == -1: return "LOCAL_FLOW_D1_BLOCK (H1+H4 vs D1)"
            return "LOCAL_FLOW (H1+H4)"
            
        # CATEGORY 4: The D1 Specialist (H1 aligned with D1, H4 ignored/counter)
        if h1==1 and d1==1:
            if h4 == -1: return "D1_SPECIALIST_H4_BLOCK (H1+D1 vs H4)"
            return "D1_SPECIALIST (H1+D1)"
            
        # CATEGORY 5: The Rebel (H1, but H4 and D1 are against)
        if h1==1 and h4==-1 and d1==-1:
            return "REBEL (Counter H4 & D1)"
            
        return "OTHER"

    df['Vector_Category'] = df.apply(categorize_trade, axis=1)

    # Calculate Stats per Category
    # We need: Count, Win Rate, Expectancy (R-Multiple)
    
    # Helper for stats
    def get_stats(group):
        count = len(group)
        wins = group[group['r_multiple'] > 0] # Assuming > 0 is win (or > 1R?) Let's use > 0 for raw Win Rate
        # Actually standard definition: Result == "WIN"
        win_count = len(group[group['result'] == 'WIN'])
        win_rate = (win_count / count * 100) if count > 0 else 0
        
        mean_r = group['r_multiple'].mean()
        expectancy = mean_r # Simple expectancy
        
        return pd.Series({
            'Count': count,
            'Win_Rate': win_rate,
            'Expectancy_R': mean_r
        })

    stats = df.groupby('Vector_Category').apply(get_stats).sort_values('Expectancy_R', ascending=False)
    
    return stats

def generate_report(stats_df):
    """Generates a markdown report."""
    
    md = "# Phase 3: Structural Vector Analysis Report\n\n"
    md += "**Objective:** Identify the 'Royal Flush' Structural Alignment.\n\n"
    
    md += "## The Rankings (Sorted by Expectancy)\n"
    
    # Custom Markdown Generation (No Tabulate Dependency)
    if not stats_df.empty:
        # Reset index to make 'Vector_Category' a column (it's the index from groupby)
        df_display = stats_df.reset_index()
        columns = df_display.columns.tolist()
        
        # Header
        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join(["---"] * len(columns)) + " |"
        
        rows = []
        for _, row in df_display.iterrows():
            # Format numbers nicely
            row_str = []
            for col in columns:
                val = row[col]
                if isinstance(val, float):
                    val = f"{val:.2f}"
                row_str.append(str(val))
            rows.append("| " + " | ".join(row_str) + " |")
            
        md += header + "\n" + separator + "\n" + "\n".join(rows)
    else:
        md += "_No Permutations Found_"
        
    md += "\n\n"
    
    md += "## The Physicist's Conclusion\n"
    
    best_cat = stats_df.index[0]
    best_wr = stats_df.iloc[0]['Win_Rate']
    best_exp = stats_df.iloc[0]['Expectancy_R']
    
    md += f"The data indicates that **{best_cat}** is the superior alignment.\n"
    md += f"- **Win Rate:** {best_wr:.2f}%\n"
    md += f"- **Expectancy:** {best_exp:.2f}R\n\n"
    
    md += "### Recommendation:\n"
    if "ROYAL_FLUSH" in best_cat or "CONSENSUS" in best_cat:
        md += "> Adopt the **Structural Consensus** filter (H1+H4+D1).\n"
    elif "LOCAL_FLOW" in best_cat:
        md += "> The **Local Flow** (H1+H4) is sufficient. D1 is too slow/lagging.\n"
    elif "D1_SPECIALIST" in best_cat:
        md += "> The **D1 Filter** (H1+D1) is king. H4 is noise.\n"
    else:
        md += "> Results are inconclusive. Further splitting required.\n"

    print(md)
    
    with open(REPORT_PATH, 'w') as f:
        f.write(md)
    print(f"Report report generated: {REPORT_PATH}")

def main():
    print("--- Starting Phase 3 Vector Analysis ---")
    df = load_latest_trade_log()
    if df is None:
        return
        
    df = parse_vector_signature(df)
    stats = analyze_permutations(df)
    
    print("\nResults:")
    print(stats)
    
    generate_report(stats)
    print("--- Analysis Complete ---")

if __name__ == "__main__":
    main()
