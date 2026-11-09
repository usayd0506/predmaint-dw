from datetime import timedelta
import math
import random
import numpy as np
import pandas as pd

# Each job is a 4-hour demonstration inspection. Scheduling tasks are synthetic.
SLOT_HOURS = 4
DAYS = 14
SLOTS_PER_DAY = 3
POPULATION = 100
GENERATIONS = 200


def distance_km(a, b):
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])

    lat2, lon2 = math.radians(b[0]), math.radians(b[1])

    x = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2

    return 6371 * 2 * math.asin(min(1, math.sqrt(x)))


def prepare(engine_health, technicians, plants):

    tasks = engine_health[engine_health.risk_level.isin(["Critical", "Warning"])].copy()

    tasks = tasks.sort_values(["predicted_rul", "failure_prob_30"], ascending=[True, False]).head(30)

    people = technicians.sort_values("technician_id").reset_index(drop=True)

    if tasks.empty:
        return tasks, people, np.zeros((0, len(people)))
    
    if people.empty:
        raise ValueError("Cannot schedule without technicians")
    
    locations = plants.set_index("plant_id")[["latitude", "longitude"]].to_dict("index")

    distances = np.zeros((len(tasks), len(people)))
    
    for i, plant_id in enumerate(tasks.plant_id):
        for j, home in enumerate(people.plant_id):

            a = locations[int(plant_id)]
            b = locations[int(home)]

            distances[i, j] = distance_km((a["latitude"], a["longitude"]),
                                          (b["latitude"], b["longitude"]))
            
    return tasks.reset_index(drop=True), people, distances


def score(chrom, tasks, people, distances):
    #lower score is better
    risk = 0.0
    travel = 0.0
    labor = 0.0
    overlap = 0
    workload = {}

    occupied = set()

    for i, (tech, slot) in enumerate(chrom):
        pair = (tech, slot)
        if pair in occupied:
            overlap += 1

        occupied.add(pair)

        week = (slot // SLOTS_PER_DAY) // 7

        workload[(tech, week)] = workload.get((tech, week), 0) + SLOT_HOURS

        risk += float(tasks.iloc[i].failure_prob_30) * slot

        travel += distances[i, tech]

        labor += float(people.iloc[tech].hourly_rate) * SLOT_HOURS

    overload = 0
    for (tech, week), hours in workload.items():
        
        overload += max(0, hours - float(people.iloc[tech].max_hours_per_week))
    # These are explicit demo weights, not fitted real-world business costs

    total = 10*risk + 0.08*travel + labor + 10000*overlap + 1000*overload
    
    return total, {"risk_penalty": risk, "travel_km": travel,
                   "labor_cost": labor, "overlaps": overlap, "overload_hours": overload}


def greedy(tasks, people, distances):
    chrom = []
    used = set()
    weekly = {}
    for i in range(len(tasks)):
        candidates = []
        for tech in range(len(people)):
            for slot in range(DAYS*SLOTS_PER_DAY):
                week = slot // (7*SLOTS_PER_DAY)
                hours = weekly.get((tech, week), 0)
                if (tech, slot) not in used and hours + SLOT_HOURS <= float(people.iloc[tech].max_hours_per_week):
                    candidates.append((slot, distances[i, tech], tech))
        if not candidates:
            raise ValueError("Not enough technician capacity within 14 days")
        slot, _, tech = min(candidates)
        chrom.append((tech, slot))
        used.add((tech, slot))
        week = slot // (7*SLOTS_PER_DAY)
        weekly[(tech, week)] = weekly.get((tech, week), 0) + SLOT_HOURS
    return chrom


def repair(chrom, people):
    """Repair duplicate slots and weekly overload so output schedules are feasible."""
    used, weekly, result = set(), {}, []
    for tech, slot in chrom:
        tech = int(tech)
        slot = int(slot)
        def free(t, s):
            w = s // (7*SLOTS_PER_DAY)
            return ((t, s) not in used and
                    weekly.get((t, w), 0) + SLOT_HOURS <= float(people.iloc[t].max_hours_per_week))
        if not free(tech, slot):
            alternatives = [(abs(s-slot), t != tech, s, t)
                            for t in range(len(people))
                            for s in range(DAYS*SLOTS_PER_DAY) if free(t, s)]
            if not alternatives:
                raise ValueError("Insufficient technician availability")
            _, _, slot, tech = min(alternatives)
        result.append((tech, slot))
        used.add((tech, slot))
        week = slot // (7*SLOTS_PER_DAY)
        weekly[(tech, week)] = weekly.get((tech, week), 0) + SLOT_HOURS
    return result


def genetic_algorithm(tasks, people, distances, seed, population=POPULATION, generations=GENERATIONS):
    rng = random.Random(seed)
    n = len(tasks)
    if n == 0:
        return [], 0, []
    base = greedy(tasks, people, distances)
    population_list = [base]
    for _ in range(population-1):
        candidate = [(rng.randrange(len(people)), rng.randrange(DAYS*SLOTS_PER_DAY)) for _ in range(n)]
        population_list.append(repair(candidate, people))
    convergence = []
    for generation in range(generations):
        population_list.sort(key=lambda c: score(c, tasks, people, distances)[0])
        convergence.append(score(population_list[0], tasks, people, distances)[0])
        next_gen = population_list[:2]  # elitism
        while len(next_gen) < population:
            def tournament():
                sample = rng.sample(population_list, 3)
                return min(sample, key=lambda c: score(c, tasks, people, distances)[0])
            a, b = tournament(), tournament()
            if n >= 3:
                p, q = sorted(rng.sample(range(1, n), 2))
                child = a[:p] + b[p:q] + a[q:]  # two-point crossover
            else:
                child = a[:]
            for i in range(n):
                if rng.random() < 0.05:
                    child[i] = (rng.randrange(len(people)), rng.randrange(DAYS*SLOTS_PER_DAY))
            next_gen.append(repair(child, people))
        population_list = next_gen
    best = min(population_list, key=lambda c: score(c, tasks, people, distances)[0])
    return best, score(best, tasks, people, distances)[0], convergence


def make_schedules(health, technicians, plants, start_date, quick=False):
    tasks, people, distances = prepare(health, technicians, plants)
    if len(tasks) == 0:
        return pd.DataFrame(columns=["engine_uid", "technician_id", "slot_start", "slot_hours", "method", "est_cost"]), [], [], (0.0, 0.0)
    baseline = greedy(tasks, people, distances)
    pop = 30 if quick else POPULATION
    gens = 20 if quick else GENERATIONS
    seeds = [42, 43] if quick else list(range(42, 52))
    ga_runs = [genetic_algorithm(tasks, people, distances, s, pop, gens) for s in seeds]
    best, bestscore, curve = min(ga_runs, key=lambda r: r[1])
    records = []
    for label, chrom in [("GREEDY", baseline), ("GA", best)]:
        for i, (tech, slot) in enumerate(chrom):
            date = start_date + timedelta(days=slot // SLOTS_PER_DAY)
            hour = [8, 12, 16][slot % SLOTS_PER_DAY]
            timestamp = date.replace(hour=hour, minute=0, second=0, microsecond=0)
            records.append({"engine_uid": int(tasks.iloc[i].engine_uid),
                            "technician_id": int(people.iloc[tech].technician_id),
                            "slot_start": timestamp, "slot_hours": SLOT_HOURS,
                            "method": label,
                            "est_cost": round(float(people.iloc[tech].hourly_rate) * SLOT_HOURS, 2)})
    comparison = []
    for label, chrom in [("GREEDY", baseline), ("GA", best)]:
        fitness, parts = score(chrom, tasks, people, distances)
        comparison.append({"method": label, "fitness": fitness, **parts})
    scores = [r[1] for r in ga_runs]
    return pd.DataFrame(records), comparison, curve, (float(np.mean(scores)), float(np.std(scores)))
