# Problem Statement: Corrugated Packaging Digital Twin

## 1. Background
In the corrugated box manufacturing industry, raw kraft paper rolls are continuously processed through sequential production lines including Corrugators, Litho-Laminators, Slotter/Die-Punchers, and Folding/Stitching machines. While modern corrugated machinery boasts incredible theoretical processing speeds (up to 300 meters per minute or 120 boxes per minute), the reality on the factory floor is vastly different.

## 2. The Core Problem: "Human Chaos" vs "Machine Math"
The theoretical maximum output of a corrugated plant is almost never achieved because the highly efficient core machines are strictly bottlenecked by volatile, human-dependent transitions. Traditional statistical models fail to accurately predict these production limits because they assume linear machine utilization.

The True Bottlenecks:
1. **Upstream Logistics Starvation:** High-speed corrugators require constant raw material feeding. Delays in forklift transit (loading 2-ton paper reels or manually splicing paper webs) force the most expensive machinery in the plant to sit idle ("Starved"), causing massive downstream disruptions before the shift even begins.
2. **Setup and Tool Changeover Variance:** In packaging, switching from producing a "Standard Box" to a "Custom Die-Cut Box" requires physical intervention. Operators must manually swap massive wooden die-boards and tweak folder rails with wrenches. This setup process generates extreme variance in downtime (modeled via skewed Lognormal distributions) that traditional spreadsheets fail to capture.
3. **Machine Breakdown & Jam Sensitivities:** Critical quality-control errors (e.g., failing to manually monitor starch glue viscosity) result in severe high-speed cardboard jams. The time to manually wrench hot, crushed paper out of the machine introduces chaotic "Failure" downtime.
4. **End-of-Line Fatigue Blocking:** The absolute speed of the folder/stitcher machine is artificially capped by the physical fatigue of the human operators catching and bundling the boxes at the end of the line. If the downstream space fills up quickly, it paralyzes the entire upstream workflow (the "Blocked" state).

## 3. Simulation Objectives
To solve this, we require a **Stochastic Discrete-Event Simulation (Digital Twin)** designed specifically to expose these "invisible" human-driven bottlenecks. 

The primary objectives of this simulation are:
- **Bottleneck Forensics:** To categorize machine idle time explicitly into `Starved (Logistics)`, `Blocked (Fatigue Limit)`, and `Failed (Jams)` rather than generic inefficiency.
- **WIP Backpressure Visualization:** To dynamically render the cumulative Work-In-Progress (WIP) queues, proving exactly when and where the factory floor saturates due to human fatigue limits.
- **Actionable ROI Insights:** To provide factory management with an AI-driven dashboard capable of accurately answering whether the plant should invest in *more forklift operators* vs *faster box-stitching machines*.

---

## 4. Exact Modeled Parameters & Distributions
To accurately test the cascading effects of human chaos, the current simulation is driven by the following carefully constructed, industry-standard metrics:

### A. Factory Layout & Fatigue Limits (Finite Queues)
The physical floor space limits human operators. Upstream machines are hard-limited by the downstream buffer capacity (`simpy.Store(capacity=N)`):
- **Corrugator:** 1 unit | *Input Queue Capacity:* 10 batches
- **Sizer & Cutter:** 1 unit | *Input Queue Capacity:* 5 batches
- **Laminator:** 1 unit | *Input Queue Capacity:* 5 batches
- **Slotter / Die-Puncher:** 2 units | *Input Queue Capacity:* 3 batches
- **Stitcher / Folder:** 2 units | *Input Queue Capacity:* 2 batches (This tight limit instantly creates fatigue blocking when human Bundlers fall behind!)
- **Bundling Line:** 1 unit | *Input Queue Capacity:* 1 batch

### B. Upstream Forklift Starvation
- The entire 3-order production flow (Standard, Custom, Printed Boxes) is supported by **exactly 2 Forklifts globally**.
- The Corrugator heavily relies on forklifts to load 2-ton paper reels. If both forklifts are busy, the Corrugator instantly starves, stalling the entire upstream factory logic.

### C. Human Setup Variance (Lognormal Distribution)
Because human setups are chaotic, we use a skewed Lognormal curve (Mean $\mu$, Std Dev $\sigma$) instead of fixed durations:
- **Corrugator Setup:** Base 25 mins ± 10 min StdDev
- **Slotter Setup (Custom Boxes):** Base 25 mins ± 12 min StdDev
- **Stitcher Setup:** Base 10 mins ± 3 min StdDev
*Result: An operator might average 25 minutes to set up a die-board, but the simulation will occasionally randomly roll a 45+ minute nightmare setup, devastating the shift's throughput.*

### D. Machine Breakdowns & Jams (Weibull Distribution)
We utilize a Weibull curve for Mean Time Between Failures (MTBF) and a Lognormal curve for Repair Times (clearing the jam):
- **Corrugator:** Jams approx. every **180 minutes** (Beta 180, Alpha 1.5). Takes **15 mins ± 5 mins** for humans to rip out the crushed, glued cardboard.
- **Slotter / Die-Puncher:** Jams approx. every **120 minutes** (Beta 120, Alpha 1.2). Takes **10 mins ± 3 mins** for humans to clear the blades.

### E. Order Demands Evaluated
- **Standard Box:** 50,000 Total units (Processed in batches of 5,000)
- **Printed Display Box:** 25,000 Total units (Processed in batches of 2,500)
- **Custom Punch Box:** 15,000 Total units (Processed in batches of 1,000)
