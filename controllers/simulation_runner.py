import pandas as pd
import math
from engine import CorrugatedSimulation

def run_simulation_batch(machines_df, jobs_df, routings_df, num_runs):
    results_list = []
    for i in range(num_runs):
        sim = CorrugatedSimulation(machines_df, jobs_df, routings_df)
        results_list.append(sim.run())
        
    df_stats = pd.DataFrame({
        'Makespan': [r['Total_Time'] for r in results_list],
        'Lead_Time': [pd.DataFrame(r['Batch_Metrics'])['Flow_Time'].mean() for r in results_list],
        'Units': [pd.DataFrame(r['Batch_Metrics'])['Units'].sum() for r in results_list],
        'Efficiency': [(pd.DataFrame(r['Batch_Metrics'])['Active_Time'] / pd.DataFrame(r['Batch_Metrics'])['Flow_Time'] * 100).mean() for r in results_list],
        'Total_Blocked': [sum(m.get('blocked_time', 0) for m in r['Machine_Stats'].values()) for r in results_list],
        'Total_Starved': [sum(m.get('starved_time', 0) for m in r['Machine_Stats'].values()) for r in results_list],
        'Total_Jams': [r['Logs'][r['Logs']['Event'] == 'Jam Start'].shape[0] if not r['Logs'].empty and 'Event' in r['Logs'].columns else 0 for r in results_list]
    })
    
    all_batches, all_logs, all_wip, all_gantt = [], [], [], []
    machine_stats_agg = {m_id: {'working_time': 0, 'setup_time': 0, 'down_time': 0, 'starved_time':0, 'blocked_time':0, 'completed_operations': 0} for m_id in results_list[0]['Machine_Stats']}
    
    for run_idx, r in enumerate(results_list):
        run_id = f"Run_{run_idx+1}"
        
        bm = pd.DataFrame(r['Batch_Metrics'])
        bm['Run_ID'] = run_id
        all_batches.append(bm)
        
        lg = r['Logs'].copy()
        lg['Run_ID'] = run_id
        all_logs.append(lg)
        
        wip = r['WIP_Timeline'].copy()
        wip['Run_ID'] = run_id
        all_wip.append(wip)
        
        gantt = pd.DataFrame(r.get('Gantt_Log', []))
        if not gantt.empty:
            gantt['Run_ID'] = run_id
            all_gantt.append(gantt)
            
        for m_id, stats in r['Machine_Stats'].items():
            for k in stats: machine_stats_agg[m_id][k] += stats[k]
            
    for m_id in machine_stats_agg:
        for k in machine_stats_agg[m_id]: machine_stats_agg[m_id][k] /= num_runs

    def get_stats(col):
        mean = df_stats[col].mean()
        std = df_stats[col].std() if len(df_stats) > 1 else 0.0
        n = len(df_stats)
        ci95 = 1.96 * (std / math.sqrt(n)) if n > 1 else 0.0
        return {"mean": mean, "std": std, "ci95": ci95}
        
    final_result = {
        "Total_Time": df_stats['Makespan'].mean(),
        "Batch_Metrics": pd.concat(all_batches, ignore_index=True),
        "Machine_Stats": machine_stats_agg,
        "Logs": pd.concat(all_logs, ignore_index=True),
        "WIP_Timeline": pd.concat(all_wip, ignore_index=True),
        "Gantt_Log": pd.concat(all_gantt, ignore_index=True) if all_gantt else pd.DataFrame(),
        "Completed_Jobs": results_list[-1]["Completed_Jobs"],
        "MultiRunStats": {
            'Makespan': get_stats('Makespan'),
            'Lead_Time': get_stats('Lead_Time'),
            'Units': get_stats('Units'),
            'Efficiency': get_stats('Efficiency')
        },
        "df_stats": df_stats
    }
    
    return results_list, final_result
