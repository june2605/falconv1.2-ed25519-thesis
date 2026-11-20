"""Descriptive statistics and exact within-session comparisons."""
from collections import Counter, defaultdict
import csv
import statistics

from . import environment as env
from . import pdf
from . import protocol as p


def describe(values):
    if not values:
        return {"n": 0}
    n = len(values)
    q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive") if n > 1 else (None, None, None)
    return dict(n=n, median=statistics.median(values), q1=q1, q3=q3, iqr=q3 - q1 if n > 1 else None,
                mean=statistics.mean(values), sample_sd=statistics.stdev(values) if n > 1 else None,
                minimum=min(values), maximum=max(values),
                p95=statistics.quantiles(values, n=100, method="inclusive")[94] if n >= 30 else None)


def read_campaign(directory):
    outcome = p.read_json(directory, "outcome.json")
    complete = outcome["status"] == "complete"
    available = p.check_inventory(directory, complete=complete)
    if "raw.csv" not in available:
        pdf.require(not complete, "analysis.missing_evidence")
        return {"directory": directory.name, "outcome": outcome, "raw_statuses": {}}, []
    recorded = p.read_json(directory, "session.json")
    plan = recorded["configuration"]
    expected = p.schedule(plan["mode"], plan["seed"])
    schedule = {trial.id: trial for trial in expected}
    pdf.require(plan == p.config(plan["mode"], plan["seed"]) or
                env.json_bytes(plan) == env.json_bytes(p.config(plan["mode"], plan["seed"])),
                "analysis.configuration")
    pdf.require(env.file_hash(directory / "schedule.json") == plan["schedule_sha256"] and
                (directory / "schedule.json").read_bytes() == env.json_bytes(p.schedule_file(plan["mode"], plan["seed"], expected)),
                "analysis.schedule")
    seen = defaultdict(set)
    observations, statuses = [], Counter()
    with (directory / "raw.csv").open(encoding="utf-8", newline="") as inp:
        rows = csv.DictReader(inp)
        pdf.require(tuple(rows.fieldnames or ()) == p.RAW_FIELDS, "analysis.header")
        for row in rows:
            pdf.require(None not in row and None not in row.values(), "analysis.row")
            trial = schedule.get(row["trial"])
            pdf.require(trial is not None and row["phase"] == trial.phase and row["layer"] == trial.layer and
                        int(row["block"]) == trial.block and row["method"] == trial.method and
                        row["workload"] == trial.workload and int(row["method_order"]) == trial.method_order and
                        int(row["trial_order"]) == trial.trial_order, "analysis.trial")
            identity = {k: v for k, v in recorded["execution"].items() if k in p.RAW_FIELDS}
            identity.update(schema=p.SCHEMA, protocol=p.PROTOCOL, campaign=recorded["campaign"],
                            session=recorded["session"], schedule_sha256=plan["schedule_sha256"])
            pdf.require(all(row[k] == str(v) for k, v in identity.items()), "analysis.identity")
            statuses[row["status"]] += 1
            if row["status"] != "ok":
                pdf.require(row["status"] in {"failed", "incomplete"} and row["failure_code"], "analysis.status")
                continue
            operation = row["operation"]
            pdf.require(not row["failure_code"] and operation in trial.operations and
                        operation not in seen[trial.id] and row["elapsed_ns"].isascii() and
                        row["elapsed_ns"].isdecimal(), "analysis.observation")
            if trial.layer == "pdf":
                size, expected_hash = pdf.WORKLOADS[trial.workload]
                pdf.require(row["input_sha256"] == expected_hash and int(row["input_bytes"]) == size and
                            int(row["growth_bytes"]) == int(row["output_bytes"]) - size, "analysis.input_size")
            elif trial.layer == "primitive":
                message = pdf.primitive_input(int(trial.workload.removesuffix("-B")))
                pdf.require(row["input_sha256"] == pdf.sha(message) and int(row["input_bytes"]) == len(message),
                            "analysis.input_size")
            else:
                pdf.require(not row["input_sha256"] and not row["input_bytes"], "analysis.keygen_input")
            seen[trial.id].add(operation)
            if trial.phase == "measured":
                row["elapsed_ns"] = int(row["elapsed_ns"])
                observations.append(row)
    details = dict(directory=directory.name, outcome=outcome, provenance=recorded, raw_statuses=dict(statuses))
    if not complete:
        details["comparison"] = "NOT REPORTED: incomplete campaign"
        return details, []
    pdf.require(set(seen) == set(schedule) and all(seen[t] == set(schedule[t].operations) for t in seen)
                and set(statuses) == {"ok"} and len(observations) == plan["measured_positive_rows"]
                and len(observations) == outcome["measured_positive_rows"], "analysis.incomplete_pairing")
    return details, observations


def rows_of_stats(rows):
    groups = defaultdict(list)
    for row in rows:
        key = row["layer"], row["workload"], row["method"], row["operation"]
        groups[key].append(row["elapsed_ns"])
    stats = []
    for (layer, workload, method, op), values in sorted(groups.items()):
        divisor = 10**6 if layer == "pdf" else 10**3
        stats.append(dict(layer=layer, workload=workload, method=method, operation=op,
                          unit="ms" if layer == "pdf" else "us", **describe([v / divisor for v in values])))
    return stats


def paired_values(rows):
    blocks = defaultdict(dict)
    for row in rows:
        if row["layer"] != "pdf":
            continue
        pair = tuple(row[field] for field in ("environment", "run_id", "job", "attempt", "session",
                                              "process_id", "block", "workload", "operation"))
        pdf.require(row["method"] not in blocks[pair], "paired.duplicate")
        blocks[pair][row["method"]] = row["elapsed_ns"]
    for identity, group in sorted(blocks.items()):
        pdf.require(set(group) == set(pdf.METHODS), "paired.missing_method")
        hybrid = group[pdf.HYBRID]
        for baseline in (pdf.ED, pdf.FALCON):
            value = group[baseline]
            yield (identity[-2], identity[-1], baseline), (hybrid - value) / 10**6, hybrid / value if value > 0 else None


def paired_stats(rows):
    groups = defaultdict(lambda: ([], []))
    for key, difference, ratio in paired_values(rows):
        diffs, ratios = groups[key]
        diffs.append(difference)
        if ratio is not None:
            ratios.append(ratio)
    return [dict(workload=w, operation=op, baseline=base,
                 hybrid_minus_baseline_ms=describe(diffs), per_pair_ratio=describe(ratios),
                 nonpositive_denominator_count=len(diffs) - len(ratios))
            for (w, op, base), (diffs, ratios) in sorted(groups.items())]


def output_sizes(rows):
    groups = defaultdict(Counter)
    for row in rows:
        if row["operation"] == "sign_and_publish":
            for field in p.SIZE_FIELDS:
                if row[field] != "":
                    groups[row["method"], row["workload"], field][int(row[field])] += 1
    return [dict(method=method, workload=w, field=field, counts=dict(sorted(counts.items())))
            for (method, w, field), counts in sorted(groups.items())]


def summary(directories):
    sessions, cohorts, ids = [], defaultdict(list), set()
    for directory in directories:
        info, rows = read_campaign(directory)
        if rows:
            data = info["provenance"]
            identity = data["session"]
            pdf.require(identity not in ids, "analysis.duplicate_session")
            ids.add(identity)
            execution = data["execution"]
            cohort = (p.PROTOCOL, data["configuration"]["mode"], execution["environment"],
                      data["profile"]["architecture"], data["profile"]["file_sha256"], data["source_set_sha256"])
            cohorts[cohort].append((data, rows))
            info.update(statistics=rows_of_stats(rows), paired=paired_stats(rows), output_sizes=output_sizes(rows))
        sessions.append(info)
    aggregates = []
    for (protocol, mode, environment, arch, profile_hash, source_set), items in sorted(cohorts.items()):
        rows = [row for _, batch in items for row in batch]
        conditions = [{"session": data["session"], "cpu": data["before"]["cpu"], "build": data["before"]["build"],
                       "runner_image": data["execution"]["runner_image"],
                       "image_version": data["execution"]["runner_image_version"]} for data, _ in items]
        aggregates.append(dict(protocol=protocol, mode=mode, environment=environment, architecture=arch,
                               profile_sha256=profile_hash, source_set_sha256=source_set, sessions=conditions,
                               inference="descriptive pooled observations clustered by session",
                               statistics=rows_of_stats(rows), paired=paired_stats(rows)))
    return dict(sessions=sessions, aggregates=aggregates, quantile="Type 7 h = 1 + (n-1)p",
                p95_min_n=30, warmups="retained in evidence; excluded from summaries")
