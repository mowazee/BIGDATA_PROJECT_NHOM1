#!/usr/bin/env python3
"""Đặt cấu hình biểu đồ (cột trục X/Y, nhóm) cho notebook Ecommerce_Hive_Analysis qua REST API Zeppelin.
Zeppelin cần biết cột nào là trục X (keys), cột nào là giá trị (values) thì mới vẽ được biểu đồ.
  python zeppelin/config_charts.py [http://localhost:8081]
"""
import json
import sys
import urllib.request

Z = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8081"


def call(method, path, body=None):
    req = urllib.request.Request(Z + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def col(name, idx):
    return {"name": name, "index": idx, "aggr": "sum"}


notes = call("GET", "/api/notebook")["body"]
note_id = next(n["id"] for n in notes if n["path"].strip("/") == "Ecommerce_Hive_Analysis")
paras = call("GET", "/api/notebook/" + note_id)["body"]["paragraphs"]

# (chế độ biểu đồ, keys, groups, values) theo thứ tự đoạn; None = không phải biểu đồ
charts = [
    None,
    ("multiBarChart", [col("source", 0)], [], [col("so_san_pham", 1)]),
    ("pieChart", [col("phan_khuc", 0)], [], [col("so_luong", 1)]),
    ("multiBarChart", [col("brand", 0)], [], [col("gia_tb_trieu", 1)]),
    ("lineChart", [col("storage_gb", 0)], [col("source", 1)], [col("gia_tb_trieu", 2)]),
    ("table", [], [], []),
    ("multiBarChart", [col("source", 0)], [], [col("so_tin_nhan", 1)]),
]

for p, ch in zip(paras, charts):
    cfg = {"title": True, "editorHide": False, "tableHide": False, "colWidth": 12}
    if ch:
        mode, keys, groups, values = ch
        res_idx = str(len(p.get("results", {}).get("msg", [])) - 1) if p.get("results") else "0"
        cfg["results"] = {res_idx: {"graph": {
            "mode": mode, "height": 320, "optionOpen": False,
            "keys": keys, "groups": groups, "values": values,
            "setting": {mode: {}} if mode != "table" else {},
            "commonSetting": {}}}}
    else:
        cfg["editorHide"] = True
    call("PUT", "/api/notebook/{}/paragraph/{}/config".format(note_id, p["id"]), cfg)
    print("ok:", p.get("title"))
