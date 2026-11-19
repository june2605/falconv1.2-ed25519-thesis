"""Produce Phase 5.3 Vietnamese tables and plot inputs from archived observations."""

import argparse
import csv
import json
import math
from pathlib import Path
import statistics

from research.benchmarks import phase5_2a as pilot
from research.benchmarks import phase5_2b_analysis as previous
from research.benchmarks.phase5_2b_collect import file_hash
import utils


INVENTORY_PATH = "analysis-l3zob63s/checksums.sha256"
INVENTORY_SHA256 = "f96d025145a113009eb3224fa9129b1985dd1fb3b13cee983a49a424e1679da3"
SOURCE_COMMIT = "3ebfe31abb080a0355ac512d6190910d33e98a63"
SESSIONS = ("matched-01", "matched-02", "matched-03")
SUPPLEMENT = "optional-40-measured"
FEASIBILITY = "optional-40-feasibility"
ALGORITHMS = ("Ed25519", "Falcon-512")
PRIMITIVE = ("64-B", "1024-B")
DOCUMENTS = ("demo", "1-MiB", "10-MiB", "40-MiB")
OPERATIONS = ("sign_and_publish", "verify_published_file")
WORKLOAD_LABELS = {"64-B": "64 B", "1024-B": "1 024 B", "demo": "742 B",
                   "1-MiB": "1 MiB", "10-MiB": "10 MiB", "40-MiB": "40 MiB"}
OPERATION_LABELS = {"sign": "Ký", "verify": "Xác minh", "sign_and_publish": "Ký và xuất",
                    "verify_published_file": "Xác minh tệp đã xuất"}


def verify_inventory(campaign):
    inventory = campaign / INVENTORY_PATH
    if file_hash(inventory) != INVENTORY_SHA256:
        raise ValueError("The archived Phase 5.2B inventory has changed.")
    for line in inventory.read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        if file_hash(campaign / name) != digest:
            raise ValueError(f"Archive hash mismatch: {name}")


def read_measurements(campaign):
    verify_inventory(campaign)
    collection = previous.completed_collection(campaign)
    if tuple(collection["sessions"]) != (*SESSIONS, FEASIBILITY, SUPPLEMENT):
        raise ValueError("Unexpected Phase 5.2B session list.")
    preflight = previous.load_json(campaign / "optional-40-preflight.json")
    records = {}
    for label in collection["sessions"]:
        context, metadata, directory = previous.read_session(campaign, label)
        if metadata["commit"] != SOURCE_COMMIT:
            raise ValueError(f"Unexpected source commit: {label}")
        previous.check_inputs(context, metadata, directory, preflight)
        values, _, _ = previous.read_raw(directory / "raw.csv", metadata)
        records[label] = values
    return records


def elapsed(records, session, workload, algorithm, operation):
    if algorithm == "Hybrid":
        mode = "unprofiled" if operation in OPERATIONS else "profiled"
        return records[session][("B", mode, workload, algorithm, operation, "ns")]
    return records[session][("A", "primitive", workload, algorithm, operation, "ns")]


def pooled(records, workload, algorithm, operation):
    return [value for name in SESSIONS for value in elapsed(records, name, workload, algorithm, operation)]


def describe(values):
    quartiles = statistics.quantiles(values, n=4, method="inclusive")
    return {**previous.describe(values), "q1": quartiles[0], "q3": quartiles[2],
            "iqr": quartiles[2] - quartiles[0]}


def vi_number(value, scale=1, precision=3):
    return f"{value / scale:.{precision}f}".replace(".", ",")


def elapsed_row(label, data):
    stats = describe(data)
    return [*label, stats["n"], *(vi_number(stats[field], 10**6)
                                  for field in ("median", "iqr", "mean", "sd", "p95"))]


def table(headers, rows):
    def line(cells):
        return "| " + " | ".join(map(str, cells)) + " |"
    return "\n".join([line(headers), line(["---"] * len(headers)), *(line(row) for row in rows)])


def timing_tables(records):
    stat_headers = ("n", "Trung vị", "IQR", "Trung bình", "SD mẫu", "P95")
    by_primitive = [elapsed_row((WORKLOAD_LABELS[w], a, OPERATION_LABELS[o]), pooled(records, w, a, o))
                    for w in PRIMITIVE for a in ALGORITHMS for o in ("sign", "verify")]
    prim_headers = ("Thông điệp", "Thuật toán", "Thao tác")
    by_session = [elapsed_row((label, WORKLOAD_LABELS[w], a, OPERATION_LABELS[o]),
                              elapsed(records, label, w, a, o))
                  for label in SESSIONS for w in PRIMITIVE for a in ALGORITHMS for o in ("sign", "verify")]

    def ratio(workload, operation, measure):
        ed25519, falcon = (statistics.median(measure(workload, algorithm, operation)) for algorithm in ALGORITHMS)
        return vi_number(falcon / ed25519)

    ratios = [(WORKLOAD_LABELS[w], OPERATION_LABELS[o],
               *(ratio(w, o, lambda *args: elapsed(records, session, *args)) for session in SESSIONS),
               ratio(w, o, lambda *args: pooled(records, *args)))
              for w in PRIMITIVE for o in ("sign", "verify")]
    hybrid = [elapsed_row((WORKLOAD_LABELS[w], OPERATION_LABELS[o]), pooled(records, w, "Hybrid", o))
              for w in DOCUMENTS[:-1] for o in OPERATIONS]
    hybrid_sessions = [elapsed_row((label, WORKLOAD_LABELS[w], OPERATION_LABELS[o]),
                                   elapsed(records, label, w, "Hybrid", o))
                       for label in SESSIONS for w in DOCUMENTS[:-1] for o in OPERATIONS]
    optional = [elapsed_row(("40 MiB", OPERATION_LABELS[o]), elapsed(records, SUPPLEMENT, "40-MiB", "Hybrid", o))
                for o in OPERATIONS]
    pdf_headers = ("PDF", "Thao tác")
    return {"primitive": table((*prim_headers, *stat_headers), by_primitive),
            "primitive_sessions": table(("Phiên", *prim_headers, *stat_headers), by_session),
            "ratios": table(("Thông điệp", "Thao tác", *SESSIONS, "Gộp 3 phiên"), ratios),
            "hybrid": table((*pdf_headers, *stat_headers), hybrid),
            "hybrid_sessions": table(("Phiên", *pdf_headers, *stat_headers), hybrid_sessions),
            "supplement": table((*pdf_headers, *stat_headers), optional)}


def profile_table(records):
    stages = (
        ("capture_source", "Chụp dữ liệu nguồn"),
        ("prepare_ed25519", "Tạo vùng chứa Ed25519"),
        ("assemble_ed25519_message", "Ghép các đoạn byte cho Ed25519"),
        ("ed25519_sign", "Lời gọi ký Ed25519"),
        ("embed_ed25519", "Chèn chữ ký Ed25519"),
        ("prepare_falcon", "Tạo vùng chứa Falcon"),
        ("shake256_prehash", "Tiền băm SHAKE256"),
        ("falcon_sign", "Lời gọi ký Falcon-512"),
        ("embed_falcon", "Chèn chữ ký Falcon"),
        ("write_and_fsync_candidate", "Ghi và fsync tệp tạm"),
        ("self_verify_candidate", "Tự xác minh tệp tạm"),
        ("publish_candidate", "Công bố tệp đầu ra"),
        ("profiled_sign_and_publish", "Toàn bộ lời gọi có đo chi tiết"),
    )
    rows = []
    for operation, label in stages:
        units = [pooled(records, w, "Hybrid", operation) for w in DOCUMENTS[:-1]]
        units.append(elapsed(records, SUPPLEMENT, DOCUMENTS[-1], "Hybrid", operation))
        rows.append([label, *(f"{vi_number(statistics.median(values), 10**6)} "
                              f"({vi_number(statistics.stdev(values), 10**6)})" for values in units)])
    return table(("Công đoạn", "742 B", "1 MiB", "10 MiB", "40 MiB bổ sung"), rows)


def historical_table(root):
    manifest = previous.load_json(pilot.ROOT / "docs/phase1-baseline.json")["benchmark_dataset_sha256"]
    for name, expected in manifest.items():
        if file_hash(root / name) != expected:
            raise ValueError(f"Historical hash mismatch: {name}")
    rows = []
    for size in (1, 10, 50, 200, 500):
        def read(category):
            path = root / "benchmark" / f"{category}_benchmark_{size}mb.csv"
            with path.open(newline="", encoding="utf-8") as stream:
                result = list(csv.DictReader(stream))
            if [int(row["run"]) for row in result] != list(range(1, 101)):
                raise ValueError(f"Unexpected historical run labels: {path}")
            return result

        signing, verification = (read(category) for category in ("sign", "verify"))
        signed = [float(row["ed_total"]) + float(row["fal_total"]) for row in signing]
        verified = [float(row["total"]) for row in verification]
        if not all(math.isfinite(value) and value >= 0 for value in (*signed, *verified)):
            raise ValueError("Invalid historical observations.")
        file_size = (root / "data_test" / f"file_test_{size}mb.pdf").stat().st_size
        rows.append((f"{size}mb", f"{file_size:,}".replace(",", " "),
                     len(signing), len(verification), sum(row["ok"] == "True" for row in verification),
                     vi_number(statistics.median(signed), 0.001, 2),
                     vi_number(statistics.median(verified), 0.001, 2),
                     sum(float(row["fal_crypto"]) == 0 for row in verification)))
    return table(("Nhãn gốc", "Byte đầu vào", "Lượt ký", "Lượt xác minh", "ok=True",
                  "Trung vị tổng các bước ký (ms)", "Trung vị tổng xác minh đã lưu (ms)",
                  "Số lần Falcon verify crypto = 0"), rows)


def container_table():
    sizes = []
    for i, capacity in enumerate(utils.DEFAULT_SIGNATURE_CAPACITIES):
        start = len(utils.SIG_MARKER_START[i])
        end = len(utils.SIG_MARKER_END[i])
        byte_range = len(utils.ZERO_BYTE_RANGE)
        signature_length = len(utils.SIG_LEN % capacity) + len(utils.SIG_LEN_SUFFIX)
        content_delimiters = len(utils.CONTENTS_PREFIX) + len(utils.CONTENTS_SUFFIX)
        sizes.append((start, byte_range, signature_length, content_delimiters, 2 * capacity, end))
    labels = ("Dấu mở", "Dòng ByteRange", "Dòng SigLength", "Cú pháp dòng Contents và LF",
              "Ô ký tự hex (gồm chữ ký và đệm)", "Dấu đóng")
    rows = [(label, a, b, a + b) for label, a, b in zip(labels, *sizes, strict=True)]
    rows.append(("Tổng số byte ghi thêm", sum(sizes[0]), sum(sizes[1]), sum(map(sum, sizes))))
    return table(("Thành phần", "Ed25519 (byte)", "Falcon-512 (byte)", "Tổng (byte)"), rows)


def chart_group(records, workload, algorithm, operation, label):
    optional = workload == "40-MiB"
    selected = {session: elapsed(records, session, workload, algorithm, operation)
                for session in ((SUPPLEMENT,) if optional else SESSIONS)}
    distribution = describe([value for values in selected.values() for value in values])
    return {"label": label, "iqr_ms": [distribution[field] / 10**6 for field in ("q1", "q3")],
            "median_ms": distribution["median"] / 10**6,
            "session_medians_ms": {key: statistics.median(value) / 10**6 for key, value in selected.items()}}


def chart_data(records):
    plots = []
    primitive_caption = "Dữ liệu chính · 3 phiên × 30 lần đo mỗi điều kiện"
    pdf_caption = "742 B, 1 MiB, 10 MiB: 3 phiên × 30 · 40 MiB bổ sung: 1 phiên × 30"
    for operation, title in (("sign", "So sánh thời gian ký ở mức thuật toán"),
                             ("verify", "So sánh thời gian xác minh ở mức thuật toán")):
        groups = [chart_group(records, w, a, operation, f"{a}\n{WORKLOAD_LABELS[w]}")
                  for w in PRIMITIVE for a in ALGORITHMS]
        plots.append(dict(name=f"primitive-{operation}", title=title, subtitle=primitive_caption,
                          groups=groups, logarithmic=operation == "sign"))
    for operation, suffix, title in zip(OPERATIONS, ("sign", "verify"),
                                        ("Ký và xuất PDF theo dung lượng", "Xác minh độc lập PDF đã xuất theo dung lượng"),
                                        strict=True):
        groups = [chart_group(records, w, "Hybrid", operation, WORKLOAD_LABELS[w] + ("\nBổ sung" if w == "40-MiB" else ""))
                  for w in DOCUMENTS]
        plots.append(dict(name=f"hybrid-{suffix}", title=title, subtitle=pdf_caption, groups=groups, logarithmic=False))
    tails = [{"label": WORKLOAD_LABELS[w], "series": {s: [v / 10**6 for v in sorted(elapsed(records, s, w, "Hybrid", OPERATIONS[0]))]
                                                       for s in SESSIONS}}
             for w in DOCUMENTS[:-1]]
    labels = {"ms": "Thời gian (ms)", "log_ms": "Thời gian (ms, thang logarit)",
              "median": "Trung vị", "supplement": "Phiên bổ sung",
              "tail_title": "Phân bố thời gian ký và xuất PDF theo phiên",
              "tail_caption": "30 quan sát mỗi phiên xếp theo thời gian tăng dần · mỗi ô có thang dọc riêng"}
    return {"plots": plots, "tails": tails, "sessions": SESSIONS, "supplement": SUPPLEMENT, "labels": labels}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--historical-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New directory outside Git and the source archive")
    options = parser.parse_args()
    campaign = options.campaign.resolve(strict=True)
    output = pilot.output_parent(options.output.parent) / options.output.name
    if output.is_relative_to(campaign):
        raise ValueError("Keep Phase 5.3 derivatives outside the Phase 5.2 archive.")
    records = read_measurements(campaign)
    tables = timing_tables(records)
    tables["profile"] = profile_table(records)
    tables["historical"] = historical_table(options.historical_root)
    tables["container"] = container_table()
    figures = chart_data(records)
    output.mkdir()
    for name, value in (("tables.json", tables), ("plot-data.json", figures)):
        with (output / name).open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
    print(output)


if __name__ == "__main__":
    main()
