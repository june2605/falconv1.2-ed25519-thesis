"""Export the accepted Phase 5.5C PDF summaries for the Vietnamese thesis."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from itertools import product
import json
from pathlib import Path


INPUT_SHA256 = {
    "verified-main.json": "dcdcf77226389248f29a8f5e4964ba7bb2cef13a40737b3dde058b7cda8139e2",
    "summary-main.json": "7ff23a8412216fb1306a0f8a058b3fe06039b78b807d64159c1c33811e5f7868",
}
ENVIRONMENTS = ("CI-WIN", "CI-LINUX", "CI-MAC")
WORKLOADS = {"demo": "742 byte", "1-MiB": "1 MiB", "10-MiB": "10 MiB"}
METHODS = ("Ed25519", "Falcon-512", "Hybrid")
OPERATIONS = {"sign_and_publish": "Ký và xuất", "verify_published_file": "Xác minh độc lập"}


def read_accepted(campaign, name):
    path = campaign / name
    if not path.is_file():
        raise ValueError(f"NOT PERFORMED: accepted input is missing: {path}")
    data = path.read_bytes()
    if sha256(data).hexdigest() != INPUT_SHA256[name]:
        raise ValueError(f"SHA-256 mismatch: {path}")
    return json.loads(data)


def indexed(rows, *fields):
    records = {}
    for row in rows:
        key = tuple(row[field] for field in fields)
        if key in records:
            raise ValueError(f"Duplicate summary key: {key}")
        records[key] = row
    return records


def pdf_statistics(bundle, n):
    stats = indexed(
        (row for row in bundle["statistics"] if row["layer"] == "pdf"),
        "workload", "method", "operation",
    )
    if set(stats) != set(product(WORKLOADS, METHODS, OPERATIONS)):
        raise ValueError("Incomplete PDF timing groups.")
    if any(row["n"] != n or row["unit"] != "ms" for row in stats.values()):
        raise ValueError("Unexpected PDF sample size or unit.")
    return stats


def paired_statistics(bundle):
    stats = indexed(bundle["paired"], "workload", "baseline", "operation")
    if set(stats) != set(product(WORKLOADS, METHODS[:2], OPERATIONS)):
        raise ValueError("Incomplete paired groups.")
    for row in stats.values():
        if (row["hybrid_minus_baseline_ms"]["n"] != 90
                or row["per_pair_ratio"]["n"] != 90
                or row["nonpositive_denominator_count"] != 0):
            raise ValueError("Unexpected paired counts.")
    return stats


def storage_statistics(sessions):
    histograms = defaultdict(Counter)
    for bundle in sessions:
        for row in bundle["output_sizes"]:
            key = row["method"], row["field"]
            histograms[key].update({int(value): count for value, count in row["counts"].items()})

    def histogram(method, field):
        counts = histograms[method, field]
        if sum(counts.values()) != 810:
            raise ValueError(f"Unexpected storage sample size: {method}, {field}")
        return sorted(counts)

    result = []
    for method in METHODS:
        fields = {}
        contents = metadata = 0
        for layer, single in zip(("ed", "falcon"), METHODS[:2], strict=True):
            if method not in (single, "Hybrid"):
                continue
            capacity, = histogram(method, f"{layer}_capacity_bytes")
            framing, = histogram(method, f"{layer}_metadata_bytes")
            native = histogram(method, f"{layer}_native_bytes")
            fields[layer] = {"capacity": capacity, "native_min": native[0], "native_max": native[-1]}
            contents += 2 * capacity
            metadata += framing
        growth, = histogram(method, "growth_bytes")
        if growth != contents + metadata:
            raise ValueError(f"Unexpected container growth: {method}")
        result.append(dict(method=method, n=810, contents=contents, metadata=metadata, growth=growth, **fields))
    return result


def fmt(value):
    return f"{value:.3f}".replace(".", ",")


def integer(value):
    return f"{value:,}".replace(",", " ")


def md_table(headers, rows):
    rows = [headers, ["---"] * len(headers), *rows]
    return "\n".join("| " + " | ".join(map(str, row)) + " |" for row in rows)


def timing_tables(pools, slots):
    fields = ("median", "q1", "q3", "iqr", "mean", "sample_sd", "p95")
    headers = ["PDF", "Phương pháp", "n", "Trung vị", "Q1", "Q3", "IQR", "Trung bình", "SD mẫu", "P95"]
    short = ["Môi trường", "PDF", "Phương pháp", "Phiên 1", "Phiên 2", "Phiên 3"]
    for op, heading in OPERATIONS.items():
        yield f"## {heading}\n\nMỗi bảng gộp ba phiên của cùng môi trường. Đơn vị ms."
        session_rows = []
        for environment in ENVIRONMENTS:
            rows = []
            for workload, size in WORKLOADS.items():
                for method in METHODS:
                    key = workload, method, op
                    stats = pools[environment][key]
                    rows.append([size, method, stats["n"], *(fmt(stats[field]) for field in fields)])
                    medians = [fmt(slots[environment, slot][key]["median"]) for slot in (1, 2, 3)]
                    session_rows.append([environment, size, method, *medians])
            yield f"### {environment}\n\n" + md_table(headers, rows)
        yield f"### Trung vị từng phiên - {heading.lower()}\n\nn = 30 trong mỗi ô, đơn vị ms.\n\n" + md_table(
            short, session_rows,
        )


def contrast_tables(pairs):
    headers = [
        "Môi trường", "PDF", "n", "Hybrid - Ed25519 (ms)", "Hybrid - Falcon-512 (ms)",
        "Hybrid / Ed25519", "Hybrid / Falcon-512",
    ]
    yield """## So sánh ghép cặp

Mỗi ô tương phản ghi trung vị (IQR) của các hiệu hoặc tỷ số tính trực tiếp trên từng cặp trong cùng phiên, khối, đầu vào và thao tác. Cả 90 cặp của mỗi nhóm đều có mẫu số dương."""
    for op, heading in OPERATIONS.items():
        rows = []
        for environment in ENVIRONMENTS:
            for workload, size in WORKLOADS.items():
                stats = [pairs[environment][workload, baseline, op] for baseline in METHODS[:2]]
                values = [row[field] for field in ("hybrid_minus_baseline_ms", "per_pair_ratio") for row in stats]
                rows.append([environment, size, values[0]["n"],
                             *(f"{fmt(value['median'])} ({fmt(value['iqr'])})" for value in values)])
        yield f"### Ghép cặp - {heading.lower()}\n\n" + md_table(headers, rows)


def storage_table(storage):
    rows = []
    for record in storage:
        native, capacity = [], []
        for layer in ("ed", "falcon"):
            if layer not in record:
                continue
            value = record[layer]
            low, high = value["native_min"], value["native_max"]
            native.append(str(low) if low == high else f"{low}-{high}")
            capacity.append(integer(value["capacity"]))
        rows.append([record["method"], record["n"], " / ".join(native), " / ".join(capacity),
                     *(integer(record[key]) for key in ("contents", "metadata", "growth"))])
    return """## Kích thước đầu ra

Mọi kích thước trong bảng có đơn vị byte. Với Hybrid, hai giá trị của chữ ký gốc và sức chứa theo thứ tự Ed25519 rồi Falcon-512. Phần khung gồm dấu mở, dấu đóng, ByteRange, SigLength và cú pháp Contents. Ô Contents chứa chữ ký hex và phần đệm.""" + "\n\n" + md_table(
        ["Phương pháp", "Số PDF", "Chữ ký gốc", "Sức chứa trước hex", "Ô Contents", "Phần khung", "Tệp tăng"],
        rows,
    )


def export(campaign, output):
    verified = read_accepted(campaign, "verified-main.json")
    summary = read_accepted(campaign, "summary-main.json")
    completed = indexed((job for job in verified["jobs"] if "session_path" in job), "environment", "slot")
    bundles = {bundle["provenance"]["session"]: bundle for bundle in summary["sessions"]}
    if len(bundles) != 9 or set(completed) != set(product(ENVIRONMENTS, (1, 2, 3))):
        raise ValueError("Expected exactly three sessions per environment.")
    slots = {key: pdf_statistics(bundles[row["session"]], 30) for key, row in completed.items()}
    aggregates = indexed(summary["aggregates"], "environment")
    if set(aggregates) != {(env,) for env in ENVIRONMENTS}:
        raise ValueError("Unexpected environment cohorts.")
    for (env,), bundle in aggregates.items():
        sessions = {completed[env, slot]["session"] for slot in (1, 2, 3)}
        if bundle["mode"] != "main" or {item["session"] for item in bundle["sessions"]} != sessions:
            raise ValueError(f"Unexpected session membership: {env}")
    pools = {env: pdf_statistics(aggregates[env,], 90) for env in ENVIRONMENTS}
    pairs = {env: paired_statistics(aggregates[env,]) for env in ENVIRONMENTS}
    storage = storage_statistics(summary["sessions"])
    plots = {
        "source": INPUT_SHA256,
        "pdf": [{"environment": env, **row} for env, records in pools.items() for row in records.values()],
        "paired": [{"environment": env, "workload": row["workload"], "baseline": row["baseline"],
                    "operation": row["operation"], **row["hybrid_minus_baseline_ms"]}
                   for env, records in pairs.items() for row in records.values()],
        "storage": storage,
    }
    parts = [
        "# Phụ lục - Bảng so sánh PDF trên ba môi trường CI",
        "Nguồn là chín phiên main của run `44705704103`, nguồn đo "
        "`613a46d06930ffd9224afa557fa90992e3a56a2a`. Số liệu lấy từ "
        "`summary-main.json` đã đối chiếu với CSV của từng phiên. Phân vị dùng quy tắc Type 7. "
        "SD mẫu dùng mẫu số n - 1. Số liệu làm tròn ba chữ số thập phân khi trình bày. "
        "[Nguồn và phương pháp](../phase5-5d-thesis-integration.md)",
        *timing_tables(pools, slots),
        *contrast_tables(pairs),
        storage_table(storage),
    ]
    output.mkdir()
    with (output / "phase5-5d-pdf-vi.md").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("\n\n".join(parts) + "\n")
    with (output / "figure-data.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(plots, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New directory outside the source evidence.")
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.campaign.resolve()):
        parser.error("--output must be outside the accepted campaign directory.")
    try:
        export(args.campaign, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
