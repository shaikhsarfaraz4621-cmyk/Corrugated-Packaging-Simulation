# Corrugated Box Manufacturing: Timeframes & Human Bottleneck Analysis

This document provides typical industry metrics for the Corrugated Box production lifecycle, specifically focusing on **Process Times**, **Setup Times**, and **Human Interventions** which often act as the primary bottlenecks in the factory flow.

---

## 1. Process & Setup Timeframes
*Note: Times vary based on automation level, but these represent standard medium-scale operations similar to the inspected factory.*

| Process Stage | Avg Process Speed | Avg Time Per Unit | Avg Setup Time (Batch Change) |
| :--- | :--- | :--- | :--- |
| **1. Corrugation & Gluing** | 100 - 300 meters / min | ~0.5 - 1.5 sec / sheet | 15 - 30 minutes |
| **2. Sheet Sizing / Cutting** | 150 - 300 sheets / min | ~0.2 - 0.5 sec / sheet | 5 - 10 minutes |
| **3. Pasting / Litho-Lamination** | 50 - 100 sheets / min | ~0.6 - 1.2 sec / sheet | 10 - 20 minutes |
| **4. Slotting & Creasing** | 100 - 200 boxes / min | ~0.3 - 0.6 sec / box | 15 - 25 minutes |
| **5. Die-Punching (Custom/Small)** | 50 - 100 boxes / min | ~0.6 - 1.2 sec / box | 15 - 20 minutes |
| **6. Stitching / Stapling** | 20 - 40 boxes / min (Semi) | ~1.5 - 3.0 sec / box | 5 - 15 minutes |
| **7. Bundling & QC** | 10 - 20 bundles / min | ~3.0 - 6.0 sec / bundle | ~2 minutes |

---

## 2. Critical Human Interventions (Bottleneck Risk Areas)

In packaging manufacturing, the machines run entirely too fast for humans to keep up with. Therefore, the **bottlenecks almost always occur during transitions, setup, and jamming**. If you are building a simulation to identify bottlenecks, these are the variables you should aggressively model:

### **A. Raw Material Handling & Paper Feeding [Beginning]**
* **The Action:** At the very start of the process, heavy 2-ton kraft paper reels must be transported from the raw material warehouse to the corrugator using forklifts or cranes. Operators must manually mount the rolls onto the reel stands, peel the edge, and manually splice the new web to the old one.
* **Simulation Impact:** If a forklift operator is delayed or a splice fails and breaks the paper web, the entire high-speed corrugation line halts immediately, causing massive upstream downtime before the process even begins.

### **B. Tool & Batch Changeovers (The #1 Bottleneck)**
* **The Action:** Whenever the factory switches to producing a different sized box, the line stops. Operators must manually unscrew and physically move heavy steel slotting blades, swap out massive laser-cut wooden Die-boards, and adjust the folder-gluer guide rails using wrenches and tape measures.
* **Simulation Impact:** This turns highly utilized machines into idle roadblocks. If scheduling isn't optimized to group similarly-sized boxes together, setup time will consume more shift hours than actual processing time.

### **C. Ink and Glue Viscosity Maintenance**
* **The Action:** Corrugation depends entirely on starch glue. If operators fail to manually monitor the glue temperature and viscosity, the board warps or splits.
* **Simulation Impact:** Leads to machine jams. Clearing a crushed cardboard jam out of a hot, high-speed press takes 5 to 15 minutes of pure brute force, halting throughput locally while upstream Work-in-Progress (WIP) piles up onto the factory floor.

### **D. End-of-Line Stacking & Bundling [End]**
* **The Action:** Modern Folder-Gluers/Stitchers can output 100+ boxes a minute. However, at the end of the line, human operators must catch these boxes, tap them into neat stacks, and feed them into a strapping machine. 
* **Simulation Impact:** Human physical fatigue sets in quickly. Operators cannot catch 100 boxes a minute for 8 hours. The machine operators will purposefully turn down the machine's speed dial to match the human catchers, creating an artificial, invisible bottleneck. 

### **E. Palletizing & Dispatch [End]**
* **The Action:** After boxes are bundled, they must be manually stacked onto wooden pallets, shrink-wrapped, and loaded onto outbound trucks via forklifts.
* **Simulation Impact:** If outbound logistics (truck arrivals) or warehouse space is constrained, the completed inventory backs up onto the factory floor, blocking the bundling stations and eventually suffocating the entire production line.

---

## 3. Summary of Bottlenecks
While modern corrugated machines boast incredible speeds (up to 300 meters per minute or 120 boxes per minute), the true throughput of the factory is dictated almost entirely by **human-driven transitions**. 

1. **At the Beginning (Material Prep):** Forklift logistics and manual reel splicing dictate whether the corrugator runs continuously or suffers unpredictable micro-stops.
2. **In the Middle (Changeovers & Jams):** Physical tool swaps (die boards, slotting knives) between different client orders consume vast amounts of setup time. Human error in monitoring glue viscosity causes devastating multi-minute jam-clearing delays.
3. **At the End (Catching & Palletizing):** The absolute speed of the folder-stitcher is heavily throttled to match human catching fatigue. Furthermore, if outbound dispatch logistics backup, it paralyzes the entire downstream packaging flow.

To build an accurate simulation, the variance in **setup durations**, **machine failure/jam frequencies**, and **palletization/forklift transit times** must be explicitly modeled, as these are where the real factory productivity is won or lost.
