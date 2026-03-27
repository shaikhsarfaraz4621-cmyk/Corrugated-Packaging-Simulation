import simpy
import random
import math
import pandas as pd
from typing import Dict, List, Any

def get_lognormal_params(mean, std):
    """Convert desired mean and standard dev to underlying normal distribution parameters."""
    if mean <= 0: return 0.0, 0.0
    if std <= 0: return math.log(mean), 0.0
    variance = std ** 2
    mean_sq = mean ** 2
    sigma = math.sqrt(math.log(1 + variance / mean_sq))
    mu = math.log(mean) - (sigma ** 2) / 2
    return mu, sigma

class CorrugatedSimulation:
    def __init__(self, machines_df: pd.DataFrame, jobs_df: pd.DataFrame, routings_df: pd.DataFrame, forklift_count=2):
        self.env = simpy.Environment()
        self.machines_df = machines_df
        self.jobs_df = jobs_df
        self.routings_df = routings_df
        self.forklift_count = forklift_count
        
        self.machines = {}  # {machine_id: simpy.Resource}
        self.machine_stats = {} # tracking aggregated absolute times
        self.machine_current_state = {} # tracking real-time status counts
        
        # Finite buffers mimicking human stacking/floor space limits
        # Capacity 0 means no buffer (infinite blocking downstream)
        self.buffers = {} # {machine_id: simpy.Store}
        
        # Forklift shared resource
        self.forklift = None
        
        self.completed_jobs = {job: 0 for job in jobs_df['Job_Type'].unique()}
        self.target_demand = dict(zip(jobs_df['Job_Type'], jobs_df['Target_Demand']))
        self.batch_sizes = dict(zip(jobs_df['Job_Type'], jobs_df['Batch_Size']))
        
        self.all_demands_met = self.env.event()
        
        self.log_events = []
        self.state_timeline = [] 
        self.gantt_log = [] 
        
        self.batch_metrics = []
        self.current_wip = 0
        self.wip_timeline = [] 

    def log(self, time, machine, job, batch_id, event_type, details=""):
        self.log_events.append({
            "Time": round(time, 2),
            "Machine": machine,
            "Job": job,
            "Batch": batch_id,
            "Event": event_type,
            "Details": details
        })

    def change_machine_state(self, m_id, state_key, delta):
        if m_id not in self.machine_current_state: return
        self.machine_current_state[m_id][state_key] += delta
        count = self.machine_current_state[m_id]["Count"]
        
        proc = self.machine_current_state[m_id]["Processing"]
        setup = self.machine_current_state[m_id]["Setup"]
        fail = self.machine_current_state[m_id]["Failed"]
        starved = self.machine_current_state[m_id]["Starved"]
        blocked = self.machine_current_state[m_id]["Blocked"]
        
        idle = count - (proc + setup + fail + starved + blocked)
        
        self.state_timeline.append({
            "Time": self.env.now,
            "Machine": m_id,
            "Processing": proc,
            "Setup": setup,
            "Failed": fail,
            "Starved": starved,
            "Blocked": blocked,
            "Idle": idle
        })

    def change_wip(self, delta):
        self.current_wip += delta
        self.log_queues()
        
    def log_queues(self):
        if not hasattr(self, 'buffers') or not self.buffers:
            return
        q_sizes = {m: len(buf.items) for m, buf in self.buffers.items()}
        self.wip_timeline.append({"Time": self.env.now, "Global_WIP": self.current_wip, **q_sizes})
        
    def setup_factory(self):
        # 1. Setup global forklift (Logistics)
        self.forklift = simpy.Resource(self.env, capacity=self.forklift_count)
        
        self.change_wip(0)
        
        for _, row in self.machines_df.iterrows():
            m_id = row['Machine_ID']
            count = int(row['Count'])
            buffer_cap = int(row.get('Input_Buffer_Capacity', 5)) # Finite queues!
            
            self.machines[m_id] = simpy.PriorityResource(self.env, capacity=count)
            self.buffers[m_id] = simpy.Store(self.env, capacity=buffer_cap)
            
            self.machine_stats[m_id] = {
                'working_time': 0, 'setup_time': 0, 'down_time': 0, 
                'blocked_time': 0, 'starved_time': 0, 'completed_operations': 0
            }
            self.machine_current_state[m_id] = {
                "Count": count, "Processing": 0, "Setup": 0, 
                "Failed": 0, "Starved": 0, "Blocked": 0
            }
            
            self.change_machine_state(m_id, "Processing", 0) 
            
            # Start chaotic breakdown processes
            for i in range(count):
                self.env.process(self.machine_failure_process(
                    m_id, 
                    alpha=row['Jam_Weibull_Alpha'], 
                    beta=row['Jam_Weibull_Beta'], 
                    mu=row['Repair_Lognormal_Mu'], 
                    sigma=row['Repair_Lognormal_Sigma'],
                    unit_index=i+1
                ))

    def machine_failure_process(self, m_id, alpha, beta, mu, sigma, unit_index):
        """Simulate stochastic machine jams (glue viscosity, crushed paper)."""
        resource = self.machines[m_id]
        if beta <= 0: return # No breakdowns configured
        
        norm_mu, norm_sigma = get_lognormal_params(mu, sigma)
        
        while True:
            time_to_fail = random.weibullvariate(beta, alpha) # MTBF
            yield self.env.timeout(time_to_fail)
            
            # Machine breaks down, request max priority to preempt or hold
            with resource.request(priority=0) as req:
                yield req
                start_fail = self.env.now
                self.log(self.env.now, m_id, "System", f"Unit_{unit_index}", "Jam Start")
                self.change_machine_state(m_id, "Failed", 1)
                
                repair_time = random.lognormvariate(norm_mu, norm_sigma)
                yield self.env.timeout(repair_time)
                
                self.machine_stats[m_id]['down_time'] += repair_time
                self.change_machine_state(m_id, "Failed", -1)
                self.log(self.env.now, m_id, "System", f"Unit_{unit_index}", "Jam Cleared")
                
                self.gantt_log.append({
                    "Machine": f"{m_id}_{unit_index}", 
                    "Category_ID": m_id,
                    "State": "Failure", 
                    "Start": start_fail, 
                    "Finish": self.env.now
                })

    def process_job_batch(self, job_type, batch_id):
        """A batch tracing through Corrugator -> Cutter -> ... -> Stitcher."""
        routing = self.routings_df[self.routings_df['Job_Type'] == job_type].sort_values('Sequence_Order')
        batch_size = self.batch_sizes[job_type]
        
        start_time = self.env.now
        self.change_wip(1)
        active_work_time = 0
        
        for idx, step in routing.iterrows():
            m_id = step['Machine_ID']
            base_setup = step['Setup_Time_Base']
            setup_std = step['Setup_Time_Std']
            process_time_per_unit = step['Process_Time_Per_Unit']
            total_process_time = process_time_per_unit * batch_size
            
            # 1. Logistics Delay (Forklift) BEFORE machine processing
            if step['Requires_Forklift']:
                start_starved = self.env.now
                self.change_machine_state(m_id, "Starved", 1)
                
                with self.forklift.request() as req:
                    yield req
                    # Forklift transiting/loading takes roughly 2 mins
                    yield self.env.timeout(random.uniform(1.5, 3.0)) 
                    
                starved_dur = self.env.now - start_starved
                self.machine_stats[m_id]['starved_time'] += starved_dur
                self.change_machine_state(m_id, "Starved", -1)
            
            # 2. Acquire Machine
            with self.machines[m_id].request(priority=1) as machine_req:
                self.log(self.env.now, m_id, job_type, batch_id, "Machine Acquired")
                yield machine_req
                
                # --- CRITICAL PHYSICS FIX: Pull batch off the floor buffer ONLY AFTER the machine is acquired! ---
                # This guarantees that if the downstream machine is busy, the batches stay in the physical buffer on the floor, 
                # strictly saturating the WIP capacity and mathematically triggering a 'Blocked' state upstream!
                yield self.buffers[m_id].get()
                self.log_queues()
                
                unit_label = f"{m_id}_u1"
                
                # 3. Setup Tooling (Lognormal Distribution for Human Chaos)
                start_setup = self.env.now
                self.change_machine_state(m_id, "Setup", 1)
                
                setup_mu, setup_sigma = get_lognormal_params(base_setup, setup_std)
                actual_setup = random.lognormvariate(setup_mu, setup_sigma) if setup_mu > 0 else 0
                yield self.env.timeout(actual_setup)
                
                self.change_machine_state(m_id, "Setup", -1)
                self.machine_stats[m_id]['setup_time'] += actual_setup
                active_work_time += actual_setup
                self.log(self.env.now, m_id, job_type, batch_id, f"Setup Finish (Took {round(actual_setup,1)}m)")
                self.gantt_log.append({"Machine": unit_label, "Category_ID": m_id, "State": "Setup", "Start": start_setup, "Finish": self.env.now})
                
                # 4. Processing
                start_proc = self.env.now
                self.change_machine_state(m_id, "Processing", 1)
                yield self.env.timeout(total_process_time)
                self.change_machine_state(m_id, "Processing", -1)
                self.machine_stats[m_id]['working_time'] += total_process_time
                self.machine_stats[m_id]['completed_operations'] += 1
                active_work_time += total_process_time
                self.log(self.env.now, m_id, job_type, batch_id, "Process Finish", details=f"Output {batch_size} boxes")
                self.gantt_log.append({"Machine": unit_label, "Category_ID": m_id, "State": "Processing", "Start": start_proc, "Finish": self.env.now})
                
                # 5. Blocking / Forwarding to downstream queue
                # Find next machine
                next_step_idx = routing.index.get_loc(idx) + 1
                if next_step_idx < len(routing):
                    next_m_id = routing.iloc[next_step_idx]['Machine_ID']
                    
                    # Machine is technically still held by the batch if the downstream buffer is full!
                    # "Blocking" phenomenon
                    start_block = self.env.now
                    self.change_machine_state(m_id, "Blocked", 1)
                    
                    # Put it into next machine's input buffer (will wait if buffer full)
                    yield self.buffers[next_m_id].put(batch_id)
                    self.log_queues()
                    
                    block_dur = self.env.now - start_block
                    self.change_machine_state(m_id, "Blocked", -1)
                    self.machine_stats[m_id]['blocked_time'] += block_dur
                    if block_dur > 0:
                        self.log(self.env.now, m_id, job_type, batch_id, f"Blocked Downstream for {round(block_dur, 1)}m")
                        self.gantt_log.append({"Machine": unit_label, "Category_ID": m_id, "State": "Blocked", "Start": start_block, "Finish": self.env.now})
        
        # Job fully completed
        end_time = self.env.now
        self.change_wip(-1)
        self.batch_metrics.append({
            "Job_Type": job_type,
            "Batch_ID": batch_id,
            "Units": batch_size,
            "Start_Time": start_time,
            "End_Time": end_time,
            "Flow_Time": end_time - start_time,
            "Active_Time": active_work_time
        })
        
        self.completed_jobs[job_type] += batch_size
        
        if all(self.completed_jobs[jt] >= self.target_demand[jt] for jt in self.target_demand):
            if not self.all_demands_met.triggered:
                self.all_demands_met.succeed()

    def job_source(self, job_type):
        """Release orders into the factory."""
        batch_size = self.batch_sizes[job_type]
        target = self.target_demand[job_type]
        batches_needed = (target + batch_size - 1) // batch_size
        
        arr_min = self.jobs_df.loc[self.jobs_df['Job_Type'] == job_type, 'Interarrival_Min'].iloc[0]
        arr_max = self.jobs_df.loc[self.jobs_df['Job_Type'] == job_type, 'Interarrival_Max'].iloc[0]
        
        # Find first machine buffer to push into
        first_machine = self.routings_df[self.routings_df['Job_Type'] == job_type].sort_values('Sequence_Order').iloc[0]['Machine_ID']
        
        for i in range(batches_needed):
            batch_id = f"{job_type}_{i+1}"
            
            # Must put into the first machine's queue before processing
            yield self.buffers[first_machine].put(batch_id)
            self.log_queues()
            self.env.process(self.process_job_batch(job_type, batch_id=batch_id))
            
            # Delay arrival slightly to mimic realistic warehouse forklift transit times
            yield self.env.timeout(random.uniform(arr_min, arr_max))

    def run(self, until_time=None):
        self.setup_factory()
        
        for job_type in self.target_demand.keys():
            self.env.process(self.job_source(job_type))
            
        if until_time:
            self.env.run(until=until_time)
        else:
            self.env.run(until=self.all_demands_met)
            
        return {
            "Total_Time": self.env.now,
            "Completed_Jobs": self.completed_jobs,
            "Machine_Stats": self.machine_stats,
            "Logs": pd.DataFrame(self.log_events),
            "State_Timeline": pd.DataFrame(self.state_timeline),
            "Gantt_Log": pd.DataFrame(self.gantt_log),
            "Batch_Metrics": pd.DataFrame(self.batch_metrics),
            "WIP_Timeline": pd.DataFrame(self.wip_timeline)
        }
