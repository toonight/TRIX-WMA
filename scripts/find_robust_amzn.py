
import pandas as pd

def main():
    df = pd.read_csv('amzn_optimization_results.csv')
    
    # Base filter: Robustness (TRIX >= 7)
    robust = df[df['trix'] >= 7].copy()
    

    with open('amzn_robust_analysis_output.txt', 'w') as f:
        f.write(f"Total Robust Candidates (TRIX>=7): {len(robust)}\n")
        
        # Scenario 1
        crash_proof = robust[robust['max_dd'] > -0.35].sort_values('cagr', ascending=False).head(10)
        f.write("\n--- SCENARIO A: Aggressive Risk Reduction (MaxDD better than -35%) ---\n")
        if not crash_proof.empty:
            f.write(crash_proof[['profile', 'trix', 'wma', 'shift', 'ts_atr', 'cagr', 'max_dd', 'n_trades']].to_string(index=False) + "\n")
        else:
            f.write("No candidates found.\n")

        # Scenario 2
        moderate = robust[(robust['max_dd'] > -0.42) & (robust['max_dd'] <= -0.35)].sort_values('cagr', ascending=False).head(10)
        f.write("\n--- SCENARIO B: Moderate Risk Reduction (MaxDD better than -42%) ---\n")
        if not moderate.empty:
            f.write(moderate[['profile', 'trix', 'wma', 'shift', 'ts_atr', 'cagr', 'max_dd', 'n_trades']].to_string(index=False) + "\n")
        else:
            f.write("No candidates found.\n")


        # Check Effect of Trailing Stop on Hybrid TRIX=10
        f.write("\n--- Effect of Trailing Stop on Hybrid TRIX=10 ---\n")
        trix10 = df[(df['trix'] == 10) & (df['profile'] == 'hybrid')].sort_values('max_dd', ascending=False).head(10)
        f.write(trix10[['trix', 'wma', 'shift', 'ts_atr', 'cagr', 'max_dd']].to_string(index=False) + "\n")

        # Scenario 3: Best Sharpe Ratio (Robust TRIX>=7)
        # Maximizing risk-adjusted return
        best_sharpe = robust.sort_values('sharpe', ascending=False).head(10)
        f.write("\n--- SCENARIO C: Best Sharpe Ratio (Robust TRIX>=7) ---\n")
        f.write(best_sharpe[['profile', 'trix', 'wma', 'shift', 'ts_atr', 'cagr', 'max_dd', 'sharpe', 'n_trades']].to_string(index=False) + "\n")



if __name__ == "__main__":
    main()
