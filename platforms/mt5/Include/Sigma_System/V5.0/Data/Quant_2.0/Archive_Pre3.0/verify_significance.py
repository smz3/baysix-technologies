
import math

# Data from Phase3_Vector_Analysis.md
# Strategy: Royal Flush
n1 = 410
p1 = 0.6585
# Strategy: Others (Base rate / Noise)
n2 = 1423
p2 = 0.5404

# Strategy: Consensus
n3 = 246
p3 = 0.6301

def calculate_significance(name1, n1, p1, name2, n2, p2):
    print(f"--- Comparing {name1} vs {name2} ---")
    print(f"{name1}: n={n1}, p={p1:.4f}")
    print(f"{name2}: n={n2}, p={p2:.4f}")
    
    # Pooled probability
    p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)
    
    # Standard Error
    se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
    
    # Z-score
    z = (p1 - p2) / se
    
    # P-value (two-tailed)
    # Using error function for normal distribution CDF
    p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    
    print(f"Difference: {(p1-p2)*100:.2f}%")
    print(f"Z-Score: {z:.4f}")
    print(f"P-Value: {p_value:.8f}")
    
    if p_value < 0.01:
        print("Conclusion: Statistically Highly Significant (>99%)")
    elif p_value < 0.05:
        print("Conclusion: Statistically Significant (>95%)")
    else:
        print("Conclusion: Not Statistically Significant")
    print("\n")
    return z, p_value

# 1. Royal Flush vs Others
calculate_significance("Royal Flush", n1, p1, "Others", n2, p2)

# 2. Consensus vs Others
calculate_significance("Consensus", n3, p3, "Others", n2, p2)

# 3. Royal Flush vs Consensus
calculate_significance("Royal Flush", n1, p1, "Consensus", n3, p3)

# 4. Expectancy Analysis (Physics Check)
# Win Rate is High, but Expectancy is only 0.05R.
# This implies the Reward:Risk ratio is poor or the Loss impact is high.
# E = (Win% * Reward) - (Loss% * Risk)
# 0.05 = (0.6585 * R_avg) - (0.3415 * 1.0)  <-- Assuming Risk is 1R
# 0.05 = 0.6585 * R_avg - 0.3415
# 0.3915 = 0.6585 * R_avg
# R_avg = 0.3915 / 0.6585 = 0.5945
# So average Winner is roughly 0.6R. 
# This means we are scalping or cutting winners early (Bulldozer effect?).

print(f"--- Expectancy Analysis ---")
risk = 1.0
expectancy = 0.05
win_rate = 0.6585
loss_rate = 1.0 - win_rate

# Solving for Avg Reward
# Exp = (WinRate * AvgReward) - (LossRate * Risk)
# AvgReward = (Exp + LossRate * Risk) / WinRate
avg_reward = (expectancy + loss_rate * risk) / win_rate
print(f"Implied Average Reward (R-multiple): {avg_reward:.4f}R")
print("Physicist Note: High Win Rate with Low R-multiple indicates a 'Scalper' profile.")
print("The 'Royal Flush' provides high probability but low yield per event.")
